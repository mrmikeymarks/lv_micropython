// appconfig: build passport and small C-side key/value store.
// Part of the fork's root native modules; see docs/native-modules.md.

#include <string.h>

#include "py/obj.h"
#include "py/objstr.h"
#include "py/runtime.h"
#include "genhdr/mpversion.h"

#ifndef MICROPY_PY_APPCONFIG
#define MICROPY_PY_APPCONFIG (1)
#endif

#if MICROPY_PY_APPCONFIG

#ifndef MICROPY_HW_BOARD_NAME
#define MICROPY_HW_BOARD_NAME "unix"
#endif
#ifndef MICROPY_HW_MCU_NAME
#define MICROPY_HW_MCU_NAME "host"
#endif

// Values live in plain C statics (ints or short copied strings), so the
// store needs no GC root registration.
#define APPCONFIG_SLOTS (16)
#define APPCONFIG_KEY_LEN (16)
#define APPCONFIG_VAL_LEN (32)

typedef struct _appconfig_slot_t {
    char key[APPCONFIG_KEY_LEN];
    char sval[APPCONFIG_VAL_LEN];
    mp_int_t ival;
    uint8_t used;
    uint8_t is_str;
} appconfig_slot_t;

static appconfig_slot_t appconfig_slots[APPCONFIG_SLOTS];

static appconfig_slot_t *appconfig_find(const char *key) {
    for (int i = 0; i < APPCONFIG_SLOTS; i++) {
        if (appconfig_slots[i].used && strcmp(appconfig_slots[i].key, key) == 0) {
            return &appconfig_slots[i];
        }
    }
    return NULL;
}

static mp_obj_t appconfig_set(mp_obj_t key_in, mp_obj_t value_in) {
    size_t key_len;
    const char *key = mp_obj_str_get_data(key_in, &key_len);
    if (key_len == 0 || key_len >= APPCONFIG_KEY_LEN) {
        mp_raise_ValueError(MP_ERROR_TEXT("key must be 1-15 chars"));
    }
    appconfig_slot_t *slot = appconfig_find(key);
    if (slot == NULL) {
        for (int i = 0; i < APPCONFIG_SLOTS; i++) {
            if (!appconfig_slots[i].used) {
                slot = &appconfig_slots[i];
                break;
            }
        }
        if (slot == NULL) {
            mp_raise_ValueError(MP_ERROR_TEXT("config store full"));
        }
        strcpy(slot->key, key);
    }
    if (mp_obj_is_str(value_in)) {
        size_t val_len;
        const char *val = mp_obj_str_get_data(value_in, &val_len);
        if (val_len >= APPCONFIG_VAL_LEN) {
            mp_raise_ValueError(MP_ERROR_TEXT("string value too long (max 31)"));
        }
        memcpy(slot->sval, val, val_len);
        slot->sval[val_len] = '\0';
        slot->is_str = 1;
    } else {
        slot->ival = mp_obj_get_int(value_in);
        slot->is_str = 0;
    }
    slot->used = 1;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(appconfig_set_obj, appconfig_set);

static mp_obj_t appconfig_get(size_t n_args, const mp_obj_t *args) {
    const char *key = mp_obj_str_get_str(args[0]);
    appconfig_slot_t *slot = appconfig_find(key);
    if (slot == NULL) {
        return n_args == 2 ? args[1] : mp_const_none;
    }
    if (slot->is_str) {
        return mp_obj_new_str(slot->sval, strlen(slot->sval));
    }
    return mp_obj_new_int(slot->ival);
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(appconfig_get_obj, 1, 2, appconfig_get);

static mp_obj_t appconfig_unset(mp_obj_t key_in) {
    appconfig_slot_t *slot = appconfig_find(mp_obj_str_get_str(key_in));
    if (slot != NULL) {
        slot->used = 0;
    }
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(appconfig_unset_obj, appconfig_unset);

static mp_obj_t appconfig_keys(void) {
    mp_obj_t list = mp_obj_new_list(0, NULL);
    for (int i = 0; i < APPCONFIG_SLOTS; i++) {
        if (appconfig_slots[i].used) {
            mp_obj_list_append(list, mp_obj_new_str(appconfig_slots[i].key, strlen(appconfig_slots[i].key)));
        }
    }
    return list;
}
static MP_DEFINE_CONST_FUN_OBJ_0(appconfig_keys_obj, appconfig_keys);

static MP_DEFINE_STR_OBJ(appconfig_board_obj, MICROPY_HW_BOARD_NAME);
static MP_DEFINE_STR_OBJ(appconfig_mcu_obj, MICROPY_HW_MCU_NAME);
static MP_DEFINE_STR_OBJ(appconfig_version_obj, MICROPY_VERSION_STRING);
static MP_DEFINE_STR_OBJ(appconfig_git_obj, MICROPY_GIT_TAG);
static MP_DEFINE_STR_OBJ(appconfig_build_date_obj, MICROPY_BUILD_DATE);
static MP_DEFINE_STR_OBJ(appconfig_compiler_obj, __VERSION__);

static const mp_rom_map_elem_t appconfig_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_appconfig) },
    { MP_ROM_QSTR(MP_QSTR_BOARD), MP_ROM_PTR(&appconfig_board_obj) },
    { MP_ROM_QSTR(MP_QSTR_MCU), MP_ROM_PTR(&appconfig_mcu_obj) },
    { MP_ROM_QSTR(MP_QSTR_VERSION), MP_ROM_PTR(&appconfig_version_obj) },
    { MP_ROM_QSTR(MP_QSTR_GIT), MP_ROM_PTR(&appconfig_git_obj) },
    { MP_ROM_QSTR(MP_QSTR_BUILD_DATE), MP_ROM_PTR(&appconfig_build_date_obj) },
    { MP_ROM_QSTR(MP_QSTR_COMPILER), MP_ROM_PTR(&appconfig_compiler_obj) },
    #ifdef LV_COLOR_DEPTH
    { MP_ROM_QSTR(MP_QSTR_LV_COLOR_DEPTH), MP_ROM_INT(LV_COLOR_DEPTH) },
    #else
    { MP_ROM_QSTR(MP_QSTR_LV_COLOR_DEPTH), MP_ROM_INT(-1) },
    #endif
    { MP_ROM_QSTR(MP_QSTR_set), MP_ROM_PTR(&appconfig_set_obj) },
    { MP_ROM_QSTR(MP_QSTR_get), MP_ROM_PTR(&appconfig_get_obj) },
    { MP_ROM_QSTR(MP_QSTR_unset), MP_ROM_PTR(&appconfig_unset_obj) },
    { MP_ROM_QSTR(MP_QSTR_keys), MP_ROM_PTR(&appconfig_keys_obj) },
};
static MP_DEFINE_CONST_DICT(appconfig_module_globals, appconfig_module_globals_table);

const mp_obj_module_t appconfig_user_cmodule = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&appconfig_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_appconfig, appconfig_user_cmodule);

#endif // MICROPY_PY_APPCONFIG
