# This is the default variant when you `make` the Unix port.

FROZEN_MANIFEST ?= $(VARIANT_DIR)/manifest.py
USER_C_MODULES ?= ${TOP}/user_modules

# Fork: root native modules (appconfig, appkeys, appperf).
SRC_C += appconfig.c appkeys.c appperf.c
