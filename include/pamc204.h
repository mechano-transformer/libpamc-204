#ifndef SERIAL_H
#define SERIAL_H

#include <string>

// ============================================================================
// C++ API
// ============================================================================

namespace pamc204
{
    /**
     * @brief 汎用コマンド送信（低レベルAPI）
     * @param portName ポート名（Windows: "COM3", Linux: "/dev/ttyUSB0"）
     * @param command コマンド文字列
     * @return 成功時 true、失敗時 false
     */
    bool send_command(const std::string &portName, const std::string &command);

    // ========================================================================
    // 高レベルAPI（個別コマンド専用関数）
    // ========================================================================

    /**
     * @brief ファームウェアバージョンを取得（ExxINF）
     */
    bool get_firmware_version(const std::string &portName, int address);

    /**
     * @brief デバイスの存在確認（Exx）
     */
    bool check_device(const std::string &portName, int address);

    /**
     * @brief デバイスアドレスを変更（SETADDRxx）
     */
    bool set_address(const std::string &portName, int new_address);

    /**
     * @brief 出力電圧を設定（ExxDACnnnn）
     * @param voltage_dac DAC値（1900=70V, 2200=80V, 2450=90V, 2700=100V, 3000=110V, 3200=120V, 3450=130V, 3750=140V, 4095=150V）
     */
    bool set_voltage(const std::string &portName, int address, int voltage_dac);

    /**
     * @brief 正回転駆動（ExxNRnnnnyyyyz）
     * @param frequency 周波数（1-1500 Hz）
     * @param pulses パルス数（0=連続駆動, 1-9999）
     * @param channel チャンネル（'A'=CH1, 'B'=CH2, 'C'=CH3, 'D'=CH4）
     */
    bool rotate_positive(const std::string &portName, int address, int frequency, int pulses, char channel);

    /**
     * @brief 正回転駆動・拡張パルス数（ExxNRnnnnXyyyyyyz）
     * @param pulses パルス数（1-999999）
     */
    bool rotate_positive_ex(const std::string &portName, int address, int frequency, int pulses, char channel);

    /**
     * @brief 逆回転駆動（ExxRRnnnnyyyyz）
     */
    bool rotate_negative(const std::string &portName, int address, int frequency, int pulses, char channel);

    /**
     * @brief 逆回転駆動・拡張パルス数（ExxRRnnnnXyyyyyyz）
     */
    bool rotate_negative_ex(const std::string &portName, int address, int frequency, int pulses, char channel);

    /**
     * @brief モーター停止（ExxS）
     */
    bool stop(const std::string &portName, int address);
}

// ============================================================================
// C API（extern "C"）
// ============================================================================

#ifdef __cplusplus
extern "C"
{
#endif

    // 低レベルAPI
    bool pamc204_send_command(const char *port_name, const char *command);

    // 高レベルAPI
    bool pamc204_get_firmware_version(const char *port_name, int address);
    bool pamc204_check_device(const char *port_name, int address);
    bool pamc204_set_address(const char *port_name, int new_address);
    bool pamc204_set_voltage(const char *port_name, int address, int voltage_dac);
    bool pamc204_rotate_positive(const char *port_name, int address, int frequency, int pulses, char channel);
    bool pamc204_rotate_positive_ex(const char *port_name, int address, int frequency, int pulses, char channel);
    bool pamc204_rotate_negative(const char *port_name, int address, int frequency, int pulses, char channel);
    bool pamc204_rotate_negative_ex(const char *port_name, int address, int frequency, int pulses, char channel);
    bool pamc204_stop(const char *port_name, int address);

#ifdef __cplusplus
}
#endif

#endif // SERIAL_H