#include "pamc204.h"
#include "utils.h"
#include <array>
#include <cerrno>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fcntl.h>
#include <filesystem>
#include <sstream>
#include <string>
#include <sys/ioctl.h>
#include <termios.h>
#include <thread>
#include <unistd.h>
#include <vector>

/**
 * @brief レスポンスを標準出力に出力する（Linux版）
 * @param resp デバイスからのレスポンス文字列
 * @note エラートークンが含まれている場合は "ERROR DETECTED: " を付けて出力
 */
static void output_response(const std::string &resp)
{
    if (resp.empty())
        return;
    std::string token = find_error_token(resp);
    if (!token.empty())
    {
        std::string errLine = "ERROR DETECTED: ";
        errLine += token;
        errLine += "\n";
        std::fwrite(errLine.data(), 1, errLine.size(), stdout);
        std::fflush(stdout);
        return;
    }
    std::string outMsg = resp;
    if (resp.empty() || (resp.back() != '\n' && resp.back() != '\r'))
        outMsg += "\n";
    std::fwrite(outMsg.data(), 1, outMsg.size(), stdout);
    std::fflush(stdout);
}

/**
 * @brief シリアルポートの通信設定を行う
 * @param fd ファイルディスクリプタ
 * @return 成功時 true、失敗時 false
 * @note 設定内容: 115200bps, 8bit, パリティなし, ストップビット1, フロー制御なし
 */
static bool configure_port(int fd)
{
    struct termios tty;
    if (tcgetattr(fd, &tty) != 0)
        return false;

    cfsetospeed(&tty, B115200);
    cfsetispeed(&tty, B115200);

    tty.c_cflag = (tty.c_cflag & ~CSIZE) | CS8;  // 8bit
    tty.c_cflag &= ~(PARENB | CSTOPB | CRTSCTS); // 8N1, no HW flow
    tty.c_cflag |= (CLOCAL | CREAD);

    tty.c_iflag &= ~(IXON | IXOFF | IXANY); // no SW flow
    tty.c_lflag = 0;                        // raw
    tty.c_oflag = 0;

    tty.c_cc[VMIN] = 0;
    tty.c_cc[VTIME] = 1; // 0.1s

    return (tcsetattr(fd, TCSANOW, &tty) == 0);
}

/**
 * @brief シリアルポートからレスポンスを読み取る
 * @param fd ファイルディスクリプタ
 * @param totalTimeoutMs 全体のタイムアウト時間（ミリ秒）
 * @param idleTimeoutMs データ受信が途切れた際のアイドルタイムアウト（ミリ秒）
 * @param bufSize 読み取りバッファサイズ
 * @return 受信したレスポンス文字列
 * @note ポーリング方式でデータを読み取り、アイドル時間が経過したら読み取りを終了
 */
static std::string read_response(int fd, int totalTimeoutMs = 2000, int idleTimeoutMs = 200,
                                 size_t bufSize = 1024)
{
    std::string response;
    std::vector<char> buf(bufSize);

    auto now_ms = []()
    {
        return std::chrono::time_point_cast<std::chrono::milliseconds>(
                   std::chrono::steady_clock::now())
            .time_since_epoch()
            .count();
    };

    long long start = now_ms();
    long long lastRead = start;
    bool started = false;

    while ((now_ms() - start) < totalTimeoutMs)
    {
        int bytesAvailable = 0;
        if (ioctl(fd, FIONREAD, &bytesAvailable) < 0)
        {
            break;
        }

        if (bytesAvailable <= 0)
        {
            if (started)
            {
                if ((now_ms() - lastRead) >= idleTimeoutMs)
                    break;
            }
            std::this_thread::sleep_for(std::chrono::milliseconds(10));
            continue;
        }

        size_t toRead = (bytesAvailable > (int)bufSize) ? bufSize : (size_t)bytesAvailable;
        ssize_t n = ::read(fd, buf.data(), toRead);
        if (n < 0)
            break;
        if (n == 0)
        {
            std::this_thread::sleep_for(std::chrono::milliseconds(10));
            continue;
        }
        response.append(buf.data(), (size_t)n);
        started = true;
        lastRead = now_ms();
    }
    return response;
}

/**
 * @brief USBシリアルポートを自動検出する
 * @param vid ベンダーID（デフォルト: "0403" = FTDI）
 * @param pid プロダクトID（デフォルト: "6015" = FT230X）
 * @return 検出されたポート名（例: "/dev/ttyUSB0"）、見つからない場合は空文字列
 * @note udevadmコマンドを使用してデバイス情報を取得し、VID/PIDが一致するポートを検索
 */
static std::string detect_port_name(const std::string &vid = "0403",
                                    const std::string &pid = "6015")
{
    namespace fs = std::filesystem;

    for (const auto &entry : fs::directory_iterator("/dev"))
    {
        const std::string devPath = entry.path().string();

        // 対象は ttyUSB* または ttyACM*
        if (devPath.find("ttyUSB") == std::string::npos &&
            devPath.find("ttyACM") == std::string::npos)
        {
            continue;
        }

        // udevadm でデバイス情報を取得
        std::string cmd = "udevadm info --query=property --name=" + devPath;
        std::array<char, 512> buffer{};
        std::string result;
        FILE *pipe = popen(cmd.c_str(), "r");
        if (!pipe)
            continue;

        while (fgets(buffer.data(), buffer.size(), pipe))
        {
            result += buffer.data();
        }
        pclose(pipe);

        // VID/PID が一致すればこのポートを返す
        if (result.find("ID_VENDOR_ID=" + vid) != std::string::npos &&
            result.find("ID_MODEL_ID=" + pid) != std::string::npos)
        {
            return devPath;
        }
    }

    // 見つからなければ空文字列
    return "";
}

