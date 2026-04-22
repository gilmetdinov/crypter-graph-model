/*
 * Crypter D — XOR (динамический ключ) → AES-128 CBC (динамический ключ)
 * L2: XOR+AES-128 dynamic  |  L3: nocomp  |  L4: noobf
 * Сборка: g++ -O2 -std=c++17 -o crypter_d.exe main.cpp -lbcrypt
 * Запуск: crypter_d.exe <payload.exe> <output.enc> [--bench]
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
#include "../encryption/aes_cng.hpp"

int main(int argc, char* argv[]) {
    if (argc < 3) { printf("Usage: crypter_d.exe <payload> <output.enc> [--bench]\n"); return 1; }
    bool bench = (argc >= 4 && strcmp(argv[3], "--bench") == 0);
    const int RUNS = bench ? 100 : 1;

    printf("=== Crypter D: XOR+AES-128 / dynamic keys / nocomp / noobf ===\n");
    auto payload = read_file(argv[1]);
    printf("Payload: %zu bytes, entropy=%.4f\n\n", payload.size(), calc_entropy(payload));

    // Динамические ключи через BCryptGenRandom
    uint8_t dyn_xor[8]={}, dyn_aes[16]={}, dyn_iv[16]={};
    gen_random(dyn_xor, 8); gen_random(dyn_aes, 16); gen_random(dyn_iv, 16);

    printf("XOR key: ");
    for (int i = 0; i < 8; ++i) printf("%02X ", dyn_xor[i]);
    printf("\n\n");

    std::vector<uint8_t> xor_out, final_enc;

    // Step 1: XOR
    auto xor_fn = [&]() { xor_out = xor_crypt(payload, dyn_xor, 8); };
    ProfileResult pr_xor = profile_fn(xor_fn, RUNS); xor_fn();
    print_profile("XOR pass", pr_xor);
    print_entropy("XOR output", xor_out);

    // Step 2: AES-128
    auto aes_fn = [&]() { final_enc = aes_cbc_encrypt(xor_out, dyn_aes, 128, dyn_iv); };
    ProfileResult pr_aes = profile_fn(aes_fn, RUNS); aes_fn();
    print_profile("AES-128 pass", pr_aes);
    print_entropy("AES-128 output", final_enc);

    printf("\n[METRICS]\n");
    printf("  time_total : %.3f ms\n", pr_xor.avg_ms + pr_aes.avg_ms);
    printf("  entropy    : %.4f bit/byte\n", calc_entropy(final_enc));
    printf("  strength   : 0.8\n");
    printf("  detectab   : ~0.35\n");

    // Блоб: [xor_key 8B][aes_key 16B][iv 16B][ciphertext]
    std::vector<uint8_t> blob;
    blob.insert(blob.end(), dyn_xor, dyn_xor+8);
    blob.insert(blob.end(), dyn_aes, dyn_aes+16);
    blob.insert(blob.end(), dyn_iv,  dyn_iv+16);
    blob.insert(blob.end(), final_enc.begin(), final_enc.end());

    write_encrypted_blob(argv[2], blob);
    printf("\nOutput: %s (%zu bytes)\n", argv[2], blob.size() + 8);
    return 0;
}