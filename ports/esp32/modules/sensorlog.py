# sensorlog - I2C sensor chain -> SD card logger, tuned for a no-PSRAM ESP32.
#
# Efficiency rules this module lives by:
#   * zero allocation in the sampling loop: each sensor's raw register bytes
#     are read straight into its slot of ONE preallocated record buffer
#     (i2c.readfrom_mem_into into precomputed memoryviews), timestamps are
#     packed in place, nothing is formatted, no floats are created
#   * one card write per BATCH records, one flush per SYNC_S seconds, so the
#     SD card sees a few hundred bytes at a time instead of a write per sample
#   * fixed-size binary records with a self-describing text header; convert
#     to CSV on the host with apps/sensorlog/decode.py (the ESP32 does the
#     minimum: read, stamp, store)
#   * the card gets its own SPI host (HSPI on free pins); the display and
#     touch keep VSPI, so logging never contends with LVGL
#   * every failure is contained: a sensor that fails to answer sets a status
#     bit in that record (its bytes are zeroed), a card that fails is
#     remounted with backoff, and a watchdog reboots a wedged board
#
# Use on the board (main.py):   import sensorlog; sensorlog.run()
# Test without hardware:        apps/sensorlog/sim_check.py (unix port)

from micropython import const
import struct
import time
import os
import gc

# ---- configuration --------------------------------------------------------- EDIT ME
# Each entry: (name, address, register, nbytes, fmt[, calib[, mux[, cmd]]])
#   register  int for an 8-bit register, (int, 16) for a 16-bit register
#             address (EEPROM-style parts such as the ST25DV), or None for a
#             command-based part that is read with a plain read
#   nbytes    contiguous bytes read in ONE transaction (never split a sensor
#             into several reads - that is the biggest bus saving there is)
#   fmt       struct format of those bytes, values logged RAW
#   calib     ((register, nbytes), ...) read ONCE into the file header so the
#             host can turn raw words into units (register may be (int, 16))
#   mux       (mux address, channel) for sensors behind a TCA9548A, so parts
#             with the SAME address can share the chain
#   cmd       bytes written right AFTER each read to start the next
#             measurement: the result is collected on the next sample, so a
#             conversion delay never stalls the loop (needs INTERVAL_MS >= the
#             part's conversion time)
SENSORS = (
    ("bme280", 0x77, 0xF7, 8, ">HBHBH", ((0x88, 26), (0xE1, 7))),
    ("sgp30", 0x58, None, 6, ">HBHB", None, None, b"\x20\x08"),     # eCO2 ppm, crc, TVOC ppb, crc
    ("nfc_eh", 0x53, (0x2002, 16), 1, "B", (((0x0000, 16), 64),)),  # ST25DV EH_CTRL_Dyn: bit2 = RF field on; header = NDEF bytes
    ("nfc_it", 0x53, (0x2005, 16), 1, "B"),                          # ST25DV IT_STS_Dyn: RF events since last read (bit1 activity, bit7 write)
)
# one-time writes before logging starts: (address, register or None, bytes)
INIT = (
    (0x77, 0xF2, b"\x01"),   # BME280 ctrl_hum: humidity x1
    (0x77, 0xF4, b"\x27"),   # BME280 ctrl_meas: temp x1, press x1, normal mode
    (0x77, 0xF5, b"\xa0"),   # BME280 config: 1000 ms standby, no filter
    (0x58, None, b"\x20\x03"),   # SGP30 iaq_init (first 15 s of readings are 400/0 warm-up values)
    (0x58, None, b"\x20\x08"),   # SGP30 first measure_iaq so sample 1 has data to collect
)
INTERVAL_MS = const(1000)
BATCH = const(32)        # records per card write
SYNC_S = const(30)       # seconds between forced flushes = max data at risk on power loss
WDT_MS = const(60000)    # watchdog; 0 to disable
REPORT_S = const(300)    # serial health line every N seconds (0 = never)
DISPLAY_S = const(2)     # refresh the LCD every N seconds (0 = no display)
DISPLAY_ADDR = 0x2D      # SparkFun Qwiic SerLCD 16x2 (see serlcd.py); None to disable
MAX_BACKOFF = const(64)  # a failing sensor is retried every 1,2,4..64 samples, never every sample
MOUNT = "/sd"
FALLBACK_DIR = "/log"   # used when no card is present: internal flash (small, but never a dead logger)
SD_PINS = dict(slot=3, sck=21, mosi=32, miso=25, cs=27)   # VSPI host on free pins: the display owns HSPI (slot 2)

