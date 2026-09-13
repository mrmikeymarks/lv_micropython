#!/usr/bin/env python3
"""Full pin probe for the ESP32 + ILI9341/XPT2046 build: exercises every pin the
project uses, from the board's own REPL, and prints a per-pin verdict.

    lvmp probe [PORT]        (or: python scripts/pinprobe.py /dev/cu.usbserial-XXXX)

What it checks, in order (about 30 s; follow the prompts on screen):
  14 panel power        level must read high
  15 backlight PWM      duty driven 0 -> full; the screen should blink
  19/18/13/12/4 display the screen cycles RED, GREEN, BLUE (visual check)
  touch SPI (T_DO=5, T_CLK=19, T_DIN=18, T_CS=25 or 27)
                        chip alive = temperature channel mid-range at 1 MHz;
                        then an 8 s window: press the screen, presses counted
  22/23 I2C             lines idle high (pull-ups), bus scan
  0 BOOT button         5 s window: press it, must read low while pressed
  26 T_IRQ (optional)   jumper T_IRQ to GPIO26: goes low on press if the chip is alive
  free pins 21 32 33 (and 25/27 if not touch CS): pull-up/down sanity -
                        a pin stuck high under pull-down is shorted to 3V3,
                        stuck low under pull-up is shorted to GND
The board is reset at the end so every pin returns to its normal driver.
Needs pyserial (the ESP-IDF venv python has it)."""

import sys
import time
import glob

try:
    import serial
except ImportError:
    sys.exit("pyserial missing: run via `lvmp probe` (uses the IDF venv python)")

