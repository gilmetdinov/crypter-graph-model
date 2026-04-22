#pragma once
#include <vector>
#include <cstdint>
#include <cstdio>
#include <stdexcept>
#include <string>

inline std::vector<uint8_t> read_file(const std::string& path) {
    FILE* f = fopen(path.c_str(), "rb");
    if (!f) throw std::runtime_error("Cannot open: " + path);
    fseek(f, 0, SEEK_END); long sz = ftell(f); fseek(f, 0, SEEK_SET);
    std::vector<uint8_t> buf(sz);
    fread(buf.data(), 1, sz, f); fclose(f);
    return buf;
}

inline void write_file(const std::string& path, const std::vector<uint8_t>& data) {
    FILE* f = fopen(path.c_str(), "wb");
    if (!f) throw std::runtime_error("Cannot write: " + path);
    fwrite(data.data(), 1, data.size(), f); fclose(f);
}

// Формат: [magic 4B][payload_size 4B][payload_bytes]
inline void write_encrypted_blob(const std::string& path,
                                  const std::vector<uint8_t>& payload,
                                  uint32_t magic = 0xDEADBEEF) {
    FILE* f = fopen(path.c_str(), "wb");
    if (!f) throw std::runtime_error("Cannot write: " + path);
    uint32_t sz = (uint32_t)payload.size();
    fwrite(&magic, 4, 1, f); fwrite(&sz, 4, 1, f);
    fwrite(payload.data(), 1, payload.size(), f); fclose(f);
}