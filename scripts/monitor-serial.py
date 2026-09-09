#!/usr/bin/env python3
"""Serial monitor/terminal for ESP32 boards.

Interactive by default when run from a terminal: output streams from the
board AND your keystrokes are sent to it, so you can use the MicroPython
REPL directly. Ctrl-] quits the monitor; Ctrl-C is passed through to the
board (interrupts running code, like idf.py monitor).

Attaches without resetting the board (DTR/RTS held de-asserted on open),
auto-detects the port, survives unplug/replug by reconnecting, and can
hard-reset the board on attach to capture the full boot log.

When stdin is not a terminal (piped/scripted use) or with --read-only, it
is a pure viewer: nothing is ever written to the board and Ctrl-C quits.

Needs pyserial. Run with any python that has it, e.g. the ESP-IDF env:
    source scripts/env-variables-esp32.sh
    python scripts/monitor-serial.py [--reset] [--timestamps] [--read-only] [port] [baud]
"""

import argparse
import glob
import os
import select
import sys
import time

try:
    import serial
except ImportError:
    sys.exit(
        "pyserial not found. Run inside the ESP-IDF environment "
        "(source scripts/env-variables-esp32.sh) or `pip install pyserial`."
    )

PORT_PATTERNS = [
    "/dev/cu.usbserial*",
    "/dev/cu.SLAB_USBtoUART*",
    "/dev/cu.wchusbserial*",
    "/dev/cu.usbmodem*",
    "/dev/ttyUSB*",
    "/dev/ttyACM*",
]

QUIT_KEY = b"\x1d"  # Ctrl-]


def find_port():
    for pattern in PORT_PATTERNS:
        ports = sorted(glob.glob(pattern))
        if ports:
            return ports[0]
    return None


def open_port(port, baud):
    # Configure before open so DTR/RTS never pulse (a pulse resets the board
    # or drops it into the bootloader on common USB-UART adapters).
    s = serial.Serial()
    s.port = port
    s.baudrate = baud
    s.timeout = 0.05
    s.dtr = False
    s.rts = False
    # exclusive lock: flashing tools get a clean "port busy" error instead of
    # silently corrupted transfers from two readers on one device
    s.exclusive = True
    s.open()
    return s


def hard_reset(s):
    # Pulse EN low via RTS, the same sequence esptool uses for a hard reset.
    s.dtr = False
    s.rts = True
    time.sleep(0.1)
    s.rts = False


def pump(s, args, interactive, state):
    """Stream serial->stdout and, when interactive, stdin->serial.

    Returns False when the user asked to quit, True on serial disconnect.
    """
    stdin_fd = sys.stdin.fileno() if interactive else None
    while True:
        try:
            data = s.read(256)
        except serial.SerialException:
            return True
        if data:
            text = data.decode("utf-8", "replace")
            if args.timestamps:
                stamp = time.strftime("[%H:%M:%S] ")
                out = []
                for ch in text:
                    if state["line_start"]:
                        out.append(stamp)
                        state["line_start"] = False
                    out.append(ch)
                    if ch == "\n":
                        state["line_start"] = True
                text = "".join(out)
            sys.stdout.write(text)
            sys.stdout.flush()
        if interactive:
            r, _, _ = select.select([stdin_fd], [], [], 0)
            if r:
                keys = os.read(stdin_fd, 64)
                if QUIT_KEY in keys:
                    return False
                if keys:
                    try:
                        s.write(keys)
                    except serial.SerialException:
                        return True


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("port", nargs="?", help="serial device (default: auto-detect)")
    ap.add_argument("baud", nargs="?", type=int, default=115200, help="baud rate (default 115200)")
    ap.add_argument("--reset", action="store_true", help="hard-reset the board on attach to capture the boot log")
    ap.add_argument("--timestamps", action="store_true", help="prefix each line with a timestamp")
    ap.add_argument("--read-only", action="store_true", help="never send keystrokes to the board (pure viewer)")
    args = ap.parse_args()

    interactive = sys.stdin.isatty() and not args.read_only
    old_termios = None
    if interactive:
        import termios
        import tty

        stdin_fd = sys.stdin.fileno()
        old_termios = termios.tcgetattr(stdin_fd)
        # raw mode: keys reach the board unmodified; Ctrl-C goes to the board
        tty.setraw(stdin_fd, termios.TCSADRAIN)

    want_reset = args.reset
    state = {"line_start": True}
    try:
        while True:
            port = args.port or find_port()
            if not port:
                print("waiting for a serial device...\r", file=sys.stderr)
                time.sleep(1)
                continue
            try:
                s = open_port(port, args.baud)
            except serial.SerialException as e:
                print(f"cannot open {port} ({e}); retrying...\r", file=sys.stderr)
                time.sleep(1)
                continue

            if interactive:
                banner = (
                    f"--- monitor {port} @ {args.baud} | keys go to the board | Ctrl-] quits ---\r"
                )
            else:
                banner = (
                    f"--- monitoring {port} @ {args.baud} (read-only viewer, Ctrl-C to quit) ---\r"
                )
            print(banner, file=sys.stderr)
            if want_reset:
                hard_reset(s)
                want_reset = False  # only reset on the first attach, not reconnects
            try:
                disconnected = pump(s, args, interactive, state)
            except KeyboardInterrupt:
                print("\r\n--- monitor stopped ---", file=sys.stderr)
                return
            finally:
                try:
                    s.close()
                except Exception:
                    pass
            if not disconnected:
                print("\r\n--- monitor stopped ---", file=sys.stderr)
                return
            print(f"\r\n--- {port} disconnected; waiting for it to return ---\r", file=sys.stderr)
            time.sleep(1)
    finally:
        if old_termios is not None:
            import termios

            termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, old_termios)


if __name__ == "__main__":
    main()
