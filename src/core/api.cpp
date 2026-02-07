#include "pamc204.h"
#include <cstdio>
#include <string>
#include <chrono>
#include <thread>
#include <vector>

// ============================================================================
// C++ 高レベルAPI実装
// ============================================================================
// 注: 各関数の詳細なドキュメントは include/pamc204.h を参照してください

namespace pamc204
{
    // ファームウェアバージョン取得（ExxINF）
    bool get_firmware_version(int address)
    {
        char cmd[32];
        std::snprintf(cmd, sizeof(cmd), "E%02dINF", address);
        return send_command(cmd);
    }

    // デバイス存在確認（Exx）
    bool check_device(int address)
    {
        char cmd[32];
        std::snprintf(cmd, sizeof(cmd), "E%02d", address);
        return send_command(cmd);
    }

    // デバイスアドレス変更（SETADDRxx）
    bool set_address(int new_address)
    {
        char cmd[32];
        std::snprintf(cmd, sizeof(cmd), "SETADDR%02d", new_address);
        return send_command(cmd);
    }

    // 出力電圧設定（ExxDACnnnn）
    bool set_voltage(int address, int voltage_dac)
    {
        char cmd[32];
        std::snprintf(cmd, sizeof(cmd), "E%02dDAC%04d", address, voltage_dac);
        return send_command(cmd);
    }

    // 正回転駆動（ExxNRnnnnyyyyz）
    bool rotate_positive(int address, int frequency, int pulses, char channel)
    {
        char cmd[64];
        std::snprintf(cmd, sizeof(cmd), "E%02dNR%04d%04d%c", address, frequency, pulses, channel);
        return send_command(cmd);
    }

    // 正回転駆動・拡張パルス数（ExxNRnnnnXyyyyyyz）
    bool rotate_positive_ex(int address, int frequency, int pulses, char channel)
    {
        char cmd[64];
        std::snprintf(cmd, sizeof(cmd), "E%02dNR%04dX%06d%c", address, frequency, pulses, channel);
        return send_command(cmd);
    }

    // 逆回転駆動（ExxRRnnnnyyyyz）
    bool rotate_negative(int address, int frequency, int pulses, char channel)
    {
        char cmd[64];
        std::snprintf(cmd, sizeof(cmd), "E%02dRR%04d%04d%c", address, frequency, pulses, channel);
        return send_command(cmd);
    }

    // 逆回転駆動・拡張パルス数（ExxRRnnnnXyyyyyyz）
    bool rotate_negative_ex(int address, int frequency, int pulses, char channel)
    {
        char cmd[64];
        std::snprintf(cmd, sizeof(cmd), "E%02dRR%04dX%06d%c", address, frequency, pulses, channel);
        return send_command(cmd);
    }

    // モーター停止（ExxS）
    bool stop(int address)
    {
        char cmd[32];
        std::snprintf(cmd, sizeof(cmd), "E%02dS", address);
        return send_command(cmd);
    }

    // モーション停止（ExxAB）
    bool abort_motion(int address)
    {
        char cmd[32];
        std::snprintf(cmd, sizeof(cmd), "E%02dAB", address);
        return send_command(cmd);
    }

    // 加速度設定（ExxmACnnnn）
    bool set_acceleration(int address, int channel, int acceleration)
    {
        char cmd[32];
        std::snprintf(cmd, sizeof(cmd), "E%02d%dAC%d", address, channel, acceleration);
        return send_command(cmd);
    }

    // 加速度問い合わせ（ExxmAC?）
    bool query_acceleration(int address, int channel)
    {
        char cmd[32];
        std::snprintf(cmd, sizeof(cmd), "E%02d%dAC?", address, channel);
        return send_command(cmd);
    }

    // 速度設定（ExxmVAnnnn）
    bool set_velocity(int address, int channel, int velocity)
    {
        char cmd[32];
        std::snprintf(cmd, sizeof(cmd), "E%02d%dVA%d", address, channel, velocity);
        return send_command(cmd);
    }

    // 速度問い合わせ（ExxmVA?）
    bool query_velocity(int address, int channel)
    {
        char cmd[32];
        std::snprintf(cmd, sizeof(cmd), "E%02d%dVA?", address, channel);
        return send_command(cmd);
    }

