// appperf: lightweight performance instrumentation for LVGL apps.
// Frame-time ring buffer (lap/fps/percentiles), heap snapshot, and a
// micro-benchmark harness. Portable across esp32 and unix ports.
// Part of the fork's root native modules; see docs/native-modules.md.

#include "py/obj.h"
#include "py/runtime.h"
#include "py/mphal.h"
#include "py/gc.h"

#ifndef MICROPY_PY_APPPERF
#define MICROPY_PY_APPPERF (1)
#endif

#if MICROPY_PY_APPPERF

#define APPPERF_RING (128)

static uint32_t appperf_deltas[APPPERF_RING];
static size_t appperf_count;    // number of valid deltas (saturates at APPPERF_RING)
static size_t appperf_head;     // next write index
static mp_uint_t appperf_last;  // timestamp of previous lap()
static uint8_t appperf_started;

static mp_obj_t appperf_now_us(void) {
    return mp_obj_new_int_from_uint(mp_hal_ticks_us());
}
static MP_DEFINE_CONST_FUN_OBJ_0(appperf_now_us_obj, appperf_now_us);

// Call once per frame; records the time since the previous call.
static mp_obj_t appperf_lap(void) {
    mp_uint_t now = mp_hal_ticks_us();
    if (appperf_started) {
        appperf_deltas[appperf_head] = (uint32_t)(now - appperf_last);
        appperf_head = (appperf_head + 1) % APPPERF_RING;
        if (appperf_count < APPPERF_RING) {
            appperf_count++;
        }
    }
    appperf_started = 1;
    appperf_last = now;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_0(appperf_lap_obj, appperf_lap);

static mp_obj_t appperf_reset(void) {
    appperf_count = 0;
    appperf_head = 0;
    appperf_started = 0;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_0(appperf_reset_obj, appperf_reset);

static uint64_t appperf_sum(void) {
    uint64_t sum = 0;
    for (size_t i = 0; i < appperf_count; i++) {
        sum += appperf_deltas[i];
    }
    return sum;
}

static mp_obj_t appperf_fps(void) {
    uint64_t sum = appperf_sum();
    if (sum == 0) {
        return mp_obj_new_float(0);
    }
    return mp_obj_new_float((mp_float_t)appperf_count * 1000000 / (mp_float_t)sum);
}
static MP_DEFINE_CONST_FUN_OBJ_0(appperf_fps_obj, appperf_fps);

static mp_obj_t appperf_avg_us(void) {
    if (appperf_count == 0) {
        return mp_obj_new_float(0);
    }
    return mp_obj_new_float((mp_float_t)appperf_sum() / (mp_float_t)appperf_count);
}
static MP_DEFINE_CONST_FUN_OBJ_0(appperf_avg_us_obj, appperf_avg_us);

// 95th-percentile frame time in us (insertion sort over <=128 samples).
static mp_obj_t appperf_p95_us(void) {
    if (appperf_count == 0) {
        return mp_obj_new_int(0);
    }
    uint32_t sorted[APPPERF_RING];
    for (size_t i = 0; i < appperf_count; i++) {
        uint32_t v = appperf_deltas[i];
        size_t j = i;
        while (j > 0 && sorted[j - 1] > v) {
            sorted[j] = sorted[j - 1];
            j--;
        }
        sorted[j] = v;
    }
    size_t idx = (appperf_count * 95) / 100;
    if (idx >= appperf_count) {
        idx = appperf_count - 1;
    }
    return mp_obj_new_int_from_uint(sorted[idx]);
}
static MP_DEFINE_CONST_FUN_OBJ_0(appperf_p95_us_obj, appperf_p95_us);

// (total, used, free, max_free_block_words) heap snapshot.
static mp_obj_t appperf_mem(void) {
    gc_info_t info;
    gc_info(&info);
    mp_obj_t items[4] = {
        mp_obj_new_int_from_uint(info.total),
        mp_obj_new_int_from_uint(info.used),
        mp_obj_new_int_from_uint(info.free),
        mp_obj_new_int_from_uint(info.max_free),
    };
    return mp_obj_new_tuple(4, items);
}
static MP_DEFINE_CONST_FUN_OBJ_0(appperf_mem_obj, appperf_mem);

// bench(callable, n=100) -> average us per call.
static mp_obj_t appperf_bench(size_t n_args, const mp_obj_t *args) {
    mp_int_t n = n_args >= 2 ? mp_obj_get_int(args[1]) : 100;
    if (n <= 0) {
        mp_raise_ValueError(MP_ERROR_TEXT("n must be > 0"));
    }
    mp_uint_t t0 = mp_hal_ticks_us();
    for (mp_int_t i = 0; i < n; i++) {
        mp_call_function_0(args[0]);
    }
    mp_uint_t dt = mp_hal_ticks_us() - t0;
    return mp_obj_new_float((mp_float_t)dt / (mp_float_t)n);
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(appperf_bench_obj, 1, 2, appperf_bench);

static const mp_rom_map_elem_t appperf_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_appperf) },
    { MP_ROM_QSTR(MP_QSTR_now_us), MP_ROM_PTR(&appperf_now_us_obj) },
    { MP_ROM_QSTR(MP_QSTR_lap), MP_ROM_PTR(&appperf_lap_obj) },
    { MP_ROM_QSTR(MP_QSTR_reset), MP_ROM_PTR(&appperf_reset_obj) },
    { MP_ROM_QSTR(MP_QSTR_fps), MP_ROM_PTR(&appperf_fps_obj) },
    { MP_ROM_QSTR(MP_QSTR_avg_us), MP_ROM_PTR(&appperf_avg_us_obj) },
    { MP_ROM_QSTR(MP_QSTR_p95_us), MP_ROM_PTR(&appperf_p95_us_obj) },
    { MP_ROM_QSTR(MP_QSTR_mem), MP_ROM_PTR(&appperf_mem_obj) },
    { MP_ROM_QSTR(MP_QSTR_bench), MP_ROM_PTR(&appperf_bench_obj) },
};
static MP_DEFINE_CONST_DICT(appperf_module_globals, appperf_module_globals_table);

const mp_obj_module_t appperf_user_cmodule = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&appperf_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_appperf, appperf_user_cmodule);

#endif // MICROPY_PY_APPPERF
