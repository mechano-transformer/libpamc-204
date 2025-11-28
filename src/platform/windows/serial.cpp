#include "pamc204.h"
#include <windows.h>
#include <string>
#include <vector>
#include <algorithm>
#include <cctype>
#include <cstdio>
#include "pamc204_internal.h"

// DLL エントリポイント (Windows専用)
BOOL APIENTRY DllMain(HMODULE hModule, DWORD ul_reason_for_call, LPVOID lpReserved)
{
    switch (ul_reason_for_call)
    {
    case DLL_PROCESS_ATTACH:
    case DLL_THREAD_ATTACH:
    case DLL_THREAD_DETACH:
    case DLL_PROCESS_DETACH:
        break;
    }
    return TRUE;
}

// --- 共有のヘルパー（serial_common.h にある実装の宣言） ---
std::string to_upper_ascii(const std::string &s);
std::string find_error_token(const std::string &resp);
std::string get_error_description(const std::string &error_token);

// --- ヘルパー ---
// RAII: HANDLE を自動で CloseHandle する
struct HandleGuard
{
    HANDLE h;
    explicit HandleGuard(HANDLE handle = INVALID_HANDLE_VALUE) : h(handle) {}
    ~HandleGuard()
    {
        if (h != INVALID_HANDLE_VALUE && h != NULL)
            CloseHandle(h);
    }
    operator HANDLE() const { return h; }
    bool valid() const { return h != INVALID_HANDLE_VALUE && h != NULL; }
};

// ポート名正規化 ("COM3" -> "\\.\COM3")
static std::wstring normalize_port_name_w(const wchar_t *comName)
{
    if (!comName)
        return L"";
    if (wcsncmp(comName, L"\\\\.\\", 4) == 0)
    {
        return std::wstring(comName);
    }
    std::wstring p = L"\\\\.\\";
    p += comName;
    return p;
}

// 文字列からワイド文字列へ（UTF-8 想定）
static std::wstring to_wstring_utf8(const std::string &s)
{
    if (s.empty())
        return std::wstring();
    int size = MultiByteToWideChar(CP_UTF8, 0, s.c_str(), (int)s.size(), nullptr, 0);
    std::wstring w;
    w.resize(size);
    MultiByteToWideChar(CP_UTF8, 0, s.c_str(), (int)s.size(), &w[0], size);
    return w;
}

// シリアルポートを開く
static HANDLE open_port(const std::wstring &portPath)
{
    return CreateFileW(portPath.c_str(),
                       GENERIC_READ | GENERIC_WRITE,
                       0, // 共有なし
                       NULL,
                       OPEN_EXISTING,
                       FILE_ATTRIBUTE_NORMAL,
                       NULL);
}

// DCB 等の設定（115200 8N1, フロー制御なし）
static bool configure_port(HANDLE h)
{
    DCB dcb;
    SecureZeroMemory(&dcb, sizeof(dcb));
    dcb.DCBlength = sizeof(dcb);
    if (!GetCommState(h, &dcb))
    {
        return false;
    }

    dcb.BaudRate = CBR_115200;
    dcb.ByteSize = 8;
    dcb.Parity = NOPARITY;
    dcb.StopBits = ONESTOPBIT;

    // フロー制御なし
    dcb.fBinary = TRUE;
    dcb.fParity = FALSE;
    dcb.fOutxCtsFlow = FALSE;
    dcb.fOutxDsrFlow = FALSE;
    dcb.fDtrControl = DTR_CONTROL_DISABLE;
    dcb.fRtsControl = RTS_CONTROL_DISABLE;
    dcb.fOutX = FALSE;
    dcb.fInX = FALSE;

    if (!SetCommState(h, &dcb))
    {
        return false;
    }

    // バッファ/タイムアウト
    SetupComm(h, 1024, 1024);
    COMMTIMEOUTS timeouts;
    timeouts.ReadIntervalTimeout = 50;
    timeouts.ReadTotalTimeoutMultiplier = 10;
    timeouts.ReadTotalTimeoutConstant = 50;
    timeouts.WriteTotalTimeoutMultiplier = 50;
    timeouts.WriteTotalTimeoutConstant = 2000;
    if (!SetCommTimeouts(h, &timeouts))
    {
        return false;
    }

    // 送受信バッファをクリア
    PurgeComm(h, PURGE_RXCLEAR | PURGE_TXCLEAR);
    return true;
}

// コマンドを書き込む（CR+LF を付加）
static bool write_command_to_port(HANDLE h, const char *command)
{
    if (!h || h == INVALID_HANDLE_VALUE || !command)
    {
        SetLastError(ERROR_INVALID_PARAMETER);
        return false;
    }
    std::string msg = command;
    msg.append("\r\n");

    DWORD written = 0;
    if (!WriteFile(h, msg.data(), static_cast<DWORD>(msg.size()), &written, NULL))
    {
        return false;
    }
    if (written != static_cast<DWORD>(msg.size()))
    {
        SetLastError(ERROR_WRITE_FAULT);
        return false;
    }
    return true;
}