    // ホームポジション設定（ExxmDHnnnn）
    bool set_home_position(int address, int channel, int position)
    {
        char cmd[64];
        std::snprintf(cmd, sizeof(cmd), "E%02d%dDH%d", address, channel, position);
        return send_command(cmd);
    }

    // ホームポジション問い合わせ（ExxmDH?）
    bool query_home_position(int address, int channel)
    {
        char cmd[32];
        std::snprintf(cmd, sizeof(cmd), "E%02d%dDH?", address, channel);
        return send_command(cmd);
    }

    // 絶対位置移動（ExxmPAnnnn）
    bool move_absolute(int address, int channel, int position)
    {
        char cmd[64];
        std::snprintf(cmd, sizeof(cmd), "E%02d%dPA%d", address, channel, position);
        return send_command(cmd);
    }

    // 絶対位置問い合わせ（ExxmPA?）
    bool query_absolute_position(int address, int channel)
    {
        char cmd[32];
        std::snprintf(cmd, sizeof(cmd), "E%02d%dPA?", address, channel);
        return send_command(cmd);
    }

    // 相対位置移動（ExxmPRnnnn）
    bool move_relative(int address, int channel, int position)
    {
        char cmd[64];
        std::snprintf(cmd, sizeof(cmd), "E%02d%dPR%d", address, channel, position);
        return send_command(cmd);
    }

    // 相対位置問い合わせ（ExxmPR?）
    bool query_relative_position(int address, int channel)
    {
        char cmd[32];
        std::snprintf(cmd, sizeof(cmd), "E%02d%dPR?", address, channel);
        return send_command(cmd);
    }

    // 実位置問い合わせ（ExxmTP?）
    bool query_actual_position(int address, int channel)
    {
        char cmd[32];
        std::snprintf(cmd, sizeof(cmd), "E%02d%dTP?", address, channel);
        return send_command(cmd);
    }

    // 動作状態確認（ExxmMD?）
    bool query_motion_status(int address, int channel)
    {
        char cmd[32];
        std::snprintf(cmd, sizeof(cmd), "E%02d%dMD?", address, channel);
        return send_command(cmd);
    }

    // 無限移動（ExxmMVn）
    bool move_infinite(int address, int channel, char direction)
    {
        char cmd[32];
        std::snprintf(cmd, sizeof(cmd), "E%02d%dMV%c", address, channel, direction);
        return send_command(cmd);
    }

    // 移動方向問い合わせ（ExxmMV?）
    bool query_move_direction(int address, int channel)
    {
        char cmd[32];
        std::snprintf(cmd, sizeof(cmd), "E%02d%dMV?", address, channel);
        return send_command(cmd);
    }

    // 動作停止（ExxmST）
    bool stop_motion(int address, int channel)
    {
        char cmd[32];
        std::snprintf(cmd, sizeof(cmd), "E%02d%dST", address, channel);
        return send_command(cmd);
    }

    // ========================================================================
    // 4軸同時操作API実装
    // ========================================================================
    // 注: これらの関数は send_commands_batch() を使用して、
    //     1回のポート開閉で全軸のコマンドを送信します（効率化）

    /**
     * @brief 4軸同時相対位置移動の実装
     * @note 各軸に対してExxmPRnnnnコマンドを生成し、バッチ送信
     */
    bool move_relative_all_channels(int address, int position)
    {
        // 全軸分のコマンドを生成
        std::vector<std::string> commands;
        for (int ch = 1; ch <= 4; ch++)
        {
            char cmd[64];
            std::snprintf(cmd, sizeof(cmd), "E%02d%dPR%d", address, ch, position);
            commands.push_back(cmd);
        }

        // バッチ送信（1回のポート開閉で全コマンド送信）
        std::vector<std::string> responses;
        if (!send_commands_batch(commands, responses))
        {
            std::fprintf(stderr, "move_relative_all_channels: Batch command failed\n");
            return false;
        }

        return true;
    }

