#pragma once
#include <vector>
#include <cstdint>
#include <cmath>
#include <cstdio>

inline double calc_entropy(const std::vector<uint8_t>& data) {
    if (data.empty()) return 0.0;
    size_t freq[256] = {};
    for (uint8_t b : data) freq[b]++;
    double h = 0.0, n = (double)data.size();
    for (int i = 0; i < 256; ++i) {
        if (!freq[i]) continue;
        double p = freq[i] / n;
        h -= p * log2(p);
    }
    return h;
}

inline void print_entropy(const char* label, const std::vector<uint8_t>& data) {
    printf("[ENTROPY] %-20s  H=%.4f bit/byte  size=%zu bytes\n",
           label, calc_entropy(data), data.size());
}