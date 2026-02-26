#include "pamc204.h"
#include <iostream>

int main(int argc, char **argv)
{
    std::string cmd = "E01INF"; // デフォルトコマンド

    if (argc >= 2)
        cmd = argv[1]; // 引数は cmd のみ受け取る

    const std::string resp = pamc204::send_command(cmd);
    const bool ok = !resp.empty();
    std::cout << (ok ? "OK" : "NG") << std::endl;
    return ok ? 0 : 1;
}