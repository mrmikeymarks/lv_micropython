#!/usr/bin/env bash

# Show ESP32 board / variant selector menu
# Non-interactive use: set BOARD (and optionally BOARD_VARIANT) in the
# environment to skip the menu, e.g.  BOARD=ESP32_GENERIC ./build-esp32.sh

if [ -n "${BOARD:-}" ]; then
    BOARD_VARIANT="${BOARD_VARIANT:-}"
    echo "Using BOARD=$BOARD BOARD_VARIANT=$BOARD_VARIANT (menu skipped)"
    return 0 2>/dev/null || exit 0
fi

# Array of configurations
configs=(
    "ESP32_GENERIC"
    "ESP32_GENERIC SPIRAM"
    "ESP32_GENERIC_S3"
    "ESP32_GENERIC_S3 SPIRAM_OCT"
    "M5STACK_CORE2"
    "LILYGO_TDISPLAY"
    "LILYGO_TWATCH_2020 V1"
    "LILYGO_TWATCH_2020 V2"
    "LILYGO_TWATCH_2020 V3"
)

# Function to display menu and get user choice
show_menu() {
    echo "Select a configuration:"
    for i in "${!configs[@]}"; do
        echo "$((i+1)). ${configs[$i]}"
    done
    read -p "Enter your choice (1-${#configs[@]}): " choice
    return $choice
}

# Display menu and get user choice
show_menu
choice=$?

# Validate user input
if [[ $choice -lt 1 || $choice -gt ${#configs[@]} ]]; then
    echo "Invalid choice. Exiting."
    exit 1
fi

# Set BOARD and BOARD_VARIANT based on user choice
selected_config=(${configs[$((choice-1))]})
# BOARD=ESP32_GENERIC
# BOARD_VARIANT=SPIRAM
BOARD=${selected_config[0]}
BOARD_VARIANT=${selected_config[1]:-""}

echo "Selected configuration: BOARD=$BOARD, BOARD_VARIANT=$BOARD_VARIANT"
