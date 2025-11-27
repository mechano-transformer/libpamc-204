#pragma once
#include <string>

// ASCII範囲で大文字変換
std::string to_upper_ascii(const std::string& s);

// エラートークン検出
std::string find_error_token(const std::string& resp);