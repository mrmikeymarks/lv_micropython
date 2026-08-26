freeze("$(PORT_DIR)/modules")
include("$(MPY_DIR)/extmod/asyncio")

# LVGL helpers and generic pure-Python display/touch drivers, frozen from the
# binding so boards don't need filesystem copies (faster imports, less heap).
module("lv_utils.py", base_path="$(MPY_DIR)/user_modules/lv_binding_micropython/lib")
module("fs_driver.py", base_path="$(MPY_DIR)/user_modules/lv_binding_micropython/lib")
module("st77xx.py", base_path="$(MPY_DIR)/user_modules/lv_binding_micropython/driver/generic")
module("ili9xxx.py", base_path="$(MPY_DIR)/user_modules/lv_binding_micropython/driver/generic")
# xpt2046 is frozen from ports/esp32/modules/ (patched copy with light polling)

# Useful networking-related packages.
require("bundle-networking")

# Require some micropython-lib modules.
require("aioespnow")
require("dht")
require("ds18x20")
require("neopixel")
require("onewire")
require("umqtt.robust")
require("umqtt.simple")
require("upysh")
