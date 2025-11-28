#include "pamc204.h"
#include <iostream>

int main(int argc, char **argv)
{
    std::string port;
    std::string cmd = "E01INF";

    if (argc >= 2)
        port = argv[1];

#if defined(_WIN32)
    if (port.empty())
        port = "COM3"; // Windows のデフォルト
#else
    if (port.empty())
        port = "/dev/ttyUSB0"; // Linux のデフォルト
#endif
    if (argc >= 3)
        cmd = argv[2];

    bool ok = pamc204::send_command(cmd);
    std::cout << (ok ? "OK" : "NG") << std::endl;
    return ok ? 0 : 1;
}