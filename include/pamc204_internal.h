#ifndef PAMC204_INTERNAL_H
#define PAMC204_INTERNAL_H

#include <string>

// ASCII範囲で大文字変換
std::string to_upper_ascii(const std::string &s);

// エラートークン検出
std::string find_error_token(const std::string &resp);

// エラーの詳細説明を取得
std::string get_error_description(const std::string &error_token);

#endif // PAMC204_INTERNAL_H