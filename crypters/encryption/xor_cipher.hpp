#pragma once
#include <vector>
#include <cstdint>

inline std::vector<uint8_t> xor_crypt(const std::vector<uint8_t>& data,
                                       const uint8_t* key, size_t key_len) {
    std::vector<uint8_t> out(data.size());
    for (size_t i = 0; i < data.size(); ++i)
        out[i] = data[i] ^ key[i % key_len];
    return out;
}

static const uint8_t XOR_KEY_A[] = { 0xDE,0xAD,0xBE,0xEF,0xCA,0xFE,0xBA,0xBE };
static const size_t  XOR_KEY_LEN = sizeof(XOR_KEY_A);