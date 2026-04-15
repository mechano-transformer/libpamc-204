#include "pamc204.h"
#include <climits>
#include <cstdio>
#include <sstream>
#include <string>
#include <vector>

// ============================================================================
// C++ 高レベルAPI実装
// ============================================================================
// 注: 各関数の詳細なドキュメントは include/pamc204.h を参照してください

namespace pamc204
{

// ── 内部ヘルパー ────────────────────────────────────────────────────────────

/**
 * @brief send_commands_batch を1コマンドで呼び出し、レスポンス文字列を返す内部ヘルパー。
 * @return レスポンス文字列。失敗時は空文字列。
 */
static std::string send_one(const std::string &cmd)
{
    auto responses = send_commands_batch({cmd});
    if (responses.empty())
        return std::string();
    return responses[0];
}

/**
 * @brief レスポンスの最後の非空行を返す内部ヘルパー。
 *
 * デバイスがコマンドをエコーバックする場合、レスポンスが
 * "E011TP?\r\n1234\r\n" のように複数行になる。
 * 実際の応答値は最後の行に含まれるため、最後の非空行を返す。
 */
static std::string last_nonempty_line(const std::string &resp)
{
    std::string last_line;
    std::istringstream ss(resp);
    std::string line;
    while (std::getline(ss, line))
    {
        if (!line.empty() && line.back() == '\r')
            line.pop_back();
        if (!line.empty())
            last_line = line;
    }
    return last_line;
}

/**
 * @brief レスポンス文字列を int にパースする内部ヘルパー。
 * @param resp レスポンス文字列
 * @param fallback パース失敗時の戻り値（デフォルト: INT_MIN）
 * @return パース結果。失敗時は fallback。
 */
static int parse_int(const std::string &resp, int fallback = INT_MIN)
{
    if (resp.empty())
        return fallback;
    const std::string val = last_nonempty_line(resp);
    if (val.empty())
        return fallback;
    try
    {
        return std::stoi(val);
    }
    catch (...)
    {
        return fallback;
    }
}

// ── 低レベルAPI ─────────────────────────────────────────────────────────────

// send_command / send_commands_batch は platform/*/serial.cpp で実装

// ── 高レベルAPI（設定系: string を返す） ────────────────────────────────────

std::string get_firmware_version(int address)
{
    char cmd[32];
    std::snprintf(cmd, sizeof(cmd), "E%02dINF", address);
    return send_command(cmd);
}

std::string check_device(int address)
{
    char cmd[32];
    std::snprintf(cmd, sizeof(cmd), "E%02d", address);
    return send_command(cmd);
}

std::string set_address(int new_address)
{
    char cmd[32];
    std::snprintf(cmd, sizeof(cmd), "SETADDR%02d", new_address);
    return send_command(cmd);
}

std::string set_voltage(int address, int voltage_dac)
{
    char cmd[32];
    std::snprintf(cmd, sizeof(cmd), "E%02dDAC%04d", address, voltage_dac);
    return send_command(cmd);
}

std::string rotate_positive(int address, int frequency, int pulses, char channel)
{
    char cmd[64];
    std::snprintf(cmd, sizeof(cmd), "E%02dNR%04d%04d%c", address, frequency, pulses, channel);
    return send_command(cmd);
}

std::string rotate_positive_ex(int address, int frequency, int pulses, char channel)
{
    char cmd[64];
    std::snprintf(cmd, sizeof(cmd), "E%02dNR%04dX%06d%c", address, frequency, pulses, channel);
    return send_command(cmd);
}

std::string rotate_negative(int address, int frequency, int pulses, char channel)
{
    char cmd[64];
    std::snprintf(cmd, sizeof(cmd), "E%02dRR%04d%04d%c", address, frequency, pulses, channel);
    return send_command(cmd);
}

std::string rotate_negative_ex(int address, int frequency, int pulses, char channel)
{
    char cmd[64];
    std::snprintf(cmd, sizeof(cmd), "E%02dRR%04dX%06d%c", address, frequency, pulses, channel);
    return send_command(cmd);
}

std::string stop(int address)
{
    char cmd[32];
    std::snprintf(cmd, sizeof(cmd), "E%02dS", address);
    return send_command(cmd);
}

std::string abort_motion(int address)
{
    char cmd[32];
    std::snprintf(cmd, sizeof(cmd), "E%02dAB", address);
    return send_command(cmd);
}

std::string set_acceleration(int address, int channel, int acceleration)
{
    char cmd[32];
    std::snprintf(cmd, sizeof(cmd), "E%02d%dAC%d", address, channel, acceleration);
    return send_command(cmd);
}

std::string set_velocity(int address, int channel, int velocity)
{
    char cmd[32];
    std::snprintf(cmd, sizeof(cmd), "E%02d%dVA%d", address, channel, velocity);
    return send_command(cmd);
}

std::string set_home_position(int address, int channel, int position)
{
    char cmd[64];
    std::snprintf(cmd, sizeof(cmd), "E%02d%dDH%d", address, channel, position);
    return send_command(cmd);
}

std::string move_absolute(int address, int channel, int position)
{
    char cmd[64];
    std::snprintf(cmd, sizeof(cmd), "E%02d%dPA%d", address, channel, position);
    return send_command(cmd);
}

std::string move_relative(int address, int channel, int position)
{
    char cmd[64];
    std::snprintf(cmd, sizeof(cmd), "E%02d%dPR%d", address, channel, position);
    return send_command(cmd);
}

std::string move_infinite(int address, int channel, char direction)
{
    char cmd[32];
    std::snprintf(cmd, sizeof(cmd), "E%02d%dMV%c", address, channel, direction);
    return send_command(cmd);
}

std::string stop_motion(int address, int channel)
{
    char cmd[32];
    std::snprintf(cmd, sizeof(cmd), "E%02d%dST", address, channel);
    return send_command(cmd);
}

// ── 高レベルAPI（問い合わせ系: 値を返す） ───────────────────────────────────

int query_acceleration(int address, int channel)
{
    char cmd[32];
    std::snprintf(cmd, sizeof(cmd), "E%02d%dAC?", address, channel);

    std::string resp = send_one(cmd);
    if (resp.empty())
        return -1;

    std::string val = last_nonempty_line(resp);
    if (val.size() <= 3)
        return -1;

    std::string number_part = val.substr(3);

    return parse_int(number_part, -1);
}

int query_velocity(int address, int channel)
{
    char cmd[32];
    std::snprintf(cmd, sizeof(cmd), "E%02d%dVA?", address, channel);

    std::string resp = send_one(cmd);
    if (resp.empty())
        return -1;

    std::string val = last_nonempty_line(resp);
    if (val.size() <= 3)
        return -1;

    std::string number_part = val.substr(3);

    return parse_int(number_part, -1);
}

int query_home_position(int address, int channel)
{
    char cmd[32];
    std::snprintf(cmd, sizeof(cmd), "E%02d%dDH?", address, channel);

    std::string resp = send_one(cmd);
    if (resp.empty())
        return -1;

    std::string val = last_nonempty_line(resp);
    if (val.size() <= 3)
        return -1;

    std::string number_part = val.substr(3);

    return parse_int(number_part);
}

int query_absolute_position(int address, int channel)
{
    char cmd[32];
    std::snprintf(cmd, sizeof(cmd), "E%02d%dPA?", address, channel);

    std::string resp = send_one(cmd);
    if (resp.empty())
        return -1;

    std::string val = last_nonempty_line(resp);
    if (val.size() <= 3)
        return -1;

    std::string number_part = val.substr(3);

    return parse_int(number_part);
}

int query_relative_position(int address, int channel)
{
    char cmd[32];
    std::snprintf(cmd, sizeof(cmd), "E%02d%dPR?", address, channel);

    std::string resp = send_one(cmd);
    if (resp.empty())
        return -1;

    std::string val = last_nonempty_line(resp);
    if (val.size() <= 3)
        return -1;

    std::string number_part = val.substr(3);

    return parse_int(number_part);
}

int query_actual_position(int address, int channel)
{
    char cmd[32];
    std::snprintf(cmd, sizeof(cmd), "E%02d%dTP?", address, channel);

    std::string resp = send_one(cmd);
    if (resp.empty())
        return -1;

    std::string val = last_nonempty_line(resp);
    if (val.size() <= 3)
        return -1;

    // Extract everything after the first 3 characters
    std::string number_part = val.substr(3);

    return parse_int(number_part);
}

int query_motion_status(int address, int channel)
{
    char cmd[32];
    std::snprintf(cmd, sizeof(cmd), "E%02d%dMD?", address, channel);
    const std::string resp = send_one(cmd);
    if (resp.empty())
        return -1;

    const std::string val = last_nonempty_line(resp);
    if (val.empty())
        return -1;

    char c = val.back(); // last character

    if (c == '0' || c == '1')
        return c - '0';

    return -1;
}

char query_move_direction(int address, int channel)
{
    char cmd[32];
    std::snprintf(cmd, sizeof(cmd), "E%02d%dMV?", address, channel);
    const std::string resp = send_one(cmd);
    if (resp.empty())
        return '\0';
    const std::string val = last_nonempty_line(resp);
    if (val.empty())
        return '\0';
    return val.back();
}

// ── 4チャンネル同時操作API ──────────────────────────────────────────────────

std::vector<std::string> move_relative_all_channels(int address, int position)
{
    std::vector<std::string> commands;
    for (int ch = 1; ch <= 4; ch++)
    {
        char cmd[64];
        std::snprintf(cmd, sizeof(cmd), "E%02d%dPR%d", address, ch, position);
        commands.push_back(cmd);
    }
    return send_commands_batch(commands);
}

std::vector<int> query_actual_position_all_channels(int address)
{
    std::vector<std::string> commands;
    for (int ch = 1; ch <= 4; ch++)
    {
        char cmd[32];
        std::snprintf(cmd, sizeof(cmd), "E%02d%dTP?", address, ch);
        commands.push_back(cmd);
    }
    const auto responses = send_commands_batch(commands);
    if (responses.empty())
        return {};
    std::vector<int> positions;
    positions.reserve(4);
    for (size_t i = 0; i < responses.size() && i < 4; i++)
    {
        const std::string val = last_nonempty_line(responses[i]);
        if (val.size() <= 3)
        {
            positions.push_back(-1);
            continue;
        }
        std::string number_part = val.substr(3);
        positions.push_back(parse_int(number_part));
    }
    return positions;
}

std::vector<int> query_motion_status_all_channels(int address)
{
    std::vector<std::string> commands;
    for (int ch = 1; ch <= 4; ch++)
    {
        char cmd[32];
        std::snprintf(cmd, sizeof(cmd), "E%02d%dMD?", address, ch);
        commands.push_back(cmd);
    }
    const auto responses = send_commands_batch(commands);
    if (responses.empty())
        return {};
    std::vector<int> statuses;
    statuses.reserve(4);
    for (size_t i = 0; i < responses.size() && i < 4; i++)
    {
        const std::string val = last_nonempty_line(responses[i]);
        if (val.empty())
        {
            statuses.push_back(-1);
            continue;
        }
        char c = val.back();
        if (c == '0' || c == '1')
            statuses.push_back(c - '0');
        else
            statuses.push_back(-1);
    }
    return statuses;
}

std::vector<std::string> move_infinite_all_channels(int address, char direction)
{
    std::vector<std::string> commands;
    for (int ch = 1; ch <= 4; ch++)
    {
        char cmd[32];
        std::snprintf(cmd, sizeof(cmd), "E%02d%dMV%c", address, ch, direction);
        commands.push_back(cmd);
    }
    return send_commands_batch(commands);
}

std::vector<std::string> stop_motion_all_channels(int address)
{
    std::vector<std::string> commands;
    for (int ch = 1; ch <= 4; ch++)
    {
        char cmd[32];
        std::snprintf(cmd, sizeof(cmd), "E%02d%dST", address, ch);
        commands.push_back(cmd);
    }
    return send_commands_batch(commands);
}

} // namespace pamc204

