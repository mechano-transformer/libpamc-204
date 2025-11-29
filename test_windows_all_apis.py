"""Windows環境で全APIを順に試すスクリプト"""
from ctypes import WinDLL, c_char_p
from ctypes import wintypes

# DLLをロード
lib = WinDLL("./build/Debug/pamc204.dll", use_last_error=True)

# API群のシグネチャ定義
lib.pamc204_send_command.restype = wintypes.BOOL
lib.pamc204_send_command.argtypes = [c_char_p, c_char_p]

lib.pamc204_get_firmware_version.restype = wintypes.BOOL
lib.pamc204_get_firmware_version.argtypes = [c_char_p, wintypes.INT]

lib.pamc204_check_device.restype = wintypes.BOOL
lib.pamc204_check_device.argtypes = [c_char_p, wintypes.INT]

lib.pamc204_set_address.restype = wintypes.BOOL
lib.pamc204_set_address.argtypes = [c_char_p, wintypes.INT]

lib.pamc204_set_voltage.restype = wintypes.BOOL
lib.pamc204_set_voltage.argtypes = [c_char_p, wintypes.INT, wintypes.INT]

lib.pamc204_rotate_positive.restype = wintypes.BOOL
lib.pamc204_rotate_positive.argtypes = [c_char_p, wintypes.INT, wintypes.INT, wintypes.INT, c_char_p]

lib.pamc204_rotate_positive_ex.restype = wintypes.BOOL
lib.pamc204_rotate_positive_ex.argtypes = [c_char_p, wintypes.INT, wintypes.INT, wintypes.INT, c_char_p]

lib.pamc204_rotate_negative.restype = wintypes.BOOL
lib.pamc204_rotate_negative.argtypes = [c_char_p, wintypes.INT, wintypes.INT, wintypes.INT, c_char_p]

lib.pamc204_rotate_negative_ex.restype = wintypes.BOOL
lib.pamc204_rotate_negative_ex.argtypes = [c_char_p, wintypes.INT, wintypes.INT, wintypes.INT, c_char_p]

lib.pamc204_stop.restype = wintypes.BOOL
lib.pamc204_stop.argtypes = [c_char_p, wintypes.INT]

# テスト対象ポートとアドレス
port = b"COM3"
address = 1  # E01

# 呼び出し例をリスト化（send_command を最初に追加）
tests = [
    ("send_command_E01INF", lambda: lib.pamc204_send_command(port, b"E01INF")),
    ("send_command_E01", lambda: lib.pamc204_send_command(port, b"E01")),
    ("get_firmware_version", lambda: lib.pamc204_get_firmware_version(port, address)),
    ("check_device", lambda: lib.pamc204_check_device(port, address)),
    ("set_address", lambda: lib.pamc204_set_address(port, 1)),  # E01
    ("set_voltage_150V", lambda: lib.pamc204_set_voltage(port, address, 4095)),
    ("set_voltage_110V", lambda: lib.pamc204_set_voltage(port, address, 3000)),
    ("set_voltage_70V", lambda: lib.pamc204_set_voltage(port, address, 1900)),
    ("rotate_positive_1500Hz_1500pulses", lambda: lib.pamc204_rotate_positive(port, address, 1500, 1500, b"A")),
    ("rotate_positive_ex_1500Hz_100000pulses", lambda: lib.pamc204_rotate_positive_ex(port, address, 1500, 100000, b"A")),
    ("rotate_positive_continuous", lambda: lib.pamc204_rotate_positive(port, address, 1500, 0, b"A")),
    ("rotate_negative_1500Hz_1500pulses", lambda: lib.pamc204_rotate_negative(port, address, 1500, 1500, b"B")),
    ("rotate_negative_ex_1500Hz_100000pulses", lambda: lib.pamc204_rotate_negative_ex(port, address, 1500, 100000, b"B")),
    ("rotate_negative_continuous", lambda: lib.pamc204_rotate_negative(port, address, 1500, 0, b"C")),
    ("stop", lambda: lib.pamc204_stop(port, address)),
]

# 順に試す
for name, func in tests:
    print(f"\n- Testing {name}...")
    ok = func()
    if ok:
        print(f"  {name} succeeded")
    else:
        from ctypes import get_last_error
        err_code = get_last_error()
        print(f"  {name} failed (WinError={err_code})")