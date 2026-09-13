# I2C bring-up companion to hw_esp32.py (Qwiic / STEMMA QT chains).
# Importing this module recovers a stuck bus if needed, then configures
# hardware I2C(0) on pins chosen to avoid the display/touch SPI wiring:
#   scl=22 sda=23 @ 400kHz, 10 ms device timeout
# Usage:
#   import i2c_esp32
#   i2c_esp32.scan()                  # list attached device addresses
#   i2c_esp32.check((0x77, 0x48))     # bus health: pull-ups, stuck lines, missing/duplicate devices
#   dev = i2c_esp32.i2c               # pass to any driver taking machine.I2C
#
# Chain rules (see apps/sensorlog/README.md): every Qwiic board adds its own
# pull-ups (usually 2.2k); more than two boards in parallel is below the
# 1k the spec allows - cut the I2C jumper on all but one or two. Keep the
# chain short (under ~1 m at 400 kHz, drop FREQ to 100_000 beyond that).

from machine import I2C, Pin
import time

SCL = 22
SDA = 23
FREQ = 400_000
TIMEOUT_US = 10_000   # a missing or dead device costs at most this per read (driver default: 50 ms)

idle_ok = None        # set by recover(): both lines read high before init (pull-ups present)


def recover():
    """Free a bus a device is holding low (an interrupted transaction) by
    clocking SCL up to 9 times until SDA releases, then issuing a STOP.
    Runs before the I2C peripheral owns the pins; returns pulses used."""
    global idle_ok
    scl = Pin(SCL, Pin.OPEN_DRAIN, value=1)
    sda = Pin(SDA, Pin.OPEN_DRAIN, value=1)
    time.sleep_us(20)
    idle_ok = bool(scl.value() and sda.value())
    if sda.value():
        return 0
    n = 0
    for n in range(1, 10):
        scl.value(0); time.sleep_us(5)
        scl.value(1); time.sleep_us(5)
        if sda.value():
            break
    sda.value(0); time.sleep_us(5)   # STOP: SDA low -> high while SCL high
    scl.value(1); time.sleep_us(5)
    sda.value(1); time.sleep_us(5)
    return n


recover()
i2c = I2C(0, scl=Pin(SCL), sda=Pin(SDA), freq=FREQ, timeout=TIMEOUT_US)


def restore():
    """Re-bind the hardware I2C to its pins after something else (a SoftI2C
    for a clock-stretching slave, see serlcd.py) borrowed them. The ESP32
    port returns the same singleton object, so every existing reference to
    `i2c` stays valid. Costs about 1.2 ms."""
    return I2C(0, scl=Pin(SCL), sda=Pin(SDA), freq=FREQ, timeout=TIMEOUT_US)


def scan(verbose=True):
    found = i2c.scan()
    if verbose:
        if found:
            for addr in found:
                print("I2C device at 0x%02x" % addr)
        else:
            print("no I2C devices found (scl=%d sda=%d)" % (SCL, SDA))
    return found


def check(expected=(), verbose=True):
    """Bus health report. `expected`: addresses the application needs.
    Returns (found, missing, duplicates_in_expected)."""
    found = i2c.scan()
    missing = [a for a in expected if a not in found]
    dups = sorted({a for a in expected if list(expected).count(a) > 1})
    if verbose:
        print("I2C bus scl=%d sda=%d @ %d kHz: %s" % (SCL, SDA, FREQ // 1000,
              "lines idle high (pull-ups present)" if idle_ok else
              "a line was LOW at start - missing pull-ups or a held bus (recovery attempted)"))
        print("  found   : %s" % (" ".join("0x%02x" % a for a in found) or "nothing"))
        if expected:
            print("  missing : %s" % (" ".join("0x%02x" % a for a in missing) or "none"))
        if dups:
            print("  CONFLICT: %s used by more than one sensor - use an address jumper or a mux channel"
                  % " ".join("0x%02x" % a for a in dups))
        if len(found) > 4 and FREQ > 100_000:
            print("  note: %d devices - if reads are flaky, set FREQ = 100_000 or cut extra pull-ups" % len(found))
    return found, missing, dups
