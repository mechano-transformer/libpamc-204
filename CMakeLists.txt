cmake_minimum_required(VERSION 3.10)
project(libpamc204 LANGUAGES CXX)

include_directories(include)

if(WIN32)
    set(SOURCES src/serial_win.cpp src/serial_common.cpp)
else()
    set(SOURCES src/serial_linux.cpp src/serial_common.cpp)
endif()

add_library(pamc204 SHARED ${SOURCES})

add_executable(test_serial test/main.cpp)
target_link_libraries(test_serial pamc204)
