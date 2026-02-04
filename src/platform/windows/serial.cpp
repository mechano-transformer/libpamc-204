#include "pamc204.h"
#include "utils.h"
#include <windows.h>
#include <setupapi.h>
#include <initguid.h>
#include <devguid.h>
#include <string>
#include <vector>
#include <cstdio>

// DLL エントリポイント (Windows専用)
BOOL APIENTRY DllMain(HMODULE, DWORD, LPVOID) { return TRUE; }

// --- 共有のヘルパー（serial_common.h にある実装の宣言） ---
std::string to_upper_ascii(const std::string &s);
std::string find_error_token(const std::string &resp);
std::string get_error_description(const std::string &error_token);

// --- ヘルパー ---
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

static std::wstring normalize_port_name_w(const wchar_t *comName)
{
    if (!comName)
        return L"";
    if (wcsncmp(comName, L"\\\\.\\", 4) == 0)
        return std::wstring(comName);
    return std::wstring(L"\\\\.\\") + comName;
}

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

static HANDLE open_port(const std::wstring &portPath)
{
    return CreateFileW(portPath.c_str(), GENERIC_READ | GENERIC_WRITE, 0, NULL, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);
}

static bool configure_port(HANDLE h)
{
    DCB dcb;
    SecureZeroMemory(&dcb, sizeof(dcb));
    dcb.DCBlength = sizeof(dcb);
    if (!GetCommState(h, &dcb))
        return false;

    dcb.BaudRate = CBR_115200;
    dcb.ByteSize = 8;
    dcb.Parity = NOPARITY;
    dcb.StopBits = ONESTOPBIT;

    dcb.fBinary = TRUE;
    dcb.fParity = FALSE;
    dcb.fOutxCtsFlow = FALSE;
    dcb.fOutxDsrFlow = FALSE;
    dcb.fDtrControl = DTR_CONTROL_DISABLE;
    dcb.fRtsControl = RTS_CONTROL_DISABLE;
    dcb.fOutX = FALSE;
    dcb.fInX = FALSE;

    if (!SetCommState(h, &dcb))
        return false;

    SetupComm(h, 1024, 1024);
    COMMTIMEOUTS timeouts{};
    timeouts.ReadIntervalTimeout = 50;
    timeouts.ReadTotalTimeoutMultiplier = 10;
    timeouts.ReadTotalTimeoutConstant = 50;
    timeouts.WriteTotalTimeoutMultiplier = 50;
    timeouts.WriteTotalTimeoutConstant = 2000;
    if (!SetCommTimeouts(h, &timeouts))
        return false;

    PurgeComm(h, PURGE_RXCLEAR | PURGE_TXCLEAR);
    return true;
}

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
        return false;
    if (written != static_cast<DWORD>(msg.size()))
    {
        SetLastError(ERROR_WRITE_FAULT);
        return false;
    }
    return true;
}

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
    COMSTAT stat{};
    ZeroMemory(&stat, sizeof(stat));

    while ((GetTickCount64() - start) < totalTimeoutMs)
    {
        if (!ClearCommError(h, &errors, &stat))
            break;

        if (stat.cbInQue == 0)
        {
            if (started && (GetTickCount64() - lastRead) >= idleTimeoutMs)
                break;
            Sleep(10);
            continue;
        }

        DWORD toRead = (stat.cbInQue > bufSize) ? bufSize : stat.cbInQue;
        DWORD bytesRead = 0;
        if (!ReadFile(h, buf.data(), toRead, &bytesRead, NULL))
            break;
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

// --- COMポート自動検出 (VID/PID指定) ---
static std::string detect_port_name(const std::string &vid = "0403",
                                    const std::string &pid = "6015")
{
    HDEVINFO hDevInfo = SetupDiGetClassDevs(&GUID_DEVCLASS_PORTS, NULL, NULL, DIGCF_PRESENT);
    if (hDevInfo == INVALID_HANDLE_VALUE)
        return "";

    SP_DEVINFO_DATA devInfoData{};
    devInfoData.cbSize = sizeof(SP_DEVINFO_DATA);

    for (DWORD i = 0; SetupDiEnumDeviceInfo(hDevInfo, i, &devInfoData); i++)
    {
        char hwidBuf[1024];
        if (!SetupDiGetDeviceRegistryPropertyA(hDevInfo, &devInfoData, SPDRP_HARDWAREID,
                                               NULL, (PBYTE)hwidBuf, sizeof(hwidBuf), NULL))
        {
            continue;
        }

        std::string hwid = hwidBuf;
        if (hwid.find("VID_" + vid) == std::string::npos ||
            hwid.find("PID_" + pid) == std::string::npos)
        {
            continue;
        }

        // VID/PID一致 → レジストリから COMポート名を取得
        HKEY hKey = SetupDiOpenDevRegKey(hDevInfo, &devInfoData,
                                         DICS_FLAG_GLOBAL, 0, DIREG_DEV, KEY_READ);
        if (hKey == INVALID_HANDLE_VALUE)
            continue;

        char portName[256];
        DWORD size = sizeof(portName);
        DWORD type = 0;
        if (RegQueryValueExA(hKey, "PortName", NULL, &type,
                             (LPBYTE)portName, &size) == ERROR_SUCCESS)
        {
            RegCloseKey(hKey);
            SetupDiDestroyDeviceInfoList(hDevInfo);
            return std::string(portName); // 例: "COM3"
        }
        RegCloseKey(hKey);
    }

    SetupDiDestroyDeviceInfoList(hDevInfo);
    return "";
}

namespace pamc204
{
    // 共通API（Windows版, Linux版と同じ仕様: cmdのみ受け取る）
    bool send_command(const std::string &command)
    {
        std::fprintf(stdout, "COMMAND TO EXECUTE: '%s'\n", command.c_str());

        // 自動検出
        std::string com = detect_port_name(); // 例: "COM3"
        std::fprintf(stdout, "PORT NAME: '%s'\n", com.c_str());
        if (com.empty())
        {
            std::fprintf(stderr, "No PAMC204 device found\n");
            return false;
        }

        // "\\.\COMx" へ正規化して開く
        std::wstring wcom = to_wstring_utf8(com);
        std::wstring path = normalize_port_name_w(wcom.c_str());
        HandleGuard hg(open_port(path));
        if (!hg.valid())
        {
            std::fprintf(stderr, "open failed on %s\n", com.c_str());
            return false;
        }

        if (!configure_port(hg.h))
        {
            std::fprintf(stderr, "configure_port failed\n");
            return false;
        }

        if (!write_command_to_port(hg.h, command.c_str()))
        {
            std::fprintf(stderr, "write failed\n");
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
                DWORD wrote = 0;
                HANDLE hStdOut = GetStdHandle(STD_OUTPUT_HANDLE);
                if (hStdOut != NULL && hStdOut != INVALID_HANDLE_VALUE)
                {
                    DWORD type = GetFileType(hStdOut);
                    if (type == FILE_TYPE_CHAR)
                    {
                        WriteConsoleA(hStdOut, errLine.c_str(), (DWORD)errLine.size(), &wrote, NULL);
                    }
                    else
                    {
                        WriteFile(hStdOut, errLine.data(), (DWORD)errLine.size(), &wrote, NULL);
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
        else
        {
            std::fprintf(stderr, "read timeout or empty response\n");
        }
        return true;
    }
}

// C API エクスポート用ラッパー（cmdのみ）
extern "C" bool send_command(const char *command)
{
    if (!command)
    {
        std::fprintf(stderr, "send_command: invalid arguments\n");
        return false;
    }
    return pamc204::send_command(std::string(command));
}