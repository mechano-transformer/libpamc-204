#include "utils.h"
#include <algorithm>
#include <cctype>
#include <vector>
#include <map>

std::string to_upper_ascii(const std::string &s)
{
    std::string r = s;
    std::transform(r.begin(), r.end(), r.begin(),
                   [](unsigned char c)
                   { return static_cast<char>(std::toupper(c)); });
    return r;
}

// エラーメッセージの詳細マップ
static const std::map<std::string, std::string> error_descriptions = {
    {"Error Value Range", "出力電圧の値が範囲外です（70V～150V）"},
    {"ERROR1", "コマンドが認識できません"},
    {"ERROR4", "6桁パルス数が範囲外です（1～999999）"},
    {"ERROR5", "4桁パルス数が範囲外です（1～9999）"},
    {"BUSY", "ドライバが駆動中です。停止後に再送信してください"},
    {"ERROR", "回転方向、周波数、チャンネル指定が不正、またはコマンド認識不可"}};

std::string find_error_token(const std::string &resp)
{
    // 優先順位順にチェック（より具体的なエラーを先に）
    static const std::vector<std::string> tokens = {
        "Error Value Range",
        "ERROR1",
        "ERROR4",
        "ERROR5",
        "BUSY",
        "ERROR"};
    std::string uresp = to_upper_ascii(resp);
    for (const auto &tok : tokens)
    {
        std::string utok = to_upper_ascii(tok);
        if (uresp.find(utok) != std::string::npos)
        {
            return tok;
        }
    }
    return std::string();
}

std::string get_error_description(const std::string &error_token)
{
    auto it = error_descriptions.find(error_token);
    if (it != error_descriptions.end())
    {
        return it->second;
    }
    return "不明なエラー";
}