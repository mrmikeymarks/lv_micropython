// appkeys: self-contained SHA-256, HMAC-SHA256, base32 decode, and
// RFC 6238 TOTP (HMAC-SHA256 variant). No mbedtls dependency, so it
// builds identically on the esp32 and unix ports.
// Part of the fork's root native modules; see docs/native-modules.md.

#include <string.h>

#include "py/obj.h"
#include "py/runtime.h"

#ifndef MICROPY_PY_APPKEYS
#define MICROPY_PY_APPKEYS (1)
#endif

#if MICROPY_PY_APPKEYS

// --- SHA-256 (FIPS 180-4) ---------------------------------------------------

typedef struct _sha256_ctx_t {
    uint32_t state[8];
    uint64_t bitlen;
    uint8_t buf[64];
    size_t buf_len;
} sha256_ctx_t;

static const uint32_t sha256_k[64] = {
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
};

#define ROTR(x, n) (((x) >> (n)) | ((x) << (32 - (n))))

static void sha256_transform(sha256_ctx_t *ctx, const uint8_t *p) {
    uint32_t w[64];
    for (int i = 0; i < 16; i++) {
        w[i] = ((uint32_t)p[i * 4] << 24) | ((uint32_t)p[i * 4 + 1] << 16)
            | ((uint32_t)p[i * 4 + 2] << 8) | (uint32_t)p[i * 4 + 3];
    }
    for (int i = 16; i < 64; i++) {
        uint32_t s0 = ROTR(w[i - 15], 7) ^ ROTR(w[i - 15], 18) ^ (w[i - 15] >> 3);
        uint32_t s1 = ROTR(w[i - 2], 17) ^ ROTR(w[i - 2], 19) ^ (w[i - 2] >> 10);
        w[i] = w[i - 16] + s0 + w[i - 7] + s1;
    }
    uint32_t a = ctx->state[0], b = ctx->state[1], c = ctx->state[2], d = ctx->state[3];
    uint32_t e = ctx->state[4], f = ctx->state[5], g = ctx->state[6], h = ctx->state[7];
    for (int i = 0; i < 64; i++) {
        uint32_t s1 = ROTR(e, 6) ^ ROTR(e, 11) ^ ROTR(e, 25);
        uint32_t ch = (e & f) ^ (~e & g);
        uint32_t t1 = h + s1 + ch + sha256_k[i] + w[i];
        uint32_t s0 = ROTR(a, 2) ^ ROTR(a, 13) ^ ROTR(a, 22);
        uint32_t maj = (a & b) ^ (a & c) ^ (b & c);
        uint32_t t2 = s0 + maj;
        h = g; g = f; f = e; e = d + t1;
        d = c; c = b; b = a; a = t1 + t2;
    }
    ctx->state[0] += a; ctx->state[1] += b; ctx->state[2] += c; ctx->state[3] += d;
    ctx->state[4] += e; ctx->state[5] += f; ctx->state[6] += g; ctx->state[7] += h;
}

static void sha256_init(sha256_ctx_t *ctx) {
    static const uint32_t iv[8] = {
        0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
        0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
    };
    memcpy(ctx->state, iv, sizeof(iv));
    ctx->bitlen = 0;
    ctx->buf_len = 0;
}

static void sha256_update(sha256_ctx_t *ctx, const uint8_t *data, size_t len) {
    ctx->bitlen += (uint64_t)len * 8;
    while (len > 0) {
        size_t take = 64 - ctx->buf_len;
        if (take > len) {
            take = len;
        }
        memcpy(ctx->buf + ctx->buf_len, data, take);
        ctx->buf_len += take;
        data += take;
        len -= take;
        if (ctx->buf_len == 64) {
            sha256_transform(ctx, ctx->buf);
            ctx->buf_len = 0;
        }
    }
}

static void sha256_final(sha256_ctx_t *ctx, uint8_t out[32]) {
    // Message length is captured before padding; ctx->bitlen is not used again.
    uint64_t bitlen = ctx->bitlen;
    uint8_t pad = 0x80;
    sha256_update(ctx, &pad, 1);
    uint8_t zero = 0;
    while (ctx->buf_len != 56) {
        sha256_update(ctx, &zero, 1);
    }
    uint8_t len_be[8];
    for (int i = 0; i < 8; i++) {
        len_be[i] = (uint8_t)(bitlen >> (56 - i * 8));
    }
    sha256_update(ctx, len_be, 8);
    for (int i = 0; i < 8; i++) {
        out[i * 4] = (uint8_t)(ctx->state[i] >> 24);
        out[i * 4 + 1] = (uint8_t)(ctx->state[i] >> 16);
        out[i * 4 + 2] = (uint8_t)(ctx->state[i] >> 8);
        out[i * 4 + 3] = (uint8_t)ctx->state[i];
    }
}

static void sha256_oneshot(const uint8_t *data, size_t len, uint8_t out[32]) {
    sha256_ctx_t ctx;
    sha256_init(&ctx);
    sha256_update(&ctx, data, len);
    sha256_final(&ctx, out);
}

// --- HMAC-SHA256 (RFC 2104) -------------------------------------------------

