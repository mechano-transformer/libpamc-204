#include "serial.h"
#include <windows.h>

namespace pamc204 {
    bool send_command(const std::string& portName, const std::string& command) {
        // Windows専用の CreateFileW, DCB, WriteFile などを利用
        return true; // 仮実装
    }
}
