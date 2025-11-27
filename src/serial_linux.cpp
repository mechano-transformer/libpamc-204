#include "serial.h"
#include <termios.h>
#include <fcntl.h>
#include <unistd.h>
#include <string>

namespace pamc204 {
    bool send_command(const std::string& portName, const std::string& command) {
        int fd = open(portName.c_str(), O_RDWR | O_NOCTTY | O_SYNC);
        if (fd < 0) return false;

        struct termios tty;
        if (tcgetattr(fd, &tty) != 0) return false;

        cfsetospeed(&tty, B115200);
        cfsetispeed(&tty, B115200);
        tty.c_cflag = (tty.c_cflag & ~CSIZE) | CS8;
        tty.c_cflag &= ~(PARENB | CSTOPB | CRTSCTS);
        tty.c_cflag |= (CLOCAL | CREAD);
        tty.c_iflag &= ~(IXON | IXOFF | IXANY);
        tty.c_lflag = 0;
        tty.c_oflag = 0;
        tcsetattr(fd, TCSANOW, &tty);

        std::string msg = command + "\r\n";
        write(fd, msg.c_str(), msg.size());

        char buf[256];
        int n = read(fd, buf, sizeof(buf));
        if (n > 0) {
            std::string resp(buf, n);
            // TODO: エラートークン検出処理を呼ぶ
        }

        close(fd);
        return true;
    }
}