// ============================================================================
// 公開API実装（Linux版）
// ============================================================================

namespace pamc204
{
/**
 * @brief シリアルポート経由でコマンドを送信し、レスポンスを受信する
 * @param command 送信するコマンド文字列（改行コードは自動付与）
 * @return レスポンス文字列。失敗時または空レスポンス時は空文字列。
 * @note ポートを開く→コマンド送信→レスポンス受信→ポートを閉じる、の一連の処理を行う
 */
std::string send_command(const std::string &command)
{
    std::fprintf(stdout, "COMMAND TO EXECUTE: '%s'\n", command.c_str());

    // ポート名の決定（自動検出）
    std::string portName = detect_port_name();
    std::fprintf(stdout, "PORT NAME: '%s'\n", portName.c_str());
    if (portName.empty())
    {
        std::fprintf(stderr, "No PAMC204 device found\n");
        return std::string();
    }

    // ポートを開く
    int fd = ::open(portName.c_str(), O_RDWR | O_NOCTTY | O_SYNC);
    if (fd < 0)
    {
        std::fprintf(stderr, "open failed on %s: %s\n", portName.c_str(), strerror(errno));
        return std::string();
    }

    // 設定
    if (!configure_port(fd))
    {
        std::fprintf(stderr, "configure_port failed: %s\n", strerror(errno));
        ::close(fd);
        return std::string();
    }

    // 書き込み
    std::string msg = command;
    msg.append("\r\n");
    ssize_t written = ::write(fd, msg.data(), msg.size());
    if (written != (ssize_t)msg.size())
    {
        std::fprintf(stderr, "write failed: %s\n", strerror(errno));
        ::close(fd);
        return std::string();
    }

    // 読み取り
    std::string resp = read_response(fd);
    ::close(fd);

    if (resp.empty())
    {
        std::fprintf(stderr, "read timeout or empty response\n");
        return std::string();
    }

    std::string token = find_error_token(resp);
    if (!token.empty())
    {
        std::string description = get_error_description(token);
        std::string errLine = "ERROR: " + token + " - " + description + "\n";
        std::fwrite(errLine.data(), 1, errLine.size(), stdout);
        std::fflush(stdout);
    }
    else
    {
        output_response(resp);
    }
    return resp;
}

/**
 * @brief 複数のコマンドを1回のポート開閉で順次送信する（効率化版）
 * @param commands 送信するコマンド文字列の配列
 * @return 各コマンドのレスポンス文字列の配列。
 *         失敗時（ポートオープン失敗・書き込み失敗等）は空の vector を返す。
 * @note ポートを1回だけ開き、全コマンドを順次送信してから閉じる。
 *       各コマンド送信後、レスポンスを受信してから次のコマンドを送信。
 *       いずれかのコマンドでエラーが発生した場合は即座に終了。
 */
std::vector<std::string> send_commands_batch(const std::vector<std::string> &commands)
{
    if (commands.empty())
    {
        std::fprintf(stderr, "send_commands_batch: no commands provided\n");
        return {};
    }

    std::fprintf(stdout, "BATCH COMMAND: %zu commands\n", commands.size());

    // ポート名の決定（自動検出）
    std::string portName = detect_port_name();
    std::fprintf(stdout, "PORT NAME: '%s'\n", portName.c_str());
    if (portName.empty())
    {
        std::fprintf(stderr, "No PAMC204 device found\n");
        return {};
    }

    // ポートを開く（1回のみ）
    int fd = ::open(portName.c_str(), O_RDWR | O_NOCTTY | O_SYNC);
    if (fd < 0)
    {
        std::fprintf(stderr, "open failed on %s: %s\n", portName.c_str(), strerror(errno));
        return {};
    }

    // 設定
    if (!configure_port(fd))
    {
        std::fprintf(stderr, "configure_port failed: %s\n", strerror(errno));
        ::close(fd);
        return {};
    }

    std::vector<std::string> responses;
    responses.reserve(commands.size());

    // 各コマンドを順次送信
    for (size_t i = 0; i < commands.size(); i++)
    {
        const std::string &command = commands[i];
        std::fprintf(stdout, "COMMAND[%zu]: '%s'\n", i + 1, command.c_str());

        // 書き込み
        std::string msg = command;
        msg.append("\r\n");
        ssize_t written = ::write(fd, msg.data(), msg.size());
        if (written != (ssize_t)msg.size())
        {
            std::fprintf(stderr, "write failed at command %zu: %s\n", i + 1, strerror(errno));
            ::close(fd);
            return {};
        }

        // 読み取り
        std::string resp = read_response(fd);
        if (resp.empty())
        {
            std::fprintf(stderr, "read timeout or empty response at command %zu\n", i + 1);
            ::close(fd);
            return {};
        }

        // エラーチェック（出力のみ、継続）
        std::string token = find_error_token(resp);
        if (!token.empty())
        {
            std::string description = get_error_description(token);
            std::string errLine = "ERROR at command " + std::to_string(i + 1) + ": " + token +
                                  " - " + description + "\n";
            std::fwrite(errLine.data(), 1, errLine.size(), stdout);
            std::fflush(stdout);
        }
        else
        {
            output_response(resp);
        }

        responses.push_back(resp);

        // 次のコマンド送信前に短い待機時間を設ける
        if (i < commands.size() - 1)
        {
            std::this_thread::sleep_for(std::chrono::milliseconds(50));
        }
    }

    // ポートを閉じる（1回のみ）
    ::close(fd);
    return responses;
}
} // namespace pamc204
