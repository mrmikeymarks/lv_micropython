#!/usr/bin/env python3
"""Decode a sensorlog .bin file (from the ESP32's SD card) into CSV on stdout.

    python3 apps/sensorlog/decode.py /Volumes/SD/slog0000.bin > data.csv

The file is self-describing: its first line names each sensor and the struct
format of its raw bytes, so no configuration is needed here. Records whose
status bit is set for a sensor are printed with that sensor's fields empty
(the logger zeroes bytes it could not read). Values are RAW register values;
apply the sensor's own scaling in your analysis."""

import struct
import sys
from datetime import datetime, timezone

STAMP = "<IHB"


def crc8(data):
    """Sensirion CRC-8 (poly 0x31, init 0xFF) used by the SGP30."""
    crc = 0xFF
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = ((crc << 1) ^ 0x31) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
    return crc


def sgp30(raw):
    """eCO2 ppm and TVOC ppb from measure_iaq's 6 bytes; a word whose CRC
    fails is left empty rather than logged as a wrong number."""
    out = []
    for i in (0, 3):
        word, crc = raw[i:i + 2], raw[i + 2]
        out.append(str(int.from_bytes(word, "big")) if crc8(word) == crc else "")
    return out


NFC_BITS = ("user", "activity", "interrupt", "field_off", "field_on", "put_msg", "get_msg", "write")


def nfc_events(v):
    return "+".join(n for i, n in enumerate(NFC_BITS) if v & (1 << i))


def ndef_text(blob):
    """Best-effort readable rendering of a Type-5 NDEF area (CC + message)."""
    return "".join(chr(b) if 32 <= b < 127 else "." for b in blob).rstrip(".")


def bme280(raw, cal):
    """Bosch compensation (datasheet 4.2.3), integer form, from the 8 raw
    bytes F7..FE and the 33 calibration bytes (0x88..0xA1 + 0xE1..0xE7)."""
    T1, T2, T3, P1, P2, P3, P4, P5, P6, P7, P8, P9, _, H1 = struct.unpack("<HhhHhhhhhhhhBB", cal[:26])
    H2, H3, e4, e5, e6, H6 = struct.unpack("<hBBBBb", cal[26:33])
    H4 = (e4 << 4) | (e5 & 0x0F)
    H5 = (e6 << 4) | (e5 >> 4)
    adc_p = (raw[0] << 12) | (raw[1] << 4) | (raw[2] >> 4)
    adc_t = (raw[3] << 12) | (raw[4] << 4) | (raw[5] >> 4)
    adc_h = (raw[6] << 8) | raw[7]
    v1 = (((adc_t >> 3) - (T1 << 1)) * T2) >> 11
    v2 = (((((adc_t >> 4) - T1) * ((adc_t >> 4) - T1)) >> 12) * T3) >> 14
    t_fine = v1 + v2
    temp = ((t_fine * 5 + 128) >> 8) / 100.0
    v1 = t_fine - 128000
    v2 = v1 * v1 * P6 + ((v1 * P5) << 17) + (P4 << 35)
    v1 = ((v1 * v1 * P3) >> 8) + ((v1 * P2) << 12)
    v1 = ((1 << 47) + v1) * P1 >> 33
    if v1 == 0:
        press = 0.0
    else:
        p = 1048576 - adc_p
        p = ((p << 31) - v2) * 3125 // v1
        v1 = (P9 * (p >> 13) * (p >> 13)) >> 25
        v2 = (P8 * p) >> 19
        press = (((p + v1 + v2) >> 8) + (P7 << 4)) / 256.0 / 100.0
    h = t_fine - 76800
    a = (((adc_h << 14) - (H4 << 20) - (H5 * h)) + 16384) >> 15
    x = (h * H6) >> 10
    y = ((h * H3) >> 11) + 32768
    z = ((x * y) >> 10) + 2097152
    h = a * ((z * H2 + 8192) >> 14)
    h -= ((((h >> 15) * (h >> 15)) >> 7) * H1) >> 4
    h = max(0, min(h, 419430400))
    return temp, press, (h >> 12) / 1024.0


def decode(path, out=sys.stdout):
    with open(path, "rb") as f:
        head = f.readline().decode().strip().split()
        if not head or head[0] != "SLOG1":
            sys.exit("%s: not a SLOG1 file" % path)
        recsize = int(head[1].split("=")[1])
        fields = []
        for spec in head[2].split("=", 1)[1].split(","):
            name, addr, reg, n, fmt = spec.split(":")   # reg may be 'cmd' or 'N/16'
            fields.append((name, int(n), fmt, struct.calcsize(fmt)))
        calib = {}
        for part in head[3:]:
            if part.startswith("calib="):
                for item in part[6:].split(","):
                    name, blob = item.split(":")
                    calib[name] = bytes.fromhex(blob)
        cols = ["time_utc", "epoch_s", "ms", "status"]
        for name, n, fmt, _ in fields:
            k = len(struct.unpack(fmt, bytes(n)))
            cols += [name if k == 1 else "%s_%d" % (name, i) for i in range(k)]
            if name in calib and name.startswith("bme280"):
                cols += [name + "_degC", name + "_hPa", name + "_RH"]
            elif name.startswith("sgp30"):
                cols += [name + "_eCO2_ppm", name + "_TVOC_ppb"]
            elif name.startswith("nfc_eh"):
                cols += [name + "_field"]
            elif name.startswith("nfc_it"):
                cols += [name + "_events"]
        for name, blob in calib.items():
            if name.startswith("nfc"):
                sys.stderr.write("%s: NDEF memory: %s\n" % (name, ndef_text(blob)))
        out.write(",".join(cols) + "\n")
        count = 0
        while True:
            rec = f.read(recsize)
            if len(rec) < recsize:
                break
            t, ms, status = struct.unpack_from(STAMP, rec, 0)
            row = [datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
                   str(t), str(ms), str(status)]
            off = struct.calcsize(STAMP)
            for i, (name, n, fmt, size) in enumerate(fields):
                vals = struct.unpack(fmt, rec[off:off + size])
                failed = status & (1 << i)
                row += [""] * len(vals) if failed else [str(v) for v in vals]
                if name in calib and name.startswith("bme280"):
                    row += [""] * 3 if failed else ["%.2f" % v for v in bme280(rec[off:off + n], calib[name])]
                elif name.startswith("sgp30"):
                    row += [""] * 2 if failed else sgp30(rec[off:off + n])
                elif name.startswith("nfc_eh"):
                    row += [""] if failed else [str((vals[0] >> 2) & 1)]
                elif name.startswith("nfc_it"):
                    row += [""] if failed else [nfc_events(vals[0])]
                off += n
            out.write(",".join(row) + "\n")
            count += 1
    return count


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    n = decode(sys.argv[1])
    sys.stderr.write("%d records\n" % n)
