cmake_minimum_required(VERSION 3.15)
project(libpamc204 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# 公開ヘッダ
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/include)

# 共有のソース
set(COMMON_SRC
    src/serial_common.cpp
)

# OS ごとの切替
if(WIN32)
    set(OS_SRC
        src/serial_win.cpp
    )
    set(CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS ON)
else()
    set(OS_SRC
        src/serial_linux.cpp
    )
endif()

add_library(pamc204 SHARED
    ${COMMON_SRC}
    ${OS_SRC}
)

# 名前の調整（Windows: pamc204.dll / Linux: libpamc204.so）
set_target_properties(pamc204 PROPERTIES
    OUTPUT_NAME "pamc204"
)

# テスト用実行ファイル
add_executable(test_serial demo/main.cpp)
target_link_libraries(test_serial pamc204)