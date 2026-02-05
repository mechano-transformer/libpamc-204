#ifndef PAMC204_SERIAL_H
#define PAMC204_SERIAL_H

#include <string>

// ============================================================================
// プラットフォーム固有のシリアル通信関数
// ============================================================================

namespace pamc204
{
    /**
     * @brief シリアルポート経由でコマンドを送信し、レスポンスを受信する
     * @param command 送信するコマンド文字列（改行コードは自動付与）
     * @return 成功時 true、失敗時 false
     * @note この関数はプラットフォーム固有の実装を持ちます:
     *       - Linux: src/platform/linux/serial.cpp
     *       - Windows: src/platform/windows/serial.cpp
     */
    bool send_command(const std::string &command);
}

// ============================================================================
// C API
// ============================================================================

#ifdef __cplusplus
extern "C"
{
#endif

    /**
     * @brief シリアルポート経由でコマンドを送信（C API）
     * @param command 送信するコマンド文字列（NULL終端）
     * @return 成功時 true、失敗時 false
     */
    bool send_command(const char *command);

#ifdef __cplusplus
}
#endif

#endif // PAMC204_SERIAL_H