MAGIC = "SLOG1"


def _hex(b):
    return "".join("%02x" % c for c in b)


def _regname(reg):
    if reg is None:
        return "cmd"
    if isinstance(reg, tuple):
        return "%d/%d" % reg
    return "%d" % reg
STAMP = "<IHB"           # epoch seconds, milliseconds, status bits (bit i = sensor i failed)
STAMP_LEN = const(7)


class Logger:
    """Fixed-layout binary logger. Hardware-free: pass any object with
    readfrom_mem_into(addr, reg, buf) and a writable file."""

    def __init__(self, i2c, sensors=SENSORS, batch=BATCH):
        self.i2c = i2c
        self.sensors = sensors
        self.batch = batch
        offs, size = [], STAMP_LEN
        for s in sensors:
            offs.append(size)
            size += s[3]
        self.recsize = size
        self.buf = bytearray(size * batch)
        self.mv = memoryview(self.buf)
        # Every (record, sensor) slot as a ready-made memoryview: the loop
        # never slices, so it never allocates.
        self.slots = [[self.mv[k * size + o:k * size + o + s[3]] for o, s in zip(offs, sensors)]
                      for k in range(batch)]
        self.zero = memoryview(bytes(max(s[3] for s in sensors) if sensors else 1))
        self.n = 0
        self.f = None
        self.errors = 0
        self.calib_cache = {}
        # Backoff: a sensor that keeps failing is skipped for a growing number
        # of samples, so an unplugged device costs the loop nothing instead of
        # one bus timeout per sample. Per-sensor counters are logged in the
        # health report.
        self.fails = [0] * len(sensors)      # consecutive failures
        self.skip = [0] * len(sensors)       # samples left to skip
        self.total_fail = [0] * len(sensors)
        self.samples = 0
        # Mux: one preallocated select byte per sensor; written only when the
        # channel actually changes between consecutive sensors.
        self.mux = [(s[6][0], bytes((1 << s[6][1],))) if len(s) > 6 and s[6] else None for s in sensors]
        # Access plan per sensor, resolved once: (register, address size, cmd)
        self.plan = []
        for s in sensors:
            reg = s[2]
            asz = 8
            if isinstance(reg, tuple):
                reg, asz = reg
            self.plan.append((reg, asz, s[7] if len(s) > 7 else None))

    def header(self):
        # Calibration blocks are read once here; a sensor that fails to answer
        # simply has no calib entry and the host logs raw values for it.
        calib = []
        self.calib_cache = {}
        for s in self.sensors:
            if len(s) > 5 and s[5] and self.i2c is not None:
                blob = b""
                try:
                    for reg, n in s[5]:
                        asz = 8
                        if isinstance(reg, tuple):
                            reg, asz = reg
                        blob += self.i2c.readfrom_mem(s[1], reg, n, addrsize=asz)
                    calib.append("%s:%s" % (s[0], _hex(blob)))
                    self.calib_cache[s[0]] = blob
                except OSError:
                    pass
        return "%s rec=%d fields=%s%s\n" % (
            MAGIC, self.recsize,
            ",".join("%s:%d:%s:%d:%s" % (s[0], s[1], _regname(s[2]), s[3], s[4]) for s in self.sensors),
            (" calib=" + ",".join(calib)) if calib else "")

    def sample(self, now_s, now_ms):
        k = self.n
        status = 0
        slots = self.slots[k]
        i2c = self.i2c
        last_mux = None
        for i, s in enumerate(self.sensors):
            if self.skip[i]:
                self.skip[i] -= 1
                status |= 1 << i
                slots[i][:] = self.zero[:s[3]]
                continue
            try:
                m = self.mux[i]
                if m is not None and m != last_mux:
                    i2c.writeto(m[0], m[1])
                    last_mux = m
                reg, asz, cmd = self.plan[i]
                if reg is None:
                    i2c.readfrom_into(s[1], slots[i])      # result of the previous cmd
                else:
                    i2c.readfrom_mem_into(s[1], reg, slots[i], addrsize=asz)
                if cmd is not None:
                    i2c.writeto(s[1], cmd)                 # start the next measurement
                self.fails[i] = 0
            except OSError:
                status |= 1 << i
                slots[i][:] = self.zero[:s[3]]
                self.fails[i] += 1
                self.total_fail[i] += 1
                b = 1 << (self.fails[i] - 1)
                self.skip[i] = b if b < MAX_BACKOFF else MAX_BACKOFF
        self.samples += 1
        if status:
            self.errors += 1
        struct.pack_into(STAMP, self.buf, k * self.recsize, now_s, now_ms, status)
        self.n = k + 1
        if self.n == self.batch:
            self.flush()

    def report(self):
        """One serial line: samples, and per-sensor failures (total, and how
        many samples a currently-failing sensor is being skipped for)."""
        parts = []
        for i, s in enumerate(self.sensors):
            state = ("skip %d" % self.skip[i]) if self.fails[i] else "ok"
            parts.append("%s:%d fails,%s" % (s[0], self.total_fail[i], state))
        print("sensorlog: %d samples, %d with errors | %s" % (self.samples, self.errors, " | ".join(parts)))

    def flush(self):
        if self.n and self.f:
            self.f.write(self.mv[:self.n * self.recsize])
            self.n = 0

    def sync(self):
        self.flush()
        if self.f:
            self.f.flush()
            try:
                os.sync()
            except AttributeError:
                pass

    def open(self, path):
        self.f = open(path, "wb")
        self.f.write(self.header())
        return path

    def close(self):
        if self.f:
            self.sync()
            self.f.close()
            self.f = None


