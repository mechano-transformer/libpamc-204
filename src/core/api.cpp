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

    bool abort_motion(int address)
    {
        char cmd[32];
        std::snprintf(cmd, sizeof(cmd), "E%02dAB", address);
        return send_command(cmd);
    }

    bool set_acceleration(int address, int channel, int acceleration)
    {
        char cmd[32];
        std::snprintf(cmd, sizeof(cmd), "E%02d%dAC%d", address, channel, acceleration);
        return send_command(cmd);
    }

    bool query_acceleration(int address, int channel)
    {
        char cmd[32];
        std::snprintf(cmd, sizeof(cmd), "E%02d%dAC?", address, channel);
        return send_command(cmd);
    }

    bool set_velocity(int address, int channel, int velocity)
    {
        char cmd[32];
        std::snprintf(cmd, sizeof(cmd), "E%02d%dVA%d", address, channel, velocity);
        return send_command(cmd);
    }

    bool query_velocity(int address, int channel)
    {
        char cmd[32];
        std::snprintf(cmd, sizeof(cmd), "E%02d%dVA?", address, channel);
        return send_command(cmd);
    }

    bool set_home_position(int address, int channel, int position)
    {
        char cmd[64];
        std::snprintf(cmd, sizeof(cmd), "E%02d%dDH%d", address, channel, position);
        return send_command(cmd);
    }

    bool query_home_position(int address, int channel)
    {
        char cmd[32];
        std::snprintf(cmd, sizeof(cmd), "E%02d%dDH?", address, channel);
        return send_command(cmd);
    }

    bool move_absolute(int address, int channel, int position)
    {
        char cmd[64];
        std::snprintf(cmd, sizeof(cmd), "E%02d%dPA%d", address, channel, position);
        return send_command(cmd);
    }

    bool query_absolute_position(int address, int channel)
    {
        char cmd[32];
        std::snprintf(cmd, sizeof(cmd), "E%02d%dPA?", address, channel);
        return send_command(cmd);
    }

    bool move_relative(int address, int channel, int position)
    {
        char cmd[64];
        std::snprintf(cmd, sizeof(cmd), "E%02d%dPR%d", address, channel, position);
        return send_command(cmd);
    }

    bool query_relative_position(int address, int channel)
    {
        char cmd[32];
        std::snprintf(cmd, sizeof(cmd), "E%02d%dPR?", address, channel);
        return send_command(cmd);
    }

    bool query_actual_position(int address, int channel)
    {
        char cmd[32];
        std::snprintf(cmd, sizeof(cmd), "E%02d%dTP?", address, channel);
        return send_command(cmd);
    }

    bool query_motion_status(int address, int channel)
    {
        char cmd[32];
        std::snprintf(cmd, sizeof(cmd), "E%02d%dMD?", address, channel);
        return send_command(cmd);
    }

    bool move_infinite(int address, int channel, char direction)
    {
        char cmd[32];
        std::snprintf(cmd, sizeof(cmd), "E%02d%dMV%c", address, channel, direction);
        return send_command(cmd);
    }

    bool query_move_direction(int address, int channel)
    {
        char cmd[32];
        std::snprintf(cmd, sizeof(cmd), "E%02d%dMV?", address, channel);
        return send_command(cmd);
    }

    bool stop_motion(int address, int channel)
    {
        char cmd[32];
        std::snprintf(cmd, sizeof(cmd), "E%02d%dST", address, channel);
        return send_command(cmd);
    }

    // ========================================================================
    // 4軸同時操作API実装
    // ========================================================================

    bool move_relative_all_channels(int address, int position)
    {
        // 全軸に同じ相対位置を設定
        for (int ch = 1; ch <= 4; ch++)
        {
            if (!move_relative(address, ch, position))
            {
                std::fprintf(stderr, "move_relative_all_channels: Failed at axis %d\n", ch);
                return false; // エラーが発生した場合は即座に終了
            }
        }
        return true;
    }

    bool query_actual_position_all_channels(int address, int positions[4])
    {
        // 各軸の実位置を順次問い合わせ
        // 注: 実際のレスポンス解析はserial.cpp内で行われるため、
        // ここでは単にコマンドを送信するのみ
        for (int ch = 1; ch <= 4; ch++)
        {
            if (!query_actual_position(address, ch))
            {
                std::fprintf(stderr, "query_actual_position_all_channels: Failed at axis %d\n", ch);
                return false; // エラーが発生した場合は即座に終了
            }
        }
        return true;
    }

    bool query_motion_status_all_channels(int address, int statuses[4])
    {
        // 各軸の動作状態を順次問い合わせ
        // 注: 実際のレスポンス解析はserial.cpp内で行われるため、
        // ここでは単にコマンドを送信するのみ
        for (int ch = 1; ch <= 4; ch++)
        {
            if (!query_motion_status(address, ch))
            {
                std::fprintf(stderr, "query_motion_status_all_channels: Failed at axis %d\n", ch);
                return false; // エラーが発生した場合は即座に終了
            }
        }
        return true;
    }

    bool move_infinite_all_channels(int address, char direction)
    {
        // 全軸を同じ方向に無限移動
        for (int ch = 1; ch <= 4; ch++)
        {
            if (!move_infinite(address, ch, direction))
            {
                std::fprintf(stderr, "move_infinite_all_channels: Failed at axis %d\n", ch);
                return false; // エラーが発生した場合は即座に終了
            }
        }
        return true;
    }

    bool stop_motion_all_channels(int address)
    {
        // 全軸の動作を停止
        for (int ch = 1; ch <= 4; ch++)
        {
            if (!stop_motion(address, ch))
            {
                std::fprintf(stderr, "stop_motion_all_channels: Failed at axis %d\n", ch);
                return false; // エラーが発生した場合は即座に終了
            }
        }
        return true;
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

    // 位置制御API
    bool pamc204_abort_motion(int address)
    {
        return pamc204::abort_motion(address);
    }

    bool pamc204_set_acceleration(int address, int channel, int acceleration)
    {
        return pamc204::set_acceleration(address, channel, acceleration);
    }

    bool pamc204_query_acceleration(int address, int channel)
    {
        return pamc204::query_acceleration(address, channel);
    }

    bool pamc204_set_velocity(int address, int channel, int velocity)
    {
        return pamc204::set_velocity(address, channel, velocity);
    }

    bool pamc204_query_velocity(int address, int channel)
    {
        return pamc204::query_velocity(address, channel);
    }

    bool pamc204_set_home_position(int address, int channel, int position)
    {
        return pamc204::set_home_position(address, channel, position);
    }

    bool pamc204_query_home_position(int address, int channel)
    {
        return pamc204::query_home_position(address, channel);
    }

    bool pamc204_move_absolute(int address, int channel, int position)
    {
        return pamc204::move_absolute(address, channel, position);
    }

    bool pamc204_query_absolute_position(int address, int channel)
    {
        return pamc204::query_absolute_position(address, channel);
    }

    bool pamc204_move_relative(int address, int channel, int position)
    {
        return pamc204::move_relative(address, channel, position);
    }

    bool pamc204_query_relative_position(int address, int channel)
    {
        return pamc204::query_relative_position(address, channel);
    }

    bool pamc204_query_actual_position(int address, int channel)
    {
        return pamc204::query_actual_position(address, channel);
    }

    bool pamc204_query_motion_status(int address, int channel)
    {
        return pamc204::query_motion_status(address, channel);
    }

    bool pamc204_move_infinite(int address, int channel, char direction)
    {
        return pamc204::move_infinite(address, channel, direction);
    }

    bool pamc204_query_move_direction(int address, int channel)
    {
        return pamc204::query_move_direction(address, channel);
    }

    bool pamc204_stop_motion(int address, int channel)
    {
        return pamc204::stop_motion(address, channel);
    }

    // 4軸同時操作API
    bool pamc204_move_relative_all_channels(int address, int position)
    {
        return pamc204::move_relative_all_channels(address, position);
    }

    bool pamc204_query_actual_position_all_channels(int address, int positions[4])
    {
        return pamc204::query_actual_position_all_channels(address, positions);
    }

    bool pamc204_query_motion_status_all_channels(int address, int statuses[4])
    {
        return pamc204::query_motion_status_all_channels(address, statuses);
    }

    bool pamc204_move_infinite_all_channels(int address, char direction)
    {
        return pamc204::move_infinite_all_channels(address, direction);
    }

    bool pamc204_stop_motion_all_channels(int address)
    {
        return pamc204::stop_motion_all_channels(address);
    }

} // extern "C"