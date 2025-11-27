#include "serial.h"
#include <termios.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include <chrono>
#include <thread>
#include <string>
#include <vector>
#include <cstdio>
#include "serial.h"
#include "serial_common.h"

// --- 共有のヘルパー（serial_common.cpp にある実装の宣言） ---
std::string to_upper_ascii(const std::string& s);
std::string find_error_token(const std::string& resp);

// Linux: 出力は stdout に行う
static void output_response_once_linux(const std::string& resp)
{
    if (resp.empty()) return;
    std::string token = find_error_token(resp);
    if (!token.empty()) {
        std::string errLine = "ERROR DETECTED: ";
        errLine += token;
        errLine += "\n";
        std::fwrite(errLine.data(), 1, errLine.size(), stdout);
        std::fflush(stdout);
        return;
    }
    std::string outMsg = resp;
    if (resp.empty() || (resp.back() != '\n' && resp.back() != '\r')) outMsg += "\n";
    std::fwrite(outMsg.data(), 1, outMsg.size(), stdout);
    std::fflush(stdout);
}

// termios 設定（115200 8N1 / フロー制御なし）
static bool configure_port_linux(int fd)
{
    struct termios tty;
    if (tcgetattr(fd, &tty) != 0) return false;

    cfsetospeed(&tty, B115200);
    cfsetispeed(&tty, B115200);

    tty.c_cflag = (tty.c_cflag & ~CSIZE) | CS8;        // 8bit
    tty.c_cflag &= ~(PARENB | CSTOPB | CRTSCTS);       // 8N1, no HW flow
    tty.c_cflag |= (CLOCAL | CREAD);

    tty.c_iflag &= ~(IXON | IXOFF | IXANY);            // no SW flow
    tty.c_lflag = 0;                                   // raw
    tty.c_oflag = 0;

    tty.c_cc[VMIN]  = 0;
    tty.c_cc[VTIME] = 1; // 0.1s

    return (tcsetattr(fd, TCSANOW, &tty) == 0);
}

// レスポンス読み取り（Windows版のロジックに近いポーリング）
static std::string read_response_from_port_linux(int fd, int totalTimeoutMs = 2000, int idleTimeoutMs = 200, size_t bufSize = 1024)
{
    std::string response;
    std::vector<char> buf(bufSize);

    auto now_ms = []() {
        return std::chrono::time_point_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now()).time_since_epoch().count();
    };

    long long start = now_ms();
    long long lastRead = start;
    bool started = false;

    while ((now_ms() - start) < totalTimeoutMs) {
        int bytesAvailable = 0;
        if (ioctl(fd, FIONREAD, &bytesAvailable) < 0) {
            break;
        }

        if (bytesAvailable <= 0) {
            if (started) {
                if ((now_ms() - lastRead) >= idleTimeoutMs) break;
            }
            std::this_thread::sleep_for(std::chrono::milliseconds(10));
            continue;
        }

        size_t toRead = (bytesAvailable > (int)bufSize) ? bufSize : (size_t)bytesAvailable;
        ssize_t n = ::read(fd, buf.data(), toRead);
        if (n < 0) break;
        if (n == 0) {
            std::this_thread::sleep_for(std::chrono::milliseconds(10));
            continue;
        }
        response.append(buf.data(), (size_t)n);
        started = true;
        lastRead = now_ms();
    }
    return response;
}

namespace pamc204 {
    // 共通API（Linux版）
    bool send_command(const std::string& portName, const std::string& command)
    {
        // Linux のポート名はそのまま（例: "/dev/ttyUSB0"）
        int fd = ::open(portName.c_str(), O_RDWR | O_NOCTTY | O_SYNC);
        if (fd < 0) {
            return false;
        }

        bool ok = configure_port_linux(fd);
        if (!ok) {
            ::close(fd);
            return false;
        }

        std::string msg = command;
        msg.append("\r\n");
        ssize_t written = ::write(fd, msg.data(), msg.size());
        if (written != (ssize_t)msg.size()) {
            ::close(fd);
            return false;
        }

        std::string resp = read_response_from_port_linux(fd);
        ::close(fd);

        if (!resp.empty()) {
            std::string token = find_error_token(resp);
            if (!token.empty()) {
                std::string errLine = "ERROR DETECTED: ";
                errLine += token;
                errLine += "\n";
                std::fwrite(errLine.data(), 1, errLine.size(), stdout);
                std::fflush(stdout);
                return false;
            }
            output_response_once_linux(resp);
        }
        return true;
    }
}