# ---- display -----------------------------------------------------------------
# Turns the LAST record into two 16-character lines. This is the one place
# that formats text on the device; it runs every DISPLAY_S seconds, not per
# sample, and its few short strings are collected at the next quiet point.

def _bme280_tp(raw, cal):
    """Temperature (0.01 C) and humidity (0.01 %RH) from raw ADC bytes with
    the Bosch integer formulas - these two fit in 31-bit small ints, so they
    cost no allocation; pressure needs 64-bit math and is left to the host."""
    T1 = cal[0] | (cal[1] << 8); T2 = cal[2] | (cal[3] << 8); T3 = cal[4] | (cal[5] << 8)
    if T2 > 32767: T2 -= 65536
    if T3 > 32767: T3 -= 65536
    H1 = cal[25]; H2 = cal[26] | (cal[27] << 8); H3 = cal[28]
    if H2 > 32767: H2 -= 65536
    H4 = (cal[29] << 4) | (cal[30] & 0x0F); H5 = (cal[31] << 4) | (cal[30] >> 4); H6 = cal[32]
    if H6 > 127: H6 -= 256
    adc_t = (raw[3] << 12) | (raw[4] << 4) | (raw[5] >> 4)
    adc_h = (raw[6] << 8) | raw[7]
    v1 = (((adc_t >> 3) - (T1 << 1)) * T2) >> 11
    v2 = (((((adc_t >> 4) - T1) * ((adc_t >> 4) - T1)) >> 12) * T3) >> 14
    t_fine = v1 + v2
    temp = (t_fine * 5 + 128) >> 8
    h = t_fine - 76800
    a = (((adc_h << 14) - (H4 << 20) - (H5 * h)) + 16384) >> 15
    x = (h * H6) >> 10
    y = ((h * H3) >> 11) + 32768
    z = ((x * y) >> 10) + 2097152
    h = a * ((z * H2 + 8192) >> 14)
    h -= ((((h >> 15) * (h >> 15)) >> 7) * H1) >> 4
    h = 0 if h < 0 else 419430400 if h > 419430400 else h
    return temp, ((h >> 12) * 100) >> 10


