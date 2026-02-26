#ifndef PAMC204_H
#define PAMC204_H

#include <string>
#include <vector>

// ============================================================================
// C++ API
// ============================================================================

namespace pamc204
{
// ========================================================================
// 低レベルAPI
// ========================================================================

/**
 * @brief 汎用コマンド送信（低レベルAPI）
 * @param command コマンド文字列
 * @return レスポンス文字列。失敗時または空レスポンス時は空文字列。
 * @note エラーレスポンス（ERROR, BUSY 等）の場合も文字列として返す。
 *       呼び出し元でエラー判定が必要な場合は find_error_token() を使用すること。
 */
std::string send_command(const std::string &command);

/**
 * @brief 複数のコマンドを1回のポート開閉で順次送信する（効率化版・低レベルAPI）
 * @param commands 送信するコマンド文字列の配列
 * @return 各コマンドのレスポンス文字列の配列。
 *         失敗時（ポートオープン失敗・書き込み失敗等）は空の vector を返す。
 *         個々のコマンドがエラーレスポンスを返した場合もその文字列を格納する。
 * @note ポートを1回だけ開閉し、複数コマンドを順次送信します。
 *       各コマンド送信後、レスポンスを受信してから次のコマンドを送信します。
 *       プラットフォーム固有の実装（serial.cpp）で実装されます。
 */
std::vector<std::string> send_commands_batch(const std::vector<std::string> &commands);

// ========================================================================
// 高レベルAPI（個別コマンド専用関数）
// ========================================================================

/**
 * @brief ファームウェアバージョンを取得（ExxINF）
 * @return レスポンス文字列。失敗時は空文字列。
 */
std::string get_firmware_version(int address);

/**
 * @brief デバイスの存在確認（Exx）
 * @return レスポンス文字列。失敗時は空文字列。
 */
std::string check_device(int address);

/**
 * @brief デバイスアドレスを変更（SETADDRxx）
 * @return レスポンス文字列。失敗時は空文字列。
 */
std::string set_address(int new_address);

/**
 * @brief 出力電圧を設定（ExxDACnnnn）
 * @param voltage_dac DAC値（1900=70V, 2200=80V, 2450=90V, 2700=100V, 3000=110V, 3200=120V,
 * 3450=130V, 3750=140V, 4095=150V）
 * @return レスポンス文字列。失敗時は空文字列。
 */
std::string set_voltage(int address, int voltage_dac);

/**
 * @brief 正回転駆動（ExxNRnnnnyyyyz）
 * @param frequency 周波数（1-1500 Hz）
 * @param pulses パルス数（0=連続駆動, 1-9999）
 * @param channel 軸指定（'A'=Axis1, 'B'=Axis2, 'C'=Axis3, 'D'=Axis4）
 * @return レスポンス文字列。失敗時は空文字列。
 */
std::string rotate_positive(int address, int frequency, int pulses, char channel);

/**
 * @brief 正回転駆動・拡張パルス数（ExxNRnnnnXyyyyyyz）
 * @param pulses パルス数（1-999999）
 * @return レスポンス文字列。失敗時は空文字列。
 */
std::string rotate_positive_ex(int address, int frequency, int pulses, char channel);

/**
 * @brief 逆回転駆動（ExxRRnnnnyyyyz）
 * @return レスポンス文字列。失敗時は空文字列。
 */
std::string rotate_negative(int address, int frequency, int pulses, char channel);

/**
 * @brief 逆回転駆動・拡張パルス数（ExxRRnnnnXyyyyyyz）
 * @return レスポンス文字列。失敗時は空文字列。
 */
std::string rotate_negative_ex(int address, int frequency, int pulses, char channel);

/**
 * @brief モーター停止（ExxS）
 * @return レスポンス文字列。失敗時は空文字列。
 */
std::string stop(int address);

/**
 * @brief モーション停止（ExxAB）
 * @return レスポンス文字列。失敗時は空文字列。
 */
std::string abort_motion(int address);

/**
 * @brief 加速度設定（ExxmACnnnn）
 * @param acceleration 加速度（1-150000 steps/sec²）
 * @return レスポンス文字列。失敗時は空文字列。
 */
std::string set_acceleration(int address, int channel, int acceleration);

/**
 * @brief 加速度問い合わせ（ExxmAC?）
 * @return 加速度値（整数）。失敗時は -1。
 */
int query_acceleration(int address, int channel);

/**
 * @brief 速度設定（ExxmVAnnnn）
 * @param velocity 速度（1-1500 steps/sec）
 * @return レスポンス文字列。失敗時は空文字列。
 */
std::string set_velocity(int address, int channel, int velocity);

/**
 * @brief 速度問い合わせ（ExxmVA?）
 * @return 速度値（整数）。失敗時は -1。
 */
int query_velocity(int address, int channel);

/**
 * @brief ホームポジション設定（ExxmDHnnnn）
 * @param position ホームポジション（-2147483648 ~ +2147483647）
 * @return レスポンス文字列。失敗時は空文字列。
 */
std::string set_home_position(int address, int channel, int position);

/**
 * @brief ホームポジション問い合わせ（ExxmDH?）
 * @return ホームポジション値（整数）。失敗時は INT_MIN。
 */
int query_home_position(int address, int channel);

/**
 * @brief 絶対位置移動（ExxmPAnnnn）
 * @param position 絶対位置（-2147483648 ~ +2147483647）
 * @return レスポンス文字列。失敗時は空文字列。
 */
std::string move_absolute(int address, int channel, int position);

/**
 * @brief 絶対位置問い合わせ（ExxmPA?）
 * @return 絶対位置値（整数）。失敗時は INT_MIN。
 */
int query_absolute_position(int address, int channel);

/**
 * @brief 相対位置移動（ExxmPRnnnn）
 * @param position 相対位置（-2147483648 ~ +2147483647）
 * @return レスポンス文字列。失敗時は空文字列。
 */
std::string move_relative(int address, int channel, int position);

/**
 * @brief 相対位置問い合わせ（ExxmPR?）
 * @return 相対位置値（整数）。失敗時は INT_MIN。
 */
int query_relative_position(int address, int channel);

/**
 * @brief 実位置問い合わせ（ExxmTP?）
 * @return 実位置値（整数）。失敗時は INT_MIN。
 */
int query_actual_position(int address, int channel);

/**
 * @brief 動作状態確認（ExxmMD?）
 * @return 0=動作中(Moving), 1=停止(Stopped)。失敗時は -1。
 */
int query_motion_status(int address, int channel);

/**
 * @brief 無限移動（ExxmMVn）
 * @param direction 方向（'+' または '-'）
 * @return レスポンス文字列。失敗時は空文字列。
 */
std::string move_infinite(int address, int channel, char direction);

/**
 * @brief 移動方向問い合わせ（ExxmMV?）
 * @return '+' または '-'。失敗時は '\0'。
 */
char query_move_direction(int address, int channel);

/**
 * @brief 動作停止（ExxmST）
 * @return レスポンス文字列。失敗時は空文字列。
 */
std::string stop_motion(int address, int channel);

// ========================================================================
// 4チャンネル同時操作API
// ========================================================================

/**
 * @brief 4チャンネル同時相対位置移動（全チャンネル同じ距離）
 * @param position 全チャンネルに適用する相対位置
 * @return 各チャンネルのレスポンス文字列の配列[4]。失敗時は空の vector。
 */
std::vector<std::string> move_relative_all_channels(int address, int position);

/**
 * @brief 4チャンネル同時実位置問い合わせ
 * @return 各チャンネルの実位置の配列[4]。失敗時は空の vector。
 *         個々のチャンネルが失敗した場合は INT_MIN を格納。
 */
std::vector<int> query_actual_position_all_channels(int address);

/**
 * @brief 4チャンネル同時動作状態確認
 * @return 各チャンネルの状態の配列[4]（0=動作中、1=停止、-1=エラー）。
 *         失敗時は空の vector。
 */
std::vector<int> query_motion_status_all_channels(int address);

/**
 * @brief 4チャンネル同時無限移動
 * @param direction 移動方向（'+' または '-'）
 * @return 各チャンネルのレスポンス文字列の配列[4]。失敗時は空の vector。
 */
std::vector<std::string> move_infinite_all_channels(int address, char direction);

/**
 * @brief 4チャンネル同時動作停止
 * @return 各チャンネルのレスポンス文字列の配列[4]。失敗時は空の vector。
 */
std::vector<std::string> stop_motion_all_channels(int address);
} // namespace pamc204

