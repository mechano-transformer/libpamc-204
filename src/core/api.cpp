#include "pamc204.h"
#include <cstdio>
#include <string>

// ============================================================================
// C++ 高レベルAPI実装
// ============================================================================

namespace pamc204
{

    bool get_firmware_version(int address)
    {
        char cmd[32];
        std::snprintf(cmd, sizeof(cmd), "E%02dINF", address);
        return send_command(cmd);
    }

    bool check_device(int address)
    {
        char cmd[32];
        std::snprintf(cmd, sizeof(cmd), "E%02d", address);
        return send_command(cmd);
    }

    bool set_address(int new_address)
    {
        char cmd[32];
        std::snprintf(cmd, sizeof(cmd), "SETADDR%02d", new_address);
        return send_command(cmd);
    }

    bool set_voltage(int address, int voltage_dac)
    {
        char cmd[32];
        std::snprintf(cmd, sizeof(cmd), "E%02dDAC%04d", address, voltage_dac);
        return send_command(cmd);
    }

    bool rotate_positive(int address, int frequency, int pulses, char channel)
    {
        char cmd[64];
        std::snprintf(cmd, sizeof(cmd), "E%02dNR%04d%04d%c", address, frequency, pulses, channel);
        return send_command(cmd);
    }

    bool rotate_positive_ex(int address, int frequency, int pulses, char channel)
    {
        char cmd[64];
        std::snprintf(cmd, sizeof(cmd), "E%02dNR%04dX%06d%c", address, frequency, pulses, channel);
        return send_command(cmd);
    }

    bool rotate_negative(int address, int frequency, int pulses, char channel)
    {
        char cmd[64];
        std::snprintf(cmd, sizeof(cmd), "E%02dRR%04d%04d%c", address, frequency, pulses, channel);
        return send_command(cmd);
    }

    bool rotate_negative_ex(int address, int frequency, int pulses, char channel)
    {
        char cmd[64];
        std::snprintf(cmd, sizeof(cmd), "E%02dRR%04dX%06d%c", address, frequency, pulses, channel);
        return send_command(cmd);
    }

    bool stop(int address)
    {
        char cmd[32];
        std::snprintf(cmd, sizeof(cmd), "E%02dS", address);
        return send_command(cmd);
    }

} // namespace pamc204

// ============================================================================
// C API実装（C++関数をラップ）
// ============================================================================

extern "C"
{

    bool pamc204_send_command(const char *command)
    {
        if (!command)
            return false;
        return pamc204::send_command(std::string(command));
    }

    bool pamc204_get_firmware_version(int address)
    {
        return pamc204::get_firmware_version(address);
    }

    bool pamc204_check_device(int address)
    {
        return pamc204::check_device(address);
    }

    bool pamc204_set_address(int new_address)
    {
        return pamc204::set_address(new_address);
    }

    bool pamc204_set_voltage(int address, int voltage_dac)
    {
        return pamc204::set_voltage(address, voltage_dac);
    }

    bool pamc204_rotate_positive(int address, int frequency, int pulses, char channel)
    {
        return pamc204::rotate_positive(address, frequency, pulses, channel);
    }

    bool pamc204_rotate_positive_ex(int address, int frequency, int pulses, char channel)
    {
        return pamc204::rotate_positive_ex(address, frequency, pulses, channel);
    }

    bool pamc204_rotate_negative(int address, int frequency, int pulses, char channel)
    {
        return pamc204::rotate_negative(address, frequency, pulses, channel);
    }

    bool pamc204_rotate_negative_ex(int address, int frequency, int pulses, char channel)
    {
        return pamc204::rotate_negative_ex(address, frequency, pulses, channel);
    }

    bool pamc204_stop(int address)
    {
        return pamc204::stop(address);
    }

} // extern "C"