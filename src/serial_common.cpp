#include <string>
#include <algorithm>
#include <cctype>

std::string to_upper_ascii(const std::string& s) {
    std::string r = s;
    std::transform(r.begin(), r.end(), r.begin(),
                   [](unsigned char c){ return std::toupper(c); });
    return r;
}
