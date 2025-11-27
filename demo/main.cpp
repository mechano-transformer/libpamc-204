#include "serial.h"
#include <iostream>

int main(int argc, char** argv) {
    std::string port;
    std::string cmd = "AT";

    if (argc >= 2) port = argv[1];
#ifdef _WIN32
    if (port.empty()) port = "COM3"; // 例
#else
    if (port.empty()) port = "/dev/ttyUSB0"; // 例
#endif
    if (argc >= 3) cmd = argv[2];

    bool ok = pamc204::send_command(port, cmd);
    std::cout << (ok ? "OK" : "NG") << std::endl;
    return ok ? 0 : 1;
}