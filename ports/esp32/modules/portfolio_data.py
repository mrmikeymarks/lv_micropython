# Frozen flat-module build of portfolio/data.py (see apps/portfolio/ for the
# filesystem-installable package variant; keep the two in sync).
# All portfolio content lives here - EDIT THIS FILE to make it yours.
# Keep strings short: the screen is 320x240 and everything below is measured
# to fit it. Symbols come from lv.SYMBOL (referenced by name at build time).

PORTFOLIO = {
    # ---- identity -------------------------------------------------- EDIT ME
    "name": "garzarobm",
    "role": "Embedded Systems Developer",
    "tagline": "Building tiny machines with big personalities",
    "location": "Earth, mostly at a soldering bench",
    "email": "robjects@protonmail.com",
    "website": "https://github.com/garzarobm",
    "github": "garzarobm",
    # ---- quick stats shown on the home page ------------------------ EDIT ME
    "stats": (
        ("Years", "10+"),
        ("Projects", "24"),
        ("Bricked", "3"),
    ),
    # ---- about ----------------------------------------------------- EDIT ME
    "bio": (
        "I design and ship firmware for microcontrollers - from bare-metal "
        "C to MicroPython UIs like the one you are poking right now.",
        "Happiest at the boundary where hardware meets software: display "
        "buses, touch controllers, RTOS scheduling, and squeezing UIs into "
        "boards with no PSRAM.",
    ),
    "facts": (
        ("HOME", "Based wherever the bench is"),
        ("EDIT", "Vim keybindings everywhere"),
        ("CHARGE", "Runs on cold brew"),
        ("WIFI", "Fluent in AT commands"),
    ),
    # ---- skills (0-100) -------------------------------------------- EDIT ME
    "skills": (
        ("MicroPython", 92),
        ("C / C++", 88),
        ("Python", 90),
        ("LVGL UI", 85),
        ("ESP-IDF", 80),
        ("FreeRTOS", 74),
        ("KiCad / PCB", 65),
        ("Rust", 45),
    ),
    # ---- stack chips grouped for the tools page -------------------- EDIT ME
    "stack": (
        ("Embedded", ("ESP32", "STM32", "RP2040", "nRF52", "ARM Cortex-M")),
        ("Firmware", ("MicroPython", "ESP-IDF", "FreeRTOS", "LVGL 9", "Zephyr")),
        ("Desktop & Cloud", ("Linux", "Docker", "Git", "CI/CD", "MQTT")),
        ("Hardware", ("KiCad", "Logic analyzers", "Oscilloscope", "SMD rework")),
    ),
    # ---- projects --------------------------------------------------- EDIT ME
    "projects": (
        {
            "name": "lv_micropython dev workflow",
            "desc": "One-shot build/flash/verify pipeline for ESP32 LVGL "
                    "firmware with frozen display drivers.",
            "tech": ("ESP32", "LVGL", "CI"),
            "stars": 4,
        },
        {
            "name": "ILI9341 touch bring-up",
            "desc": "Display + XPT2046 resistive touch driver tuning: SPI "
                    "sharing, polling, and calibration.",
            "tech": ("SPI", "Drivers"),
            "stars": 5,
        },
        {
            "name": "This portfolio",
            "desc": "10-page interactive resume running on the device it "
                    "was written for. You are here.",
            "tech": ("MicroPython", "LVGL 9"),
            "stars": 5,
        },
        {
            "name": "ESP-NOW sensor mesh",
            "desc": "Battery-powered sensor nodes with a bedside LVGL "
                    "dashboard head unit.",
            "tech": ("ESP-NOW", "Low power"),
            "stars": 4,
        },
    ),
    # ---- experience timeline (newest first) ------------------------- EDIT ME
    "experience": (
        ("2023-now", "Senior Embedded Developer", "Freelance",
         "Firmware, display UIs, and driver bring-up for client hardware."),
        ("2019-2023", "Embedded Software Engineer", "IoT startup",
         "Shipped ESP32 fleet firmware, OTA updates, and factory tooling."),
        ("2016-2019", "Software Engineer", "Systems shop",
         "Linux services and test rigs; drifted steadily closer to the metal."),
        ("2014-2016", "Jr. Developer", "First real job",
         "Learned that the bug is always in your own code."),
    ),
    # ---- open source / github page ---------------------------------- EDIT ME
    "oss": {
        "contribs": (12, 30, 48, 61, 85, 120, 96),  # per year, oldest first
        "years": ("'19", "'20", "'21", "'22", "'23", "'24", "'25"),
        "repos": (
            ("lv_micropython", "fork, ESP32 workflow"),
            ("lv_binding_micropython", "driver patches"),
            ("micropython", "small fixes"),
        ),
    },
    # ---- talks / media ---------------------------------------------- EDIT ME
    "media": (
        ("VIDEO", "Talk", "MicroPython UIs that fit in 100 KB", "2025"),
        ("VIDEO", "Demo", "LVGL 9 on a $6 dev board", "2024"),
        ("AUDIO", "Podcast", "Guest: life without printf", "2024"),
        ("FILE", "Blog", "Frozen modules, thawed iteration speed", "2025"),
        ("FILE", "Blog", "SPI bus sharing without tears", "2023"),
        ("IMAGE", "Gallery", "Bench photos & build logs", "ongoing"),
    ),
    # ---- interests: (symbol name, label, enthusiasm 0-100) ----------- EDIT ME
    "interests": (
        ("AUDIO", "Synthesizers", 90),
        ("GPS", "Drone flying", 75),
        ("SETTINGS", "3D printing", 85),
        ("IMAGE", "Pixel art", 60),
        ("WIFI", "Home automation", 80),
        ("BATTERY_2", "Solar projects", 70),
    ),
    # ---- what I'm looking for / footer ------------------------------- EDIT ME
    "cta": "Open to embedded contracts and interesting collaborations.",
}
