"""Windows環境で全APIを順に試すスクリプト"""
from ctypes import CDLL, c_char_p
from ctypes import wintypes

# DLLをロード（cdecl 前提。stdcall の場合は WinDLL に切り替え）
lib = CDLL("./build/Debug/pamc204.dll")

# API群のシグネチャ定義（port 引数をすべて削除）
lib.pamc204_send_command.restype = wintypes.BOOL
lib.pamc204_send_command.argtypes = [c_char_p]

lib.pamc204_get_firmware_version.restype = wintypes.BOOL
lib.pamc204_get_firmware_version.argtypes = [wintypes.INT]

lib.pamc204_check_device.restype = wintypes.BOOL
lib.pamc204_check_device.argtypes = [wintypes.INT]

lib.pamc204_set_address.restype = wintypes.BOOL
lib.pamc204_set_address.argtypes = [wintypes.INT]

lib.pamc204_set_voltage.restype = wintypes.BOOL
lib.pamc204_set_voltage.argtypes = [wintypes.INT, wintypes.INT]

lib.pamc204_rotate_positive.restype = wintypes.BOOL
lib.pamc204_rotate_positive.argtypes = [wintypes.INT, wintypes.INT, wintypes.INT, c_char_p]

lib.pamc204_rotate_positive_ex.restype = wintypes.BOOL
lib.pamc204_rotate_positive_ex.argtypes = [wintypes.INT, wintypes.INT, wintypes.INT, c_char_p]

lib.pamc204_rotate_negative.restype = wintypes.BOOL
lib.pamc204_rotate_negative.argtypes = [wintypes.INT, wintypes.INT, wintypes.INT, c_char_p]

lib.pamc204_rotate_negative_ex.restype = wintypes.BOOL
lib.pamc204_rotate_negative_ex.argtypes = [wintypes.INT, wintypes.INT, wintypes.INT, c_char_p]

lib.pamc204_stop.restype = wintypes.BOOL
lib.pamc204_stop.argtypes = [wintypes.INT]

# テスト対象アドレス（E01）
address = 1

# 呼び出し例をリスト化（send_command を最初に追加）
tests = [
    ("send_command_E01INF", lambda: lib.pamc204_send_command(b"E01INF")),
    ("send_command_E01", lambda: lib.pamc204_send_command(b"E01")),
    ("get_firmware_version", lambda: lib.pamc204_get_firmware_version(address)),
    ("check_device", lambda: lib.pamc204_check_device(address)),
    ("set_address", lambda: lib.pamc204_set_address(1)),  # E01
    ("set_voltage_150V", lambda: lib.pamc204_set_voltage(address, 4095)),
    ("set_voltage_110V", lambda: lib.pamc204_set_voltage(address, 3000)),
    ("set_voltage_70V", lambda: lib.pamc204_set_voltage(address, 1900)),
    ("rotate_positive_1500Hz_1500pulses", lambda: lib.pamc204_rotate_positive(address, 1500, 1500, b"A")),
    ("rotate_positive_ex_1500Hz_100000pulses", lambda: lib.pamc204_rotate_positive_ex(address, 1500, 100000, b"A")),
    ("rotate_positive_continuous", lambda: lib.pamc204_rotate_positive(address, 1500, 0, b"A")),
    ("rotate_negative_1500Hz_1500pulses", lambda: lib.pamc204_rotate_negative(address, 1500, 1500, b"B")),
    ("rotate_negative_ex_1500Hz_100000pulses", lambda: lib.pamc204_rotate_negative_ex(address, 1500, 100000, b"B")),
    ("rotate_negative_continuous", lambda: lib.pamc204_rotate_negative(address, 1500, 0, b"C")),
    ("stop", lambda: lib.pamc204_stop(address)),
]

# 順に試す
for name, func in tests:
    print(f"\n- Testing {name}...")
    ok = func()
    if ok:
        print(f"  {name} succeeded")
    else:
        # cdecl の CDLL では get_last_error の代わりに WinError は拾いづらいです
        # DLL側で明示的に SetLastError を使っていれば下記でも参照可能
        from ctypes import get_last_error
        err_code = get_last_error()
        print(f"  {name} failed (WinError={err_code})")