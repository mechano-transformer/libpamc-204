from ctypes import WinDLL, c_char_p
from ctypes import wintypes

lib = WinDLL("./pamc204.dll", use_last_error=True)

# C APIの関数を取得
send_command = lib.pamc204_send_command
send_command.restype = wintypes.BOOL
send_command.argtypes = [c_char_p, c_char_p]

# COMポートとコマンド
com_port = b"COM3"
cmd = b"E01INF"

ok = send_command(com_port, cmd)
if not ok:
    from ctypes import get_last_error
    err_code = get_last_error()
    print(f"send_command failed: {err_code}")
else:
    print("send succeeded")