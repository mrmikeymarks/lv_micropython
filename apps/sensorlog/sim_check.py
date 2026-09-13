# Hardware-free check of the sensorlog record path on the unix port:
#   cd apps/sensorlog && ../../ports/unix/build-standard/micropython sim_check.py [out.bin]
# A fake bus serves four sensors: one healthy, one that drops out every 7th
# read, one that is dead (never answers), and one behind a mux channel.
# Verifies: header layout, record count, ZERO heap growth per sample, that a
# status bit is set exactly when a slot is zeroed, byte-exact slots for every
# successful read, that the dead sensor is backed off (few bus calls instead
# of one timeout per sample), and that mux select writes happen only when the
# channel changes. Decode the output with decode.py to check the host side.

import sys
import gc
import struct

sys.path.insert(0, "../../ports/esp32/modules")
import sensorlog

SENSORS = (
    ("good", 0x48, 0x00, 2, ">h"),
    ("flaky", 0x40, 0x02, 1, "B"),
    ("dead", 0x50, 0x00, 4, "<I"),
    ("muxed", 0x48, 0x00, 2, ">h", None, (0x70, 3)),
    ("cmdpart", 0x58, None, 3, ">HB", None, None, b"\x20\x08"),   # command-based, pipelined
    ("wide", 0x53, (0x2005, 16), 1, "B", (((0x0000, 16), 8),)),    # 16-bit register + calib
)
N = 400
path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/sensorlog_sim.bin"
failures = 0


def fail(msg):
    global failures
    failures += 1
    print("FAIL", msg)


class FakeI2C:
    def __init__(self):
        self.calls = {}
        self.mux_writes = 0
        self.channel = None

    def writeto(self, addr, data):
        if addr == 0x58:
            self.cmds = getattr(self, "cmds", 0) + 1
            self.pending = bytes([0x12, 0x34, 0x56])   # "measurement" ready for the next read
            return
        self.mux_writes += 1
        self.channel = data[0]

    def readfrom_into(self, addr, buf):
        self.calls[addr] = self.calls.get(addr, 0) + 1
        p = getattr(self, "pending", None)
        if p is None:
            raise OSError(19)   # nothing was commanded yet
        buf[:] = p[:len(buf)]
        self.pending = None

    def readfrom_mem(self, addr, reg, n, addrsize=8):
        self.wide_reads = getattr(self, "wide_reads", 0) + (1 if addrsize == 16 else 0)
        return bytes((reg + i) & 0xFF for i in range(n))

    def readfrom_mem_into(self, addr, reg, buf, addrsize=8):
        if addr == 0x53 and addrsize != 16:
            raise OSError(19)   # this part only answers 16-bit register addresses
        n = self.calls[addr] = self.calls.get(addr, 0) + 1
        if addr == 0x50:
            raise OSError(110)                      # dead: always times out
        if addr == 0x40 and n % 7 == 0:
            raise OSError(19)                       # flaky: drops out periodically
        base = (addr + reg + n + (self.channel or 0)) & 0xFF
        for i in range(len(buf)):
            buf[i] = (base + i) & 0xFF


i2c = FakeI2C()
lg = sensorlog.Logger(i2c, SENSORS, batch=16)
lg.open(path)
if lg.recsize != 7 + 2 + 1 + 4 + 2 + 3 + 1:
    fail("record size %d, expected 20" % lg.recsize)
i2c.writeto(0x58, b"\x20\x08")   # INIT would have issued the first command

lg.sample(1000, 0)
gc.collect()
before = gc.mem_alloc()
for k in range(1, 16):
    lg.sample(1000 + k, k)
gc.collect()
grown = gc.mem_alloc() - before
print("heap growth over 15 samples: %d bytes" % grown)
if grown > 0:
    fail("sampling loop allocates (%d bytes)" % grown)
for k in range(16, N):
    lg.sample(1000 + k, k % 1000)
lg.close()

data = open(path, "rb").read()
head, _, body = data.partition(b"\n")
print("header:", head.decode())
if len(body) != N * lg.recsize:
    fail("body %d bytes, expected %d" % (len(body), N * lg.recsize))

zeroed_with_bit = zeroed_without_bit = ok_reads = 0
for k in range(N):
    rec = body[k * 20:(k + 1) * 20]
    t, ms, status = struct.unpack_from("<IHB", rec, 0)
    off = 7
    for i, s in enumerate(SENSORS):
        slot = rec[off:off + s[3]]
        if status & (1 << i):
            zeroed_with_bit += 1
            if slot != bytes(s[3]):
                fail("record %d: failed %s not zeroed" % (k, s[0])); break
        else:
            ok_reads += 1
            if slot == bytes(s[3]) and s[0] != "flaky" and s[3] > 1:   # a lone byte can be 0
                zeroed_without_bit += 1
            if s[0] == "cmdpart" and slot != b"\x12\x34\x56":
                fail("record %d: command-based read returned %r" % (k, slot)); break
        off += s[3]
print("slots: %d ok reads, %d zeroed+flagged, %d zeroed-without-flag" % (ok_reads, zeroed_with_bit, zeroed_without_bit))
if zeroed_without_bit:
    fail("a slot was zero without its status bit")
dead_calls = i2c.calls.get(0x50, 0)
print("dead sensor: %d bus calls in %d samples (backoff caps retries at 1 per %d)" % (dead_calls, N, sensorlog.MAX_BACKOFF))
if dead_calls > N // sensorlog.MAX_BACKOFF + 8:
    fail("backoff not limiting a dead sensor (%d calls)" % dead_calls)
if i2c.calls.get(0x48, 0) < 2 * N * 0.9:
    fail("healthy sensors were not read every sample")
print("mux select writes: %d (one per sample: channel changes once per record)" % i2c.mux_writes)
if i2c.mux_writes > N:
    fail("mux written more than once per sample")
print("command part: %d commands issued for %d reads; 16-bit calib reads: %d" % (i2c.cmds, i2c.calls.get(0x58, 0), i2c.wide_reads))
if i2c.cmds != N + 1 or i2c.calls.get(0x58, 0) != N:
    fail("command pipelining broken (cmds %d, reads %d)" % (i2c.cmds, i2c.calls.get(0x58, 0)))
if "calib=wide:0001020304050607" not in head.decode():
    fail("16-bit calibration block missing from header")
if lg.total_fail[2] != dead_calls:
    fail("dead sensor failure count %d != calls %d" % (lg.total_fail[2], dead_calls))
lg.report()
print("---")
print("%d failure(s)" % failures)
sys.exit(1 if failures else 0)