// ============================================================================
// C API実装（C++関数をラップ）
// ============================================================================

extern "C"
{

    bool pamc204_send_command(const char *command, char *out_response, int out_size)
    {
        if (!command)
            return false;
        const std::string resp = pamc204::send_command(std::string(command));
        if (out_response && out_size > 0)
        {
            std::snprintf(out_response, static_cast<size_t>(out_size), "%s", resp.c_str());
        }
        return !resp.empty();
    }

    // 設定系（bool を返す）
    bool pamc204_get_firmware_version(int address)
    {
        return !pamc204::get_firmware_version(address).empty();
    }
    bool pamc204_check_device(int address) { return !pamc204::check_device(address).empty(); }
    bool pamc204_set_address(int new_address) { return !pamc204::set_address(new_address).empty(); }
    bool pamc204_set_voltage(int address, int v)
    {
        return !pamc204::set_voltage(address, v).empty();
    }

    bool pamc204_rotate_positive(int address, int frequency, int pulses, char channel)
    {
        return !pamc204::rotate_positive(address, frequency, pulses, channel).empty();
    }
    bool pamc204_rotate_positive_ex(int address, int frequency, int pulses, char channel)
    {
        return !pamc204::rotate_positive_ex(address, frequency, pulses, channel).empty();
    }
    bool pamc204_rotate_negative(int address, int frequency, int pulses, char channel)
    {
        return !pamc204::rotate_negative(address, frequency, pulses, channel).empty();
    }
    bool pamc204_rotate_negative_ex(int address, int frequency, int pulses, char channel)
    {
        return !pamc204::rotate_negative_ex(address, frequency, pulses, channel).empty();
    }

    bool pamc204_stop(int address) { return !pamc204::stop(address).empty(); }
    bool pamc204_abort_motion(int address) { return !pamc204::abort_motion(address).empty(); }
    bool pamc204_set_acceleration(int address, int ch, int acc)
    {
        return !pamc204::set_acceleration(address, ch, acc).empty();
    }
    bool pamc204_set_velocity(int address, int ch, int vel)
    {
        return !pamc204::set_velocity(address, ch, vel).empty();
    }
    bool pamc204_set_home_position(int address, int ch, int pos)
    {
        return !pamc204::set_home_position(address, ch, pos).empty();
    }
    bool pamc204_move_absolute(int address, int ch, int pos)
    {
        return !pamc204::move_absolute(address, ch, pos).empty();
    }
    bool pamc204_move_relative(int address, int ch, int pos)
    {
        return !pamc204::move_relative(address, ch, pos).empty();
    }
    bool pamc204_move_infinite(int address, int ch, char dir)
    {
        return !pamc204::move_infinite(address, ch, dir).empty();
    }
    bool pamc204_stop_motion(int address, int ch)
    {
        return !pamc204::stop_motion(address, ch).empty();
    }

    // 問い合わせ系（値を int/char で返す）
    int pamc204_query_acceleration(int address, int ch)
    {
        return pamc204::query_acceleration(address, ch);
    }
    int pamc204_query_velocity(int address, int ch) { return pamc204::query_velocity(address, ch); }
    int pamc204_query_home_position(int address, int ch)
    {
        return pamc204::query_home_position(address, ch);
    }
    int pamc204_query_absolute_position(int address, int ch)
    {
        return pamc204::query_absolute_position(address, ch);
    }
    int pamc204_query_relative_position(int address, int ch)
    {
        return pamc204::query_relative_position(address, ch);
    }
    int pamc204_query_actual_position(int address, int ch)
    {
        return pamc204::query_actual_position(address, ch);
    }
    int pamc204_query_motion_status(int address, int ch)
    {
        return pamc204::query_motion_status(address, ch);
    }
    char pamc204_query_move_direction(int address, int ch)
    {
        return pamc204::query_move_direction(address, ch);
    }

    // 4軸同時操作API（配列引数版: 既存コードとの互換性のため維持）
    bool pamc204_move_relative_all_channels(int address, int position)
    {
        return !pamc204::move_relative_all_channels(address, position).empty();
    }

    bool pamc204_query_actual_position_all_channels(int address, int positions[4])
    {
        const auto result = pamc204::query_actual_position_all_channels(address);
        if (result.empty())
            return false;
        for (size_t i = 0; i < result.size() && i < 4; i++)
            positions[i] = result[i];
        return true;
    }

    bool pamc204_query_motion_status_all_channels(int address, int statuses[4])
    {
        const auto result = pamc204::query_motion_status_all_channels(address);
        if (result.empty())
            return false;
        for (size_t i = 0; i < result.size() && i < 4; i++)
            statuses[i] = result[i];
        return true;
    }

    bool pamc204_move_infinite_all_channels(int address, char direction)
    {
        return !pamc204::move_infinite_all_channels(address, direction).empty();
    }

    bool pamc204_stop_motion_all_channels(int address)
    {
        return !pamc204::stop_motion_all_channels(address).empty();
    }

} // extern "C"
