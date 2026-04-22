#pragma once
#include <vector>
#include <cstdint>
#include <cstdlib>

// x64 NOP-эквивалентные junk-последовательности
static const uint8_t JUNK_SEQS[][4] = {
    { 0x90,0x90,0x90,0x90 },   // 4x NOP
    { 0x66,0x90,0x66,0x90 },   // 2x XCHG AX,AX
    { 0x0F,0x1F,0x00,0x90 },   // NOP DWORD [RAX]
    { 0x48,0x87,0xC0,0x90 },   // XCHG RAX,RAX
};

// Вставка junk каждые interval байт
inline std::vector<uint8_t> metamorphic_pad(const std::vector<uint8_t>& stub,
                                              int interval = 8, unsigned seed = 0x1337) {
    std::vector<uint8_t> out; out.reserve(stub.size() * 2);
    srand(seed);
    for (size_t i = 0; i < stub.size(); ++i) {
        out.push_back(stub[i]);
        if (i > 0 && i % interval == 0) {
            const uint8_t* junk = JUNK_SEQS[rand() % 4];
            for (int j = 0; j < 4; ++j) out.push_back(junk[j]);
        }
    }
    return out;
}

// Poly XOR-encode: каждый байт XOR с ротирующим ключом
inline std::vector<uint8_t> poly_encode_stub(const std::vector<uint8_t>& stub,
                                              uint8_t seed_key = 0xA5) {
    std::vector<uint8_t> out(stub.size());
    uint8_t k = seed_key;
    for (size_t i = 0; i < stub.size(); ++i) {
        out[i] = stub[i] ^ k;
        k = (k << 1) | (k >> 7); // ROL 1
    }
    return out;
}

inline void print_obf_stats(const char* label, size_t orig, size_t obf) {
    printf("[OBFUSC]  %-20s  orig=%zu  obfuscated=%zu  overhead=+%.1f%%\n",
           label, orig, obf, 100.0 * (double)(obf - orig) / orig);
}