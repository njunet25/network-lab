cmake_minimum_required(VERSION 3.10)

project(http-client C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

add_executable(dns src/main.c)

target_link_libraries(dns PRIVATE resolv)
