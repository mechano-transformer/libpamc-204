cmake_minimum_required(VERSION 3.15)
project(libpamc204 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# 公開ヘッダ
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/include)

# 内部ヘッダ（src/core）
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/src/core)

# コアソース（プラットフォーム非依存）
set(CORE_SRC
    src/core/utils.cpp
    src/core/pamc204.cpp
)

# プラットフォーム固有のソース
if(WIN32)
    set(PLATFORM_SRC
        src/platform/windows/serial.cpp
    )
    set(CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS ON)
else()
    set(PLATFORM_SRC
        src/platform/linux/serial.cpp
    )
endif()

# 共有ライブラリのビルド
add_library(pamc204 SHARED
    ${CORE_SRC}
    ${PLATFORM_SRC}
)

# ライブラリ名の設定（Windows: pamc204.dll / Linux: libpamc204.so）
set_target_properties(pamc204 PROPERTIES
    OUTPUT_NAME "pamc204"
)

# Windows の場合は SetupAPI をリンク
if(WIN32)
    target_link_libraries(pamc204 PRIVATE SetupAPI)
endif()

# テスト用実行ファイル
add_executable(test_serial demo/main.cpp)
target_link_libraries(test_serial pamc204)