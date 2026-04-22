cmake_minimum_required(VERSION 3.20)
project(vkr_crypters CXX)
set(CMAKE_CXX_STANDARD 17)
include_directories(${CMAKE_SOURCE_DIR})

add_executable(crypter_a crypter_a/main.cpp)
target_link_libraries(crypter_a bcrypt)

add_executable(crypter_b crypter_b/main.cpp)
target_link_libraries(crypter_b bcrypt)

add_executable(crypter_c crypter_c/main.cpp)
target_link_libraries(crypter_c bcrypt)

add_executable(crypter_d crypter_d/main.cpp)
target_link_libraries(crypter_d bcrypt)

if(MSVC)
    add_compile_options(/O2 /W3)
    add_compile_definitions(_CRT_SECURE_NO_WARNINGS)
endif()
if(MINGW OR CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
    add_compile_options(-O2 -Wall)
endif()