cmake_minimum_required(VERSION 3.10)

# 工程名称
project(http-client C)

# 设置 C 标准（可选）
set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

# 添加可执行文件
add_executable(http-client src/main.c)