static void hmac_sha256(const uint8_t *key, size_t key_len,
    const uint8_t *msg, size_t msg_len, uint8_t out[32]) {
    uint8_t k[64];
    memset(k, 0, sizeof(k));
    if (key_len > 64) {
        sha256_oneshot(key, key_len, k);
    } else {
        memcpy(k, key, key_len);
    }
    uint8_t pad[64];
    sha256_ctx_t ctx;
    // inner = H((K ^ ipad) || msg)
    for (int i = 0; i < 64; i++) {
        pad[i] = k[i] ^ 0x36;
    }
    sha256_init(&ctx);
    sha256_update(&ctx, pad, 64);
    sha256_update(&ctx, msg, msg_len);
    uint8_t inner[32];
    sha256_final(&ctx, inner);
    // out = H((K ^ opad) || inner)
    for (int i = 0; i < 64; i++) {
        pad[i] = k[i] ^ 0x5c;
    }
    sha256_init(&ctx);
    sha256_update(&ctx, pad, 64);
    sha256_update(&ctx, inner, 32);
    sha256_final(&ctx, out);
}

// --- Python bindings --------------------------------------------------------

static mp_obj_t appkeys_sha256(mp_obj_t data_in) {
    mp_buffer_info_t data;
    mp_get_buffer_raise(data_in, &data, MP_BUFFER_READ);
    uint8_t out[32];
    sha256_oneshot(data.buf, data.len, out);
    return mp_obj_new_bytes(out, 32);
}
static MP_DEFINE_CONST_FUN_OBJ_1(appkeys_sha256_obj, appkeys_sha256);

static mp_obj_t appkeys_hmac_sha256(mp_obj_t key_in, mp_obj_t msg_in) {
    mp_buffer_info_t key, msg;
    mp_get_buffer_raise(key_in, &key, MP_BUFFER_READ);
    mp_get_buffer_raise(msg_in, &msg, MP_BUFFER_READ);
    uint8_t out[32];
    hmac_sha256(key.buf, key.len, msg.buf, msg.len, out);
    return mp_obj_new_bytes(out, 32);
}
static MP_DEFINE_CONST_FUN_OBJ_2(appkeys_hmac_sha256_obj, appkeys_hmac_sha256);

// RFC 4648 base32 decode; case-insensitive, '=' padding and spaces ignored.
static mp_obj_t appkeys_b32decode(mp_obj_t str_in) {
    mp_buffer_info_t src;
    mp_get_buffer_raise(str_in, &src, MP_BUFFER_READ);
    const char *s = src.buf;
    vstr_t vstr;
    vstr_init(&vstr, src.len * 5 / 8 + 1);
    uint32_t acc = 0;
    int bits = 0;
    for (size_t i = 0; i < src.len; i++) {
        char c = s[i];
        int v;
        if (c >= 'A' && c <= 'Z') {
            v = c - 'A';
        } else if (c >= 'a' && c <= 'z') {
            v = c - 'a';
        } else if (c >= '2' && c <= '7') {
            v = c - '2' + 26;
        } else if (c == '=' || c == ' ' || c == '-') {
            continue;
        } else {
            mp_raise_ValueError(MP_ERROR_TEXT("invalid base32 character"));
        }
        acc = (acc << 5) | v;
        bits += 5;
        if (bits >= 8) {
            bits -= 8;
            vstr_add_byte(&vstr, (uint8_t)(acc >> bits));
        }
    }
    return mp_obj_new_bytes_from_vstr(&vstr);
}
static MP_DEFINE_CONST_FUN_OBJ_1(appkeys_b32decode_obj, appkeys_b32decode);

// totp(secret, unixtime, step=30, digits=6) -> int
// RFC 6238 with HMAC-SHA256 (test vectors: appendix B, SHA256 column).
static mp_obj_t appkeys_totp(size_t n_args, const mp_obj_t *args) {
    mp_buffer_info_t secret;
    mp_get_buffer_raise(args[0], &secret, MP_BUFFER_READ);
    long long unixtime = mp_obj_get_int(args[1]);
    mp_int_t step = n_args >= 3 ? mp_obj_get_int(args[2]) : 30;
    mp_int_t digits = n_args >= 4 ? mp_obj_get_int(args[3]) : 6;
    if (step <= 0 || digits < 4 || digits > 9) {
        mp_raise_ValueError(MP_ERROR_TEXT("step must be >0, digits 4-9"));
    }
    uint64_t counter = (uint64_t)(unixtime / step);
    uint8_t msg[8];
    for (int i = 0; i < 8; i++) {
        msg[i] = (uint8_t)(counter >> (56 - i * 8));
    }
    uint8_t mac[32];
    hmac_sha256(secret.buf, secret.len, msg, 8, mac);
    int off = mac[31] & 0x0f;
    uint32_t code = ((uint32_t)(mac[off] & 0x7f) << 24)
        | ((uint32_t)mac[off + 1] << 16)
        | ((uint32_t)mac[off + 2] << 8)
        | (uint32_t)mac[off + 3];
    uint32_t mod = 1;
    for (int i = 0; i < digits; i++) {
        mod *= 10;
    }
    return mp_obj_new_int_from_uint(code % mod);
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(appkeys_totp_obj, 2, 4, appkeys_totp);

static const mp_rom_map_elem_t appkeys_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_appkeys) },
    { MP_ROM_QSTR(MP_QSTR_sha256), MP_ROM_PTR(&appkeys_sha256_obj) },
    { MP_ROM_QSTR(MP_QSTR_hmac_sha256), MP_ROM_PTR(&appkeys_hmac_sha256_obj) },
    { MP_ROM_QSTR(MP_QSTR_b32decode), MP_ROM_PTR(&appkeys_b32decode_obj) },
    { MP_ROM_QSTR(MP_QSTR_totp), MP_ROM_PTR(&appkeys_totp_obj) },
};
static MP_DEFINE_CONST_DICT(appkeys_module_globals, appkeys_module_globals_table);

const mp_obj_module_t appkeys_user_cmodule = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&appkeys_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_appkeys, appkeys_user_cmodule);

#endif // MICROPY_PY_APPKEYS
