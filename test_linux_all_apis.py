"""Linux環境で全APIを順に試すスクリプト"""
from ctypes import CDLL, c_char_p, c_bool, c_int

# 共有ライブラリをロード
lib = CDLL("./build/libpamc204.so")

# API群のシグネチャ定義
lib.pamc204_send_command.restype = c_bool
lib.pamc204_send_command.argtypes = [c_char_p, c_char_p]

lib.pamc204_get_firmware_version.restype = c_bool
lib.pamc204_get_firmware_version.argtypes = [c_char_p, c_int]

lib.pamc204_check_device.restype = c_bool
lib.pamc204_check_device.argtypes = [c_char_p, c_int]

lib.pamc204_set_address.restype = c_bool
lib.pamc204_set_address.argtypes = [c_char_p, c_int]

lib.pamc204_set_voltage.restype = c_bool
lib.pamc204_set_voltage.argtypes = [c_char_p, c_int, c_int]

lib.pamc204_rotate_positive.restype = c_bool
lib.pamc204_rotate_positive.argtypes = [c_char_p, c_int, c_int, c_int, c_char_p]

lib.pamc204_rotate_positive_ex.restype = c_bool
lib.pamc204_rotate_positive_ex.argtypes = [c_char_p, c_int, c_int, c_int, c_char_p]

lib.pamc204_rotate_negative.restype = c_bool
lib.pamc204_rotate_negative.argtypes = [c_char_p, c_int, c_int, c_int, c_char_p]

lib.pamc204_rotate_negative_ex.restype = c_bool
lib.pamc204_rotate_negative_ex.argtypes = [c_char_p, c_int, c_int, c_int, c_char_p]

lib.pamc204_stop.restype = c_bool
lib.pamc204_stop.argtypes = [c_char_p, c_int]

# テスト対象ポートとアドレス
port = b"/dev/ttyUSB0"
address = 1  # E01

# 呼び出し例をリスト化（send_command を最初に追加）
tests = [
    ("send_command_E01INF", lambda: lib.pamc204_send_command(port, b"E01INF")),
    ("send_command_E01", lambda: lib.pamc204_send_command(port, b"E01")),
    ("set_address", lambda: lib.pamc204_set_address(port, 2)),  # E01 → E02
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
        print(f"  {name} failed")