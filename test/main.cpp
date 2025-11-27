#include "serial.h"
#include <iostream>

int main() {
    if (pamc204::send_command("/dev/ttyUSB0", "AT")) {
        std::cout << "Command sent successfully\n";
    } else {
        std::cout << "Failed to send command\n";
    }
    return 0;
}
