#pragma once
#include <string>

namespace pamc204 {
    // ポート名は OS ごとに形式が異なります。
    // Windows: "COM3" や "\\\\.\\COM3"
    // Linux: "/dev/ttyUSB0" など
    bool send_command(const std::string& portName, const std::string& command);
}