// レスポンス読み取り（同期、ポーリング）
static std::string read_response_from_port(HANDLE h, DWORD totalTimeoutMs = 2000, DWORD idleTimeoutMs = 200, DWORD bufSize = 1024)
{
    std::string response;
    if (!h || h == INVALID_HANDLE_VALUE)
        return response;

    std::vector<char> buf(bufSize);
    ULONGLONG start = GetTickCount64();
    ULONGLONG lastRead = start;
    bool started = false;

    DWORD errors = 0;
    COMSTAT stat;
    ZeroMemory(&stat, sizeof(stat));

    while ((GetTickCount64() - start) < totalTimeoutMs)
    {
        if (!ClearCommError(h, &errors, &stat))
            break;

        if (stat.cbInQue == 0)
        {
            if (started)
            {
                if ((GetTickCount64() - lastRead) >= idleTimeoutMs)
                    break;
            }
            Sleep(10);
            continue;
        }

        DWORD toRead = (stat.cbInQue > bufSize) ? bufSize : stat.cbInQue;
        DWORD bytesRead = 0;
        if (!ReadFile(h, buf.data(), toRead, &bytesRead, NULL))
        {
            break;
        }
        if (bytesRead == 0)
        {
            Sleep(10);
            continue;
        }
        response.append(buf.data(), bytesRead);
        started = true;
        lastRead = GetTickCount64();
    }

    return response;
}

// 受信データを一度だけ出力（エラー検出時の特別扱い含む）
static void output_response_once(const std::string &resp)
{
    if (resp.empty())
        return;

    std::string token = find_error_token(resp);
    HANDLE hStdOut = GetStdHandle(STD_OUTPUT_HANDLE);

    auto write_line = [&](const std::string &s)
    {
        if (hStdOut != NULL && hStdOut != INVALID_HANDLE_VALUE)
        {
            DWORD type = GetFileType(hStdOut);
            DWORD wrote = 0;
            if (type == FILE_TYPE_CHAR)
            {
                WriteConsoleA(hStdOut, s.c_str(), static_cast<DWORD>(s.size()), &wrote, NULL);
            }
            else
            {
                WriteFile(hStdOut, s.data(), static_cast<DWORD>(s.size()), &wrote, NULL);
            }
        }
        else
        {
            OutputDebugStringA(s.c_str());
        }
    };

    if (!token.empty())
    {
        std::string description = get_error_description(token);
        std::string errLine = "ERROR: " + token + " - " + description + "\r\n";
        write_line(errLine);
        OutputDebugStringA(resp.c_str());
        return;
    }

    std::string outMsg = resp;
    if (resp.size() < 2 || (resp.back() != '\n' && resp.back() != '\r'))
        outMsg += "\r\n";
    write_line(outMsg);
}

namespace pamc204
{
    // 共通API（Windows版）
    bool send_command(const std::string &portName, const std::string &command)
    {
        // Windows ではポート名はワイド文字経由で正規化
        std::wstring wport = to_wstring_utf8(portName);
        std::wstring portPath = normalize_port_name_w(wport.c_str());

        HandleGuard hg(open_port(portPath));
        if (!hg.valid())
        {
            return false;
        }

        if (!configure_port(hg.h))
        {
            return false;
        }

        if (!write_command_to_port(hg.h, command.c_str()))
        {
            return false;
        }

        std::string resp = read_response_from_port(hg.h);
        if (!resp.empty())
        {
            std::string token = find_error_token(resp);
            if (!token.empty())
            {
                std::string description = get_error_description(token);
                std::string errLine = "ERROR: " + token + " - " + description + "\r\n";

                HANDLE hStdOut = GetStdHandle(STD_OUTPUT_HANDLE);
                DWORD wrote = 0;
                if (hStdOut != NULL && hStdOut != INVALID_HANDLE_VALUE)
                {
                    DWORD type = GetFileType(hStdOut);
                    if (type == FILE_TYPE_CHAR)
                    {
                        WriteConsoleA(hStdOut, errLine.c_str(), static_cast<DWORD>(errLine.size()), &wrote, NULL);
                    }
                    else
                    {
                        WriteFile(hStdOut, errLine.data(), static_cast<DWORD>(errLine.size()), &wrote, NULL);
                    }
                }
                else
                {
                    OutputDebugStringA(errLine.c_str());
                }
                OutputDebugStringA(resp.c_str());
                SetLastError(ERROR_INVALID_DATA);
                return false;
            }
            output_response_once(resp);
        }
        return true;
    }
}