BOARD_CODE = r'''
import time, gc, machine
from machine import Pin, I2C
import lvgl as lv
import hw_esp32
def row(pin, role, verdict, note): print("ROW|%s|%s|%s|%s" % (pin, role, verdict, note))
print("INFO|firmware|%s" % __import__("sys").implementation._machine)
print("INFO|reset cause|%d (1=power-on 3=soft 4=watchdog)" % machine.reset_cause())
gc.collect(); print("INFO|free heap|%d bytes" % gc.mem_free())
try: hw_esp32.disp.event_loop.disable(); print("INFO|lvgl event loop|paused for the probe")
except Exception as e: print("INFO|lvgl event loop|could not pause: %s" % e)
try: hw_esp32.touch.indev_drv.enable(False)
except Exception: pass

# ---- 14 panel power / 15 backlight ------------------------------------------
v14 = Pin(14).value()
row(14, "panel power", "OK" if v14 == 1 else "FAIL", "reads %d (expect 1)" % v14)
bl = hw_esp32.disp.bl
d_before = bl.duty_u16()
bl.duty_u16(0); time.sleep_ms(400); a = bl.duty_u16()
bl.duty_u16(65535); time.sleep_ms(400); b = bl.duty_u16()
bl.duty_u16(0); time.sleep_ms(400); bl.duty_u16(65535)
row(15, "backlight PWM", "OK" if a == 0 and b > 60000 else "FAIL",
    "duty %d -> %d -> %d; VISUAL: screen should have blinked twice" % (d_before, a, b))

# ---- display bus: colour cycle on the top layer -----------------------------
top = lv.layer_top()
sheet = lv.obj(top); sheet.set_size(lv.pct(100), lv.pct(100)); sheet.set_style_border_width(0, 0)
sheet.set_style_radius(0, 0); sheet.set_style_bg_opa(lv.OPA.COVER, 0)
for c in (0xFF0000, 0x00FF00, 0x0000FF):
    sheet.set_style_bg_color(lv.color_hex(c), 0); lv.refr_now(None); time.sleep_ms(500)
sheet.delete(); lv.refr_now(None)
row("19/18/13/12/4", "display SPI + ctrl", "VISUAL", "screen should have shown RED, GREEN, BLUE full-screen")

# ---- touch controller --------------------------------------------------------
spi = hw_esp32.spi
CH = {"T0": 0x00, "BAT": 0x20, "X": 0x50, "Y": 0x10, "Z1": 0x30}
buf = bytearray(3)
def rd(cs, chan):
    cs.value(0); buf[0] = 0x80 | chan; buf[1] = 0; buf[2] = 0
    spi.write_readinto(buf, buf); cs.value(1)
    return (buf[1] << 4) | (buf[2] >> 4)
spi.init(baudrate=1_000_000)
alive_cs = None
for gp in (25, 27):
    cs = Pin(gp, Pin.OUT, value=1)
    t0s = [rd(cs, CH["T0"]) for _ in range(8)]
    bat = rd(cs, CH["BAT"]); z = rd(cs, CH["Z1"])
    stuck = all(v in (0, 4095) for v in t0s)
    steady = max(t0s) - min(t0s) < 200
    ok = (not stuck) and steady and 150 < sum(t0s) // len(t0s) < 3900
    if ok and alive_cs is None: alive_cs = gp
    row(gp, "touch T_CS candidate", "OK" if ok else "FAIL",
        "temp channel %s (mid-range+steady = chip alive), bat %d, z1 %d" % (
            "%d..%d" % (min(t0s), max(t0s)), bat, z))
# Optional SPI-independent liveness check: jumper T_IRQ (PENIRQ) to GPIO26.
# A powered XPT2046 holds it high and pulls it low while the panel is pressed.
irq = Pin(26, Pin.IN, Pin.PULL_UP)
print("PROMPT|irq|PRESS THE SCREEN NOW for the T_IRQ check (4 s; only meaningful if T_IRQ is wired to GPIO26)")
lows = 0; t0 = time.ticks_ms()
while time.ticks_diff(time.ticks_ms(), t0) < 4000:
    lows += 1 - irq.value(); time.sleep_ms(20)
row(26, "T_IRQ (optional jumper)", "OK" if lows else "WARN",
    "%d low samples while pressing (0 = no PENIRQ seen: not wired, chip unpowered, or panel not pressed)" % lows)
if alive_cs is None:
    row("5/19/18", "touch T_DO/T_CLK/T_DIN", "FAIL", "chip never answered on CS 25 or 27: check T_DO->5, T_CLK->19, T_DIN->18, T_CS, and chip power")
else:
    cs = Pin(alive_cs, Pin.OUT, value=1)
    print("PROMPT|touch|PRESS AND HOLD SPOTS ON THE SCREEN NOW (8 s)")
    hits = 0; xs = []; ys = []; zmax = 0
    t0 = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), t0) < 8000:
        z1 = rd(cs, CH["Z1"]); zmax = max(zmax, z1)
        if z1 >= 16:
            x = rd(cs, CH["X"]); y = rd(cs, CH["Y"])
            if 50 < x < 4050 and 50 < y < 4050: hits += 1; xs.append(x); ys.append(y)
        time.sleep_ms(30)
    if hits:
        row("touch panel", "presses via CS %d" % alive_cs, "OK",
            "%d samples, raw x %d..%d, y %d..%d, z1 max %d" % (hits, min(xs), max(xs), min(ys), max(ys), zmax))
    else:
        row("touch panel", "presses via CS %d" % alive_cs, "FAIL", "chip alive but no press seen (z1 max %d): panel flex/pressure" % zmax)
spi.init(baudrate=24_000_000)

# ---- I2C 22/23 ----------------------------------------------------------------
scl = Pin(22, Pin.IN); sda = Pin(23, Pin.IN)
lv22 = scl.value(); lv23 = sda.value()
try:
    devs = I2C(0, scl=Pin(22), sda=Pin(23), freq=100_000).scan()
    note = "devices: %s" % ([hex(d) for d in devs] or "none")
except Exception as e:
    devs = None; note = "scan error: %s" % e
row("22/23", "I2C SCL/SDA", "OK" if lv22 and lv23 else "WARN",
    "idle SCL=%d SDA=%d (both 1 = pull-ups present); %s" % (lv22, lv23, note))

# ---- BOOT button ----------------------------------------------------------------
btn = Pin(0, Pin.IN, Pin.PULL_UP)
print("PROMPT|boot|PRESS THE BOOT BUTTON NOW (5 s)")
lows = 0; t0 = time.ticks_ms()
while time.ticks_diff(time.ticks_ms(), t0) < 5000:
    lows += 1 - btn.value(); time.sleep_ms(20)
row(0, "BOOT button", "OK" if lows else "WARN", "%d low samples (0 = never pressed)" % lows)

# ---- free pins: short-to-rail check ---------------------------------------------
free = [g for g in (21, 32, 33, 25, 27) if g != alive_cs]
for g in free:
    up = sum(Pin(g, Pin.IN, Pin.PULL_UP).value() for _ in range(20))
    dn = sum(Pin(g, Pin.IN, Pin.PULL_DOWN).value() for _ in range(20))
    if up == 20 and dn == 0: v, n = "OK", "floats (free to use)"
    elif dn == 20: v, n = "WARN", "reads high under pull-down: shorted to 3V3 or driven"
    elif up == 0: v, n = "WARN", "reads low under pull-up: shorted to GND or driven"
    else: v, n = "WARN", "unstable (%d/20 up, %d/20 down)" % (up, dn)
    row(g, "free pin", v, n)
print("DONE")
time.sleep_ms(300)
machine.reset()
'''


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else (glob.glob("/dev/cu.usbserial*") or [None])[0]
    if not port:
        sys.exit("no /dev/cu.usbserial* device found; pass the port")
    p = serial.Serial(port, 115200, timeout=0.3)
    # Opening the port toggles DTR/RTS, which can drop the board into ROM
    # download mode. Force a clean run-mode reset (EN pulse with IO0 high),
    # then wait for the REPL banner instead of guessing a boot time.
    p.dtr = False; p.rts = True; time.sleep(0.1); p.rts = False
    seen, t0 = b"", time.time()
    while time.time() - t0 < 15:
        seen += p.read(65536)
        if b">>>" in seen:
            break
    else:
        sys.exit("no REPL prompt on %s within 15 s after reset (last output: %r)" % (port, seen[-120:]))
    for _ in range(6):
        p.write(b"\x03\r\n"); time.sleep(0.5)
        if b">>>" in p.read(65536):
            break
    p.write(b"\x05"); time.sleep(0.3)
    code = BOARD_CODE.replace("\n", "\r\n").encode()
    for i in range(0, len(code), 64):          # pace the paste: the REPL's UART
        p.write(code[i:i + 64]); time.sleep(0.03)   # RX buffer is only 256 bytes
        p.read(65536)                            # and it echoes everything back
    time.sleep(0.5)
    p.write(b"\x04")
    rows, deadline, buf, raw = [], time.time() + 60, "", ""
    print("probing %s ..." % port)
    while time.time() < deadline:
        chunk = p.read(65536).decode("utf-8", "replace")
        if chunk:
            buf += chunk; raw += chunk
            while "\n" in buf:
                line, buf = buf.split("\n", 1)
                line = line.strip()
                if line.startswith("PROMPT|"):
                    print(">>> " + line.split("|", 2)[2], flush=True)
                elif line.startswith(("ROW|", "INFO|")):
                    rows.append(line.split("|"))
                elif line.startswith("DONE"):
                    deadline = 0
                elif "Traceback" in line or "Error" in line:
                    print("board error: " + line)
    p.close()
    print()
    for r in rows:
        if r[0] == "INFO":
            print("  %-18s %s" % (r[1], r[2]))
    print()
    print("  %-16s %-26s %-7s %s" % ("PIN", "ROLE", "RESULT", "NOTE"))
    for r in rows:
        if r[0] == "ROW":
            print("  %-16s %-26s %-7s %s" % (r[1], r[2], r[3], r[4]))
    bad = [r for r in rows if r[0] == "ROW" and r[3] == "FAIL"]
    print()
    if not any(r[0] == "ROW" for r in rows):
        print("--- raw transcript tail ---")
        print(raw[-1500:])
        sys.exit("probe produced no results (see transcript) - reset the board and try again")
    print("board reset. %s" % ("all checks passed (verify the VISUAL rows yourself)" if not bad
                              else "%d FAIL row(s) above" % len(bad)))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
