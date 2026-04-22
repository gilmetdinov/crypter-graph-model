#pragma once
#include <windows.h>
#include <functional>
#include <cstdio>

struct ProfileResult { double avg_ms, min_ms, max_ms; };

inline ProfileResult profile_fn(std::function<void()> fn, int runs = 100) {
    LARGE_INTEGER freq, t0, t1;
    QueryPerformanceFrequency(&freq);
    double total = 0.0, lo = 1e18, hi = 0.0;
    for (int i = 0; i < runs; ++i) {
        QueryPerformanceCounter(&t0); fn(); QueryPerformanceCounter(&t1);
        double ms = (double)(t1.QuadPart - t0.QuadPart) * 1000.0 / (double)freq.QuadPart;
        total += ms;
        if (ms < lo) lo = ms;
        if (ms > hi) hi = ms;
    }
    return { total / runs, lo, hi };
}

inline void print_profile(const char* label, const ProfileResult& r) {
    printf("[PROFILE] %-20s  avg=%.3f ms  min=%.3f ms  max=%.3f ms\n",
           label, r.avg_ms, r.min_ms, r.max_ms);
}