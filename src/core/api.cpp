#include "pamc204.h"
#include <cstdio>
#include <string>

// ============================================================================
// C++ 高レベルAPI実装
// ============================================================================

namespace pamc204
{

    bool get_firmware_version(const std::string &portName, int address)
    {
        char cmd[32];
        std::snprintf(cmd, sizeof(cmd), "E%02dINF", address);
        return send_command(portName, cmd);
    }

    bool check_device(const std::string &portName, int address)
    {
        char cmd[32];
        std::snprintf(cmd, sizeof(cmd), "E%02d", address);
        return send_command(portName, cmd);
    }

    bool set_address(const std::string &portName, int new_address)
    {
        char cmd[32];
        std::snprintf(cmd, sizeof(cmd), "SETADDR%02d", new_address);
        return send_command(portName, cmd);
    }

    bool set_voltage(const std::string &portName, int address, int voltage_dac)
    {
        char cmd[32];
        std::snprintf(cmd, sizeof(cmd), "E%02dDAC%04d", address, voltage_dac);
        return send_command(portName, cmd);
    }

    bool rotate_positive(const std::string &portName, int address, int frequency, int pulses, char channel)
    {
        char cmd[64];
        std::snprintf(cmd, sizeof(cmd), "E%02dNR%04d%04d%c", address, frequency, pulses, channel);
        return send_command(portName, cmd);
    }

    bool rotate_positive_ex(const std::string &portName, int address, int frequency, int pulses, char channel)
    {
        char cmd[64];
        std::snprintf(cmd, sizeof(cmd), "E%02dNR%04dX%06d%c", address, frequency, pulses, channel);
        return send_command(portName, cmd);
    }

    bool rotate_negative(const std::string &portName, int address, int frequency, int pulses, char channel)
    {
        char cmd[64];
        std::snprintf(cmd, sizeof(cmd), "E%02dRR%04d%04d%c", address, frequency, pulses, channel);
        return send_command(portName, cmd);
    }

    bool rotate_negative_ex(const std::string &portName, int address, int frequency, int pulses, char channel)
    {
        char cmd[64];
        std::snprintf(cmd, sizeof(cmd), "E%02dRR%04dX%06d%c", address, frequency, pulses, channel);
        return send_command(portName, cmd);
    }

    bool stop(const std::string &portName, int address)
    {
        char cmd[32];
        std::snprintf(cmd, sizeof(cmd), "E%02dS", address);
        return send_command(portName, cmd);
    }

} // namespace pamc204

// ============================================================================
// C API実装（C++関数をラップ）
// ============================================================================

extern "C"
{

    bool pamc204_send_command(const char *port_name, const char *command)
    {
        if (!port_name || !command)
            return false;
        return pamc204::send_command(std::string(port_name), std::string(command));
    }

    bool pamc204_get_firmware_version(const char *port_name, int address)
    {
        if (!port_name)
            return false;
        return pamc204::get_firmware_version(std::string(port_name), address);
    }

    bool pamc204_check_device(const char *port_name, int address)
    {
        if (!port_name)
            return false;
        return pamc204::check_device(std::string(port_name), address);
    }

    bool pamc204_set_address(const char *port_name, int new_address)
    {
        if (!port_name)
            return false;
        return pamc204::set_address(std::string(port_name), new_address);
    }

    bool pamc204_set_voltage(const char *port_name, int address, int voltage_dac)
    {
        if (!port_name)
            return false;
        return pamc204::set_voltage(std::string(port_name), address, voltage_dac);
    }

    bool pamc204_rotate_positive(const char *port_name, int address, int frequency, int pulses, char channel)
    {
        if (!port_name)
            return false;
        return pamc204::rotate_positive(std::string(port_name), address, frequency, pulses, channel);
    }

    bool pamc204_rotate_positive_ex(const char *port_name, int address, int frequency, int pulses, char channel)
    {
        if (!port_name)
            return false;
        return pamc204::rotate_positive_ex(std::string(port_name), address, frequency, pulses, channel);
    }

    bool pamc204_rotate_negative(const char *port_name, int address, int frequency, int pulses, char channel)
    {
        if (!port_name)
            return false;
        return pamc204::rotate_negative(std::string(port_name), address, frequency, pulses, channel);
    }

    bool pamc204_rotate_negative_ex(const char *port_name, int address, int frequency, int pulses, char channel)
    {
        if (!port_name)
            return false;
        return pamc204::rotate_negative_ex(std::string(port_name), address, frequency, pulses, channel);
    }

    bool pamc204_stop(const char *port_name, int address)
    {
        if (!port_name)
            return false;
        return pamc204::stop(std::string(port_name), address);
    }

} // extern "C"