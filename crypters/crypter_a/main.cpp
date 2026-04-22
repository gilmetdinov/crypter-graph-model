/*
 * Crypter A — XOR фиксированный ключ, без компрессии, без обфускации
 * L2: XOR  |  L3: nocomp  |  L4: noobf
 * Сборка: g++ -O2 -std=c++17 -o crypter_a.exe main.cpp -lbcrypt
 * Запуск: crypter_a.exe <payload.exe> <output.enc> [--bench]
 */
#include <cstdio>
#include <cstring>
#include <vector>
#include <stdexcept>
#include <windows.h>
#include "../common/profiler.hpp"
#include "../common/entropy.hpp"
#include "../common/pe_io.hpp"
#include "../encryption/xor_cipher.hpp"

int main(int argc, char* argv[]) {
    if (argc < 3) { printf("Usage: crypter_a.exe <payload> <output.enc> [--bench]\n"); return 1; }
    bool bench = (argc >= 4 && strcmp(argv[3], "--bench") == 0);

    printf("=== Crypter A: XOR / nocomp / noobf ===\n");
    auto payload = read_file(argv[1]);
    printf("Payload: %zu bytes, entropy=%.4f\n\n", payload.size(), calc_entropy(payload));

    std::vector<uint8_t> encrypted;
    auto enc_fn = [&]() { encrypted = xor_crypt(payload, XOR_KEY_A, XOR_KEY_LEN); };

    ProfileResult pr = profile_fn(enc_fn, bench ? 100 : 1);
    enc_fn();

    print_profile("XOR encrypt", pr);
    print_entropy("XOR output", encrypted);

    printf("\n[METRICS]\n");
    printf("  time_avg  : %.3f ms\n", pr.avg_ms);
    printf("  entropy   : %.4f bit/byte\n", calc_entropy(encrypted));
    printf("  strength  : 0.2\n");
    printf("  detectab  : ~0.85\n");

    write_encrypted_blob(argv[2], encrypted);
    printf("\nOutput: %s (%zu bytes)\n", argv[2], encrypted.size() + 8);
    return 0;
}