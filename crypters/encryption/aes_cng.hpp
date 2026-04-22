#pragma once
#include <windows.h>
#include <bcrypt.h>
#include <vector>
#include <cstdint>
#include <stdexcept>
#pragma comment(lib, "Bcrypt.lib")

inline std::vector<uint8_t> aes_cbc_encrypt(const std::vector<uint8_t>& plain,
                                              const uint8_t* key, size_t key_bits,
                                              const uint8_t* iv) {
    BCRYPT_ALG_HANDLE hAlg = nullptr; BCRYPT_KEY_HANDLE hKey = nullptr;
    BCryptOpenAlgorithmProvider(&hAlg, BCRYPT_AES_ALGORITHM, nullptr, 0);
    BCryptSetProperty(hAlg, BCRYPT_CHAINING_MODE,
        (PUCHAR)BCRYPT_CHAIN_MODE_CBC, sizeof(BCRYPT_CHAIN_MODE_CBC), 0);
    BCryptGenerateSymmetricKey(hAlg, &hKey, nullptr, 0,
        (PUCHAR)key, (ULONG)(key_bits / 8), 0);
    size_t pad = 16 - (plain.size() % 16);
    std::vector<uint8_t> padded(plain);
    padded.insert(padded.end(), pad, (uint8_t)pad);
    std::vector<uint8_t> iv_buf(iv, iv + 16);
    std::vector<uint8_t> cipher(padded.size());
    ULONG out_len = 0;
    BCryptEncrypt(hKey, (PUCHAR)padded.data(), (ULONG)padded.size(),
        nullptr, iv_buf.data(), 16, cipher.data(), (ULONG)cipher.size(), &out_len, 0);
    BCryptDestroyKey(hKey); BCryptCloseAlgorithmProvider(hAlg, 0);
    cipher.resize(out_len); return cipher;
}

inline void gen_random(uint8_t* buf, size_t len) {
    BCRYPT_ALG_HANDLE hAlg = nullptr;
    BCryptOpenAlgorithmProvider(&hAlg, BCRYPT_RNG_ALGORITHM, nullptr, 0);
    BCryptGenRandom(hAlg, buf, (ULONG)len, 0);
    BCryptCloseAlgorithmProvider(hAlg, 0);
}

static const uint8_t AES128_KEY[] = {
    0x2b,0x7e,0x15,0x16,0x28,0xae,0xd2,0xa6,
    0xab,0xf7,0x15,0x88,0x09,0xcf,0x4f,0x3c };
static const uint8_t AES256_KEY[] = {
    0x60,0x3d,0xeb,0x10,0x15,0xca,0x71,0xbe,
    0x2b,0x73,0xae,0xf0,0x85,0x7d,0x77,0x81,
    0x1f,0x35,0x2c,0x07,0x3b,0x61,0x08,0xd7,
    0x2d,0x98,0x10,0xa3,0x09,0x14,0xdf,0xf4 };
static const uint8_t AES_IV[] = {
    0x00,0x01,0x02,0x03,0x04,0x05,0x06,0x07,
    0x08,0x09,0x0a,0x0b,0x0c,0x0d,0x0e,0x0f };