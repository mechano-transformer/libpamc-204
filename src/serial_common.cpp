#include "serial_common.h"
#include <algorithm>
#include <cctype>
#include <vector>

std::string to_upper_ascii(const std::string& s) {
    std::string r = s;
    std::transform(r.begin(), r.end(), r.begin(),
                   [](unsigned char c){ return static_cast<char>(std::toupper(c)); });
    return r;
}

std::string find_error_token(const std::string& resp) {
    static const std::vector<std::string> tokens = {
        "Error Value Range",
        "ERROR1",
        "ERROR4",
        "ERROR5",
        "BUSY",
        "ERROR"
    };
    std::string uresp = to_upper_ascii(resp);
    for (const auto& tok : tokens) {
        std::string utok = to_upper_ascii(tok);
        if (uresp.find(utok) != std::string::npos) {
            return tok;
        }
    }
    return std::string();
}