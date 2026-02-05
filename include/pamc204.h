#ifndef PAMC204_H
#define PAMC204_H

#include <string>

// ============================================================================
// C++ API
// ============================================================================

namespace pamc204
{
    /**
     * @brief 汎用コマンド送信（低レベルAPI）
     * @param command コマンド文字列
     * @return 成功時 true、失敗時 false
     */
    bool send_command(const std::string &command);

    // ========================================================================
    // 高レベルAPI（個別コマンド専用関数）
    // ========================================================================

    /**
     * @brief ファームウェアバージョンを取得（ExxINF）
     */
    bool get_firmware_version(int address);

    /**
     * @brief デバイスの存在確認（Exx）
     */
    bool check_device(int address);

    /**
     * @brief デバイスアドレスを変更（SETADDRxx）
     */
    bool set_address(int new_address);

    /**
     * @brief 出力電圧を設定（ExxDACnnnn）
     * @param voltage_dac DAC値（1900=70V, 2200=80V, 2450=90V, 2700=100V, 3000=110V, 3200=120V, 3450=130V, 3750=140V, 4095=150V）
     */
    bool set_voltage(int address, int voltage_dac);

    /**
     * @brief 正回転駆動（ExxNRnnnnyyyyz）
     * @param frequency 周波数（1-1500 Hz）
     * @param pulses パルス数（0=連続駆動, 1-9999）
     * @param channel 軸指定（'A'=Axis1, 'B'=Axis2, 'C'=Axis3, 'D'=Axis4）
     */
    bool rotate_positive(int address, int frequency, int pulses, char channel);

    /**
     * @brief 正回転駆動・拡張パルス数（ExxNRnnnnXyyyyyyz）
     * @param pulses パルス数（1-999999）
     */
    bool rotate_positive_ex(int address, int frequency, int pulses, char channel);

    /**
     * @brief 逆回転駆動（ExxRRnnnnyyyyz）
     */
    bool rotate_negative(int address, int frequency, int pulses, char channel);

    /**
     * @brief 逆回転駆動・拡張パルス数（ExxRRnnnnXyyyyyyz）
     */
    bool rotate_negative_ex(int address, int frequency, int pulses, char channel);

    /**
     * @brief モーター停止（ExxS）
     */
    bool stop(int address);

    /**
     * @brief モーション停止（ExxAB）
     * @param address ドライバアドレス（1-32）
     */
    bool abort_motion(int address);

    /**
     * @brief 加速度設定（ExxmACnnnn）
     * @param address ドライバアドレス（1-32）
     * @param channel 軸番号（1-4）
     * @param acceleration 加速度（1-150000 steps/sec²）
     */
    bool set_acceleration(int address, int channel, int acceleration);

    /**
     * @brief 加速度問い合わせ（ExxmAC?）
     * @param address ドライバアドレス（1-32）
     * @param channel 軸番号（1-4）
     */
    bool query_acceleration(int address, int channel);

    /**
     * @brief 速度設定（ExxmVAnnnn）
     * @param address ドライバアドレス（1-32）
     * @param channel 軸番号（1-4）
     * @param velocity 速度（1-1500 steps/sec）
     */
    bool set_velocity(int address, int channel, int velocity);

    /**
     * @brief 速度問い合わせ（ExxmVA?）
     * @param address ドライバアドレス（1-32）
     * @param channel 軸番号（1-4）
     */
    bool query_velocity(int address, int channel);

    /**
     * @brief ホームポジション設定（ExxmDHnnnn）
     * @param address ドライバアドレス（1-32）
     * @param channel 軸番号（1-4）
     * @param position ホームポジション（-2147483648 ~ +2147483647）
     */
    bool set_home_position(int address, int channel, int position);

    /**
     * @brief ホームポジション問い合わせ（ExxmDH?）
     * @param address ドライバアドレス（1-32）
     * @param channel 軸番号（1-4）
     */
    bool query_home_position(int address, int channel);

    /**
     * @brief 絶対位置移動（ExxmPAnnnn）
     * @param address ドライバアドレス（1-32）
     * @param channel 軸番号（1-4）
     * @param position 絶対位置（-2147483648 ~ +2147483647）
     */
    bool move_absolute(int address, int channel, int position);

    /**
     * @brief 絶対位置問い合わせ（ExxmPA?）
     * @param address ドライバアドレス（1-32）
     * @param channel 軸番号（1-4）
     */
    bool query_absolute_position(int address, int channel);

    /**
     * @brief 相対位置移動（ExxmPRnnnn）
     * @param address ドライバアドレス（1-32）
     * @param channel 軸番号（1-4）
     * @param position 相対位置（-2147483648 ~ +2147483647）
     */
    bool move_relative(int address, int channel, int position);

    /**
     * @brief 相対位置問い合わせ（ExxmPR?）
     * @param address ドライバアドレス（1-32）
     * @param channel 軸番号（1-4）
     */
    bool query_relative_position(int address, int channel);

    /**
     * @brief 実位置問い合わせ（ExxmTP?）
     * @param address ドライバアドレス（1-32）
     * @param channel 軸番号（1-4）
     */
    bool query_actual_position(int address, int channel);