    /**
     * @brief 4軸同時実位置問い合わせの実装
     * @note 各軸に対してExxmTP?コマンドを生成し、バッチ送信
     *       レスポンスをパースしてpositions配列に格納
     */
    bool query_actual_position_all_channels(int address, int positions[4])
    {
        // 全軸分のコマンドを生成
        std::vector<std::string> commands;
        for (int ch = 1; ch <= 4; ch++)
        {
            char cmd[32];
            std::snprintf(cmd, sizeof(cmd), "E%02d%dTP?", address, ch);
            commands.push_back(cmd);
        }

        // バッチ送信（1回のポート開閉で全コマンド送信）
        std::vector<std::string> responses;
        if (!send_commands_batch(commands, responses))
        {
            std::fprintf(stderr, "query_actual_position_all_channels: Batch command failed\n");
            return false;
        }

        // レスポンスから位置情報を抽出してpositions配列に格納
        // レスポンス形式: 数値文字列（例: "1000", "-500"）
        for (size_t i = 0; i < responses.size() && i < 4; i++)
        {
            const std::string &resp = responses[i];
            try
            {
                positions[i] = std::stoi(resp);
            }
            catch (...)
            {
                // パースエラーまたは未接続の場合は0を設定
                positions[i] = 0;
                std::fprintf(stderr, "query_actual_position_all_channels: Invalid response for CH%zu: '%s'\n",
                             i + 1, resp.c_str());
            }
        }

        return true;
    }

    /**
     * @brief 4軸同時動作状態確認の実装
     * @note 各軸に対してExxmMD?コマンドを生成し、バッチ送信
     *       レスポンスをパースしてstatuses配列に格納（0=駆動中、1=停止）
     */
    bool query_motion_status_all_channels(int address, int statuses[4])
    {
        // 全軸分のコマンドを生成
        std::vector<std::string> commands;
        for (int ch = 1; ch <= 4; ch++)
        {
            char cmd[32];
            std::snprintf(cmd, sizeof(cmd), "E%02d%dMD?", address, ch);
            commands.push_back(cmd);
        }

        // バッチ送信（1回のポート開閉で全コマンド送信）
        std::vector<std::string> responses;
        if (!send_commands_batch(commands, responses))
        {
            std::fprintf(stderr, "query_motion_status_all_channels: Batch command failed\n");
            return false;
        }

        // レスポンスから状態情報を抽出してstatuses配列に格納
        // レスポンス形式: "0" (駆動中) または "1" (停止)
        for (size_t i = 0; i < responses.size() && i < 4; i++)
        {
            const std::string &resp = responses[i];
            // レスポンスから数値を抽出（0 or 1）
            if (!resp.empty() && (resp[0] == '0' || resp[0] == '1'))
            {
                statuses[i] = resp[0] - '0';
            }
            else
            {
                // パースエラーまたは未接続の場合は-1を設定
                statuses[i] = -1;
                std::fprintf(stderr, "query_motion_status_all_channels: Invalid response for CH%zu: '%s'\n",
                             i + 1, resp.c_str());
            }
        }

        return true;
    }

    /**
     * @brief 4軸同時無限移動の実装
     * @note 各軸に対してExxmMVnコマンドを生成し、バッチ送信
     */
    bool move_infinite_all_channels(int address, char direction)
    {
        // 全軸分のコマンドを生成
        std::vector<std::string> commands;
        for (int ch = 1; ch <= 4; ch++)
        {
            char cmd[32];
            std::snprintf(cmd, sizeof(cmd), "E%02d%dMV%c", address, ch, direction);
            commands.push_back(cmd);
        }

        // バッチ送信（1回のポート開閉で全コマンド送信）
        std::vector<std::string> responses;
        if (!send_commands_batch(commands, responses))
        {
            std::fprintf(stderr, "move_infinite_all_channels: Batch command failed\n");
            return false;
        }

        return true;
    }

    /**
     * @brief 4軸同時動作停止の実装
     * @note 各軸に対してExxmSTコマンドを生成し、バッチ送信
     */
    bool stop_motion_all_channels(int address)
    {
        // 全軸分のコマンドを生成
        std::vector<std::string> commands;
        for (int ch = 1; ch <= 4; ch++)
        {
            char cmd[32];
            std::snprintf(cmd, sizeof(cmd), "E%02d%dST", address, ch);
            commands.push_back(cmd);
        }

        // バッチ送信（1回のポート開閉で全コマンド送信）
        std::vector<std::string> responses;
        if (!send_commands_batch(commands, responses))
        {
            std::fprintf(stderr, "stop_motion_all_channels: Batch command failed\n");
            return false;
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
