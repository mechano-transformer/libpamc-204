from ctypes import WinDLL, c_char_p, get_last_error, create_unicode_buffer
from ctypes import wintypes, windll

def format_error(err_code):
    buf = create_unicode_buffer(256)
    windll.kernel32.FormatMessageW(
        0x00001000,
        None,
        err_code,
        0,
        buf,
        len(buf),
        None
    )
    return buf.value.strip()

lib = WinDLL("./build/Debug/libpamc204.dll", use_last_error=True)
send_command = lib.send_command
send_command.restype = wintypes.BOOL
send_command.argtypes = [wintypes.LPCWSTR, c_char_p]

com_port = "COM3"
cmd = "E01INF"

ok = send_command(com_port, cmd.encode("ascii"))
if not ok:
    err_code = get_last_error()
    print(f"send_command failed: {err_code} - {format_error(err_code)}")
else:
    print("send succeeded")