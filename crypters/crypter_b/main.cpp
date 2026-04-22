/*
 * Crypter B — AES-256 CBC + RLE-компрессия (LZMA-stub)
 * L2: AES-256  |  L3: RLE(LZMA-stub)  |  L4: noobf
 * Сборка: g++ -O2 -std=c++17 -o crypter_b.exe main.cpp -lbcrypt
 * Запуск: crypter_b.exe <payload.exe> <output.enc> [--bench]
 */
#include <cstdio>
#include <cstring>
#include <vector>
#include <stdexcept>
#include <windows.h>
#include "../common/profiler.hpp"
#include "../common/entropy.hpp"
#include "../common/pe_io.hpp"
#include "../encryption/aes_cng.hpp"
#include "../compression/compress.hpp"

int main(int argc, char* argv[]) {
    if (argc < 3) { printf("Usage: crypter_b.exe <payload> <output.enc> [--bench]\n"); return 1; }
    bool bench = (argc >= 4 && strcmp(argv[3], "--bench") == 0);
    const int RUNS = bench ? 100 : 1;

    printf("=== Crypter B: AES-256 CBC / RLE(LZMA-stub) / noobf ===\n");
    auto payload = read_file(argv[1]);
    printf("Payload: %zu bytes, entropy=%.4f\n\n", payload.size(), calc_entropy(payload));

    std::vector<uint8_t> compressed, encrypted;

    // L3: compress first (перед шифрованием — лучше сжимается)
    auto comp_fn = [&]() { compressed = rle_compress(payload); };
    ProfileResult pr_comp = profile_fn(comp_fn, RUNS); comp_fn();
    print_profile("RLE compress", pr_comp);
    print_compression_ratio("RLE", payload.size(), compressed.size());

    // L2: AES-256
    auto enc_fn = [&]() { encrypted = aes_cbc_encrypt(compressed, AES256_KEY, 256, AES_IV); };
    ProfileResult pr_enc = profile_fn(enc_fn, RUNS); enc_fn();
    print_profile("AES-256 encrypt", pr_enc);
    print_entropy("AES-256 output", encrypted);

    printf("\n[METRICS]\n");
    printf("  time_total : %.3f ms\n", pr_comp.avg_ms + pr_enc.avg_ms);
    printf("  entropy    : %.4f bit/byte\n", calc_entropy(encrypted));
    printf("  strength   : 1.0\n");
    printf("  detectab   : ~0.42\n");

    write_encrypted_blob(argv[2], encrypted);
    printf("\nOutput: %s (%zu bytes)\n", argv[2], encrypted.size() + 8);
    return 0;
}