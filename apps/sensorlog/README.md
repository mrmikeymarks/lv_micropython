# sensorlog — I2C sensor chain → SD card, for a no-PSRAM ESP32

Reads every sensor on the I2C bus at a fixed interval and appends fixed-size
binary records to a microSD card. Built for a board with ~100 KB of heap:
the sampling loop allocates nothing, the card is written in batches, and
the ESP32 never formats or scales a value — that happens on your computer.

## Wiring

| Signal | GPIO | Note |
|---|---|---|
| I2C SCL | 22 | 400 kHz, from `i2c_esp32.py` — every sensor shares these two |
| I2C SDA | 23 | |
| SD SCK | 21 | the card gets its **own** SPI host (slot 3 / VSPI); the display and touch own the other one |
| SD MOSI | 32 | |
| SD MISO | 25 | |
| SD CS | 27 | |

The microSD socket on the back of the 2.8" ILI9341 module exposes exactly
these four SD pins (`SD_SCK`, `SD_MOSI`, `SD_MISO`, `SD_CS`). Pull-ups on
SCL/SDA: most breakout sensors include them; if `i2c_esp32.scan()` finds
nothing, add 4.7 kΩ to 3.3 V on each line. Card: FAT32, any size.

## Adding sensors to the Qwiic chain

The bus is shared: every device you daisy-chain changes its electrical
behaviour, and the failure modes are quiet (reads that time out, values
that are stale or zero), so the logger checks and reports rather than
trusting the chain.

**Electrical rules.** Qwiic/STEMMA boards each carry their own pull-ups
(2.2 kΩ is typical, 4.7 kΩ or 10 kΩ on some). Pull-ups add in parallel: two
2.2 kΩ boards make 1.1 kΩ, three make 0.73 kΩ — below the ~1 kΩ the I²C
spec allows at 3.3 V, and devices start failing to pull SDA low. Cut the
I²C jumper on all but one or two boards. Cable capacitance (~50 pF/m) slows
the edges; keep the whole chain under about a metre at 400 kHz, or set
`FREQ = 100_000` in `i2c_esp32.py` for longer runs. Two devices with the
same address (two BME280s, two ADS1115s…) cannot share a bus: change one
with its address jumper, or put them behind a TCA9548A mux and give each a
channel in the table (`("bme_out", 0x77, 0xF7, 8, ">HBHBH", calib, (0x70, 2))`).
Everything is 3.3 V — never mix in a 5 V board without a level shifter.

**What the code does about it.** `i2c_esp32` clocks the bus free at boot if
a device is holding SDA low (the classic "bus stuck after a reset" fault),
records whether both lines idled high (missing pull-ups show up here), and
sets a 10 ms device timeout instead of the 50 ms default so a dead device
costs little. `sensorlog.run()` compares the sensor table to a bus scan at
start and prints what is missing or duplicated. During logging, a sensor
that fails is retried after 1, 2, 4… up to 64 samples (its status bit is
set and its slot zeroed meanwhile), so an unplugged device costs the loop
almost nothing and a healthy one is read every sample. Each sensor is one
contiguous register-block read — never split a sensor into several reads.
Mux channels are written only when the channel changes between consecutive
sensors, so ordering same-channel sensors together costs one select write
per sample. Every `REPORT_S` seconds a health line goes to serial with
per-sensor failure counts and current backoff, so a chain problem is visible
on the console — and in the data — without you watching the board.

## This chain

Identified on the bus (`i2c_esp32.scan()`): **BME280** at 0x77 (id 0x60),
**SGP30** VOC/eCO₂ at 0x58 (command-based, confirmed by its serial-ID reply
with valid CRCs), and an **ST25DV** NFC tag at 0x53/0x57 (Type-5 NDEF
capability container `E1 40`, ST UID `E0 02 …`). The shipped `SENSORS`
table logs all of them, 17 bytes per record:

| entry | what is logged | decoded columns |
|---|---|---|
| `bme280` | 8 raw ADC bytes; calibration in the header | `_degC`, `_hPa`, `_RH` |
| `sgp30` | eCO₂ + CRC, TVOC + CRC from `measure_iaq` | `_eCO2_ppm`, `_TVOC_ppb` (blank on CRC failure) |
| `nfc_eh` | `EH_CTRL_Dyn`; the tag's first 64 NDEF bytes in the header | `_field` (1 while an RF reader's field is on) |
| `nfc_it` | `IT_STS_Dyn`, RF events since the last sample | `_events` (`activity`, `write`, `field_on`, …) |