class Display:
    def __init__(self, lg, addr):
        import serlcd
        self.lg = lg
        self.lcd = serlcd.SerLCD(addr)
        self.cal = None
        self.idx = {s[0]: i for i, s in enumerate(lg.sensors)}
        self.lcd.show("sensorlog", "starting...")

    def refresh(self):
        lg = self.lg
        k = lg.n - 1 if lg.n else lg.batch - 1      # most recently written record slot
        slots = lg.slots[k]
        i = self.idx.get("bme280")
        l1 = ""
        if i is not None and lg.calib_cache.get("bme280"):
            temp, hum = _bme280_tp(slots[i], lg.calib_cache["bme280"])
            l1 = "%d.%dC %d%%RH" % (temp // 100, (temp % 100) // 10, hum // 100)
        i = self.idx.get("sgp30")
        l2 = ""
        if i is not None:
            s = slots[i]
            l2 = "%dppm %dppb" % ((s[0] << 8) | s[1], (s[3] << 8) | s[4])
        i = self.idx.get("nfc_eh")
        if i is not None and slots[i][0] & 4:
            l1 = l1[:12] + " NFC"
        if lg.errors:
            l2 = l2[:13] + " E%d" % min(lg.errors, 99) if len(l2) <= 13 else l2
        self.lcd.show(l1, l2)


# ---- board side ------------------------------------------------------------

def _mount():
    import machine
    sd = machine.SDCard(**SD_PINS)
    os.mount(sd, MOUNT)
    return sd


def _next_path(base):
    n = 0
    for name in os.listdir(base):
        if name.startswith("slog") and name.endswith(".bin"):
            try:
                n = max(n, int(name[4:-4]) + 1)
            except ValueError:
                pass
    return "%s/slog%04d.bin" % (base, n)


def _storage():
    """Mount the card; without one, fall back to a directory on internal
    flash so the logger still runs (and says so)."""
    try:
        sd = _mount()
        return sd, MOUNT
    except OSError as e:
        print("sensorlog: no SD card (%s) - logging to %s on internal flash" % (e, FALLBACK_DIR))
        try:
            os.mkdir(FALLBACK_DIR)
        except OSError:
            pass
        return None, FALLBACK_DIR


def run(i2c=None, sensors=SENSORS, interval_ms=INTERVAL_MS, wdt_ms=WDT_MS):
    import machine
    if i2c is None:
        import i2c_esp32
        i2c = i2c_esp32.i2c
        # Say up front what is missing or conflicting, instead of logging
        # zeros for hours; mux-attached sensors are not visible to a scan.
        i2c_esp32.check([s[1] for s in sensors if len(s) <= 6])
    for addr, reg, data in INIT:
        try:
            if reg is None:
                i2c.writeto(addr, data)
            else:
                i2c.writeto_mem(addr, reg, data)
            time.sleep_ms(20)
        except OSError as e:
            print("sensorlog: init write to 0x%02x failed (%s) - is it connected?" % (addr, e))
    sd, base = _storage()
    lg = Logger(i2c, sensors)
    path = lg.open(_next_path(base))
    print("sensorlog: %d sensors, %d-byte records, %d per write -> %s" %
          (len(sensors), lg.recsize, lg.batch, path))
    wd = machine.WDT(timeout=wdt_ms) if wdt_ms else None
    disp = None
    if DISPLAY_S and DISPLAY_ADDR is not None:
        try:
            disp = Display(lg, DISPLAY_ADDR)
        except Exception as e:
            print("sensorlog: no display (%s) - logging without it" % e)
    last_sync = last_report = last_disp = time.time()
    next_t = time.ticks_ms()
    gc.collect()
    try:
        while True:
            now = time.time()
            try:
                lg.sample(now, time.ticks_ms() % 1000)
                if now - last_sync >= SYNC_S:
                    lg.sync()
                    last_sync = now
                    gc.collect()   # the loop allocates nothing; collect at a known quiet point
                if REPORT_S and now - last_report >= REPORT_S:
                    lg.report()
                    last_report = now
                if disp and now - last_disp >= DISPLAY_S:
                    try:
                        disp.refresh()
                    except Exception as e:   # a display bug must never stop logging
                        print("sensorlog: display refresh failed:", e)
                    last_disp = now
            except OSError as e:
                # card trouble: keep sampling into RAM, try to get the card back
                print("sensorlog: card error", e, "- remounting")
                try:
                    lg.close()
                except OSError:
                    pass
                if sd is not None:
                    try:
                        os.umount(MOUNT)
                    except OSError:
                        pass
                time.sleep_ms(500)
                try:
                    sd, base = _storage()
                    lg.open(_next_path(base))
                except OSError as e2:
                    print("sensorlog: reopen failed", e2)
            if wd:
                wd.feed()
            next_t = time.ticks_add(next_t, interval_ms)   # drift-free schedule
            delay = time.ticks_diff(next_t, time.ticks_ms())
            if delay > 0:
                time.sleep_ms(delay)
    except KeyboardInterrupt:
        lg.close()
        print("sensorlog: stopped, %d records with errors" % lg.errors)
