#pragma once
#include <vector>
#include <cstdint>
#include <cstdio>

// RLE-заглушка. Замени rle_compress/rle_decompress на liblzma когда подключишь.
inline std::vector<uint8_t> rle_compress(const std::vector<uint8_t>& in) {
    std::vector<uint8_t> out;
    out.push_back(0xCC); // маркер RLE
    size_t i = 0;
    while (i < in.size()) {
        uint8_t b = in[i]; size_t run = 1;
        while (i + run < in.size() && in[i+run] == b && run < 255) run++;
        if (run >= 3) {
            out.push_back(0xFF); out.push_back(b); out.push_back((uint8_t)run);
        } else {
            for (size_t j = 0; j < run; ++j) {
                if (b == 0xFF) { out.push_back(0xFF); out.push_back(0xFF); out.push_back(1); }
                else out.push_back(b);
            }
        }
        i += run;
    }
    return out;
}

inline std::vector<uint8_t> no_compress(const std::vector<uint8_t>& in) { return in; }

inline void print_compression_ratio(const char* label, size_t orig, size_t comp) {
    printf("[COMPRESS] %-20s  %zu -> %zu bytes  ratio=%.2f%%\n",
           label, orig, comp, 100.0 * comp / orig);
}