// ============================================================================
// C API（extern "C"）
// ============================================================================

#ifdef __cplusplus
extern "C"
{
#endif

    // 低レベルAPI
    // out_response: レスポンスを格納するバッファ（nullptr 可）
    // out_size: バッファサイズ
    // 戻り値: 成功時 true、失敗時 false
    bool pamc204_send_command(const char *command, char *out_response, int out_size);

    // 高レベルAPI（設定系: 成功/失敗を bool で返す）
    bool pamc204_get_firmware_version(int address);
    bool pamc204_check_device(int address);
    bool pamc204_set_address(int new_address);
    bool pamc204_set_voltage(int address, int voltage_dac);
    bool pamc204_rotate_positive(int address, int frequency, int pulses, char channel);
    bool pamc204_rotate_positive_ex(int address, int frequency, int pulses, char channel);
    bool pamc204_rotate_negative(int address, int frequency, int pulses, char channel);
    bool pamc204_rotate_negative_ex(int address, int frequency, int pulses, char channel);
    bool pamc204_stop(int address);
    bool pamc204_abort_motion(int address);
    bool pamc204_set_acceleration(int address, int channel, int acceleration);
    bool pamc204_set_velocity(int address, int channel, int velocity);
    bool pamc204_set_home_position(int address, int channel, int position);
    bool pamc204_move_absolute(int address, int channel, int position);
    bool pamc204_move_relative(int address, int channel, int position);
    bool pamc204_move_infinite(int address, int channel, char direction);
    bool pamc204_stop_motion(int address, int channel);

    // 高レベルAPI（問い合わせ系: 値を int で返す、失敗時は -1 または INT_MIN）
    int pamc204_query_acceleration(int address, int channel);
    int pamc204_query_velocity(int address, int channel);
    int pamc204_query_home_position(int address, int channel);
    int pamc204_query_absolute_position(int address, int channel);
    int pamc204_query_relative_position(int address, int channel);
    int pamc204_query_actual_position(int address, int channel);
    int pamc204_query_motion_status(int address, int channel);
    char pamc204_query_move_direction(int address, int channel);

    // 4軸同時操作API
    bool pamc204_move_relative_all_channels(int address, int position);
    bool pamc204_query_actual_position_all_channels(int address, int positions[4]);
    bool pamc204_query_motion_status_all_channels(int address, int statuses[4]);
    bool pamc204_move_infinite_all_channels(int address, char direction);
    bool pamc204_stop_motion_all_channels(int address);

#ifdef __cplusplus
}
#endif

#endif // PAMC204_H