The SGP30 is *pipelined*: each sample reads the previous second's result,
then immediately issues the next `measure_iaq`, so its 12 ms conversion
never stalls the loop — and the 1 s cadence is exactly what its baseline
algorithm wants (the first ~15 s read 400 ppm / 0 ppb while it warms up).
The ST25DV's registers live behind 16-bit addresses; the table's `(reg, 16)`
form handles that. Its `IT_STS_Dyn` register clears on read, so each record
holds the events of that one interval.

## The LCD (SparkFun Qwiic SerLCD 16x2)

The SerLCD on this chain sits at **0x2D** (its factory address is 0x72;
`serlcd.SerLCD().set_address()` changes it). It is an AVR-based board that
stretches the I²C clock while its firmware digests each byte, and the
ESP32's *hardware* I²C master NACKs it at any speed — a bit-banged SoftI²C
at 100 kHz works. So `serlcd.py` borrows the bus pins for the few
milliseconds of each write and hands them back to the hardware bus
(`i2c_esp32.restore()`, ~1.2 ms): the sensors keep their 400 kHz hardware
bus and the display costs nothing between refreshes. The logger refreshes
it every `DISPLAY_S` seconds (default 2) with temperature and humidity
(computed on-device with the Bosch integer formulas — they fit in small
ints; pressure needs 64-bit math and is left to the host), eCO₂/TVOC, an
`NFC` marker while a reader's field is present, and an `E<n>` error count.
Set `DISPLAY_ADDR = None` to run without it; an unplugged display is
counted, not fatal.

## Configure

Edit the `SENSORS` table at the top of
[ports/esp32/modules/sensorlog.py](../../ports/esp32/modules/sensorlog.py):
one line per device — name, I2C address, first register, number of bytes,
the `struct` format of those bytes, and optionally the calibration
registers to capture once into the file header. Anything readable as a
register block works (LM75/TMP102, INA219, BME280, ADS1115, MPU6050…).
`INIT` holds one-time register writes some sensors need before they produce
data. The shipped default is the **BME280 found on this board at 0x77**
(chip id 0x60), with its mode/oversampling init and its two calibration
blocks, so `decode.py` outputs real °C / hPa / %RH columns next to the raw
ADC words.
`INTERVAL_MS`, `BATCH`, `SYNC_S`, and `WDT_MS` tune rate, write batching,
flush interval, and the watchdog. Find addresses with:

```python
import i2c_esp32; i2c_esp32.scan()
```

## Run

The module is frozen into the firmware (`lvmp flash`), so `main.py` on the
board is one line:

```python
import sensorlog; sensorlog.run()
```

Each boot opens a new `/sd/slogNNNN.bin` (with no card present it logs to `/log/` on internal flash instead, and says so on serial). Ctrl-C at the REPL stops it
cleanly (buffer flushed, file closed). A failing sensor sets its status bit
in that record and its bytes are zeroed; a failing card is remounted with
backoff while sampling continues; the watchdog reboots a wedged board.

## Read the data

```bash
python3 apps/sensorlog/decode.py /Volumes/SD/slog0000.bin > data.csv
```

The file is self-describing (its first line carries the sensor table), so
`decode.py` needs no configuration. Columns are UTC time, epoch seconds,
milliseconds, the status bitmask, then one column per struct field per
sensor; a sensor's fields are empty on records where it failed. Values are
raw register values — apply each sensor's scaling in your analysis. For a
`bme280` entry with calibration in the header, three compensated columns
(`_degC`, `_hPa`, `_RH`, Bosch's integer algorithm) are added.

## Cost per record (defaults)

7-byte stamp + the sensors' bytes: with the example table that is 19 bytes
per record, 608 bytes per card write (every 32 s at 1 Hz), ~1.6 MB per day.
A 1 GB card holds about 600 days. Data at risk on power loss: at most
`SYNC_S` seconds.

## Check without hardware

```bash
cd apps/sensorlog && ../../ports/unix/build-standard/micropython sim_check.py
```

Runs the real logger against a fake bus (one sensor drops out every 7th
sample) and verifies header, record layout, error bits, byte-exact sensor
slots, and that the sampling loop grows the heap by zero bytes.
