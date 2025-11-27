#pragma once
#include <string>

namespace pamc204 {
    bool send_command(const std::string& portName, const std::string& command);
}