    /**
     * @brief 動作状態確認（ExxmMD?）
     * @param address ドライバアドレス（1-32）
     * @param channel 軸番号（1-4）
     */
    bool query_motion_status(int address, int channel);

    /**
     * @brief 無限移動（ExxmMVn）
     * @param address ドライバアドレス（1-32）
     * @param channel 軸番号（1-4）
     * @param direction 方向（'+' または '-'）
     */
    bool move_infinite(int address, int channel, char direction);

    /**
     * @brief 移動方向問い合わせ（ExxmMV?）
     * @param address ドライバアドレス（1-32）
     * @param channel 軸番号（1-4）
     */
    bool query_move_direction(int address, int channel);

    /**
     * @brief 動作停止（ExxmST）
     * @param address ドライバアドレス（1-32）
     * @param channel 軸番号（1-4）
     */
    bool stop_motion(int address, int channel);

    // ========================================================================
    // 4チャンネル同時操作API
    // ========================================================================

    /**
     * @brief 4チャンネル同時相対位置移動（全チャンネル同じ距離）
     * @param address ドライバアドレス（1-32）
     * @param position 全チャンネルに適用する相対位置
     * @return 成功時 true、失敗時 false
     * @note 全チャンネルに対して同じ相対位置でExxmPRnnnnコマンドを順次実行します。
     *       各コマンド送信後、レスポンスを受信してから次のコマンドを送信します。
     *       レスポンスが返ってこない場合は2秒でタイムアウトし、falseを返します。
     *       各コマンド間には50msの待機時間を設けています。
     */
    bool move_relative_all_channels(int address, int position);

    /**
     * @brief 4チャンネル同時実位置問い合わせ
     * @param address ドライバアドレス（1-32）
     * @param positions 各チャンネルの実位置を格納する配列[4]
     * @return 成功時 true、失敗時 false
     * @note 各チャンネルに対してExxmTP?コマンドを順次実行します。
     *       各コマンド送信後、レスポンスを受信してから次のコマンドを送信します。
     *       レスポンスが返ってこない場合は2秒でタイムアウトし、falseを返します。
     *       各コマンド間には50msの待機時間を設けています。
     */
    bool query_actual_position_all_channels(int address, int positions[4]);

    /**
     * @brief 4チャンネル同時動作状態確認
     * @param address ドライバアドレス（1-32）
     * @param statuses 各チャンネルの状態を格納する配列[4]（0=駆動中、1=停止）
     * @return 成功時 true、失敗時 false
     * @note 各チャンネルに対してExxmMD?コマンドを順次実行します。
     *       各コマンド送信後、レスポンスを受信してから次のコマンドを送信します。
     *       レスポンスが返ってこない場合は2秒でタイムアウトし、falseを返します。
     *       各コマンド間には50msの待機時間を設けています。
     */
    bool query_motion_status_all_channels(int address, int statuses[4]);

    /**
     * @brief 4チャンネル同時無限移動
     * @param address ドライバアドレス（1-32）
     * @param direction 移動方向（'+' または '-'）
     * @return 成功時 true、失敗時 false
     * @note 全チャンネルに対して同じ方向でExxmMVnコマンドを順次実行します。
     *       各コマンド送信後、レスポンスを受信してから次のコマンドを送信します。
     *       レスポンスが返ってこない場合は2秒でタイムアウトし、falseを返します。
     *       各コマンド間には50msの待機時間を設けています。
     */
    bool move_infinite_all_channels(int address, char direction);

    /**
     * @brief 4チャンネル同時動作停止
     * @param address ドライバアドレス（1-32）
     * @return 成功時 true、失敗時 false
     * @note 全チャンネルに対してExxmSTコマンドを順次実行します。
     *       各コマンド送信後、レスポンスを受信してから次のコマンドを送信します。
     *       レスポンスが返ってこない場合は2秒でタイムアウトし、falseを返します。
     *       各コマンド間には50msの待機時間を設けています。
     */
    bool stop_motion_all_channels(int address);
}

// ============================================================================
// C API（extern "C"）
// ============================================================================

#ifdef __cplusplus
extern "C"
{
#endif

    // 低レベルAPI
    bool pamc204_send_command(const char *command);

    // 高レベルAPI
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
    bool pamc204_query_acceleration(int address, int channel);
    bool pamc204_set_velocity(int address, int channel, int velocity);
    bool pamc204_query_velocity(int address, int channel);
    bool pamc204_set_home_position(int address, int channel, int position);
    bool pamc204_query_home_position(int address, int channel);
    bool pamc204_move_absolute(int address, int channel, int position);
    bool pamc204_query_absolute_position(int address, int channel);
    bool pamc204_move_relative(int address, int channel, int position);
    bool pamc204_query_relative_position(int address, int channel);
    bool pamc204_query_actual_position(int address, int channel);
    bool pamc204_query_motion_status(int address, int channel);
    bool pamc204_move_infinite(int address, int channel, char direction);
    bool pamc204_query_move_direction(int address, int channel);
    bool pamc204_stop_motion(int address, int channel);

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