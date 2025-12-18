"""Linux環境で全APIを順に試すスクリプト"""
from ctypes import CDLL, c_char, c_bool, c_int

# 共有ライブラリをロード
lib = CDLL("./build/libpamc204.so")

# API群のシグネチャ定義
lib.pamc204_send_command.restype = c_bool
lib.pamc204_send_command.argtype = c_char

lib.pamc204_get_firmware_version.restype = c_bool
lib.pamc204_get_firmware_version.argtype = c_int

lib.pamc204_check_device.restype = c_bool
lib.pamc204_check_device.argtype = c_int

lib.pamc204_set_address.restype = c_bool
lib.pamc204_set_address.argtype = c_int

lib.pamc204_set_voltage.restype = c_bool
lib.pamc204_set_voltage.argtypes = [c_int, c_int]

lib.pamc204_rotate_positive.restype = c_bool
lib.pamc204_rotate_positive.argtypes = [c_int, c_int, c_int, c_char]

lib.pamc204_rotate_positive_ex.restype = c_bool
lib.pamc204_rotate_positive_ex.argtypes = [c_int, c_int, c_int, c_char]

lib.pamc204_rotate_negative.restype = c_bool
lib.pamc204_rotate_negative.argtypes = [c_int, c_int, c_int, c_char]

lib.pamc204_rotate_negative_ex.restype = c_bool
lib.pamc204_rotate_negative_ex.argtypes = [c_int, c_int, c_int, c_char]

lib.pamc204_stop.restype = c_bool
lib.pamc204_stop.argtype = c_int

lib.pamc204_set_acceleration.restype = c_bool
lib.pamc204_set_acceleration.argtypes = [c_int, c_int, c_int]

lib.pamc204_query_acceleration.restype = c_bool
lib.pamc204_query_acceleration.argtypes = [c_int, c_int]

lib.pamc204_set_velocity.restype = c_bool
lib.pamc204_set_velocity.argtypes = [c_int, c_int, c_int]

lib.pamc204_move_absolute.restype = c_bool
lib.pamc204_move_absolute.argtypes = [c_int, c_int, c_int]

lib.pamc204_move_relative.restype = c_bool
lib.pamc204_move_relative.argtypes = [c_int, c_int, c_int]

lib.pamc204_query_actual_position.restype = c_bool
lib.pamc204_query_actual_position.argtypes = [c_int, c_int]

lib.pamc204_move_infinite.restype = c_bool
lib.pamc204_move_infinite.argtypes = [c_int, c_int, c_char]

lib.pamc204_stop_motion.restype = c_bool
lib.pamc204_stop_motion.argtypes = [c_int, c_int]

lib.pamc204_abort_motion.restype = c_bool
lib.pamc204_abort_motion.argtype = c_int

# テスト対象アドレス
address = 1  # E01

# 呼び出し例をリスト化（send_command を最初に追加）
tests = [
    ("send_command_E01INF", lambda: lib.pamc204_send_command(b"E01INF")),
    ("send_command_E01", lambda: lib.pamc204_send_command(b"E01")),
    ("set_address", lambda: lib.pamc204_set_address(1)),  # E01
    ("set_voltage_150V", lambda: lib.pamc204_set_voltage(address, 4095)),
    ("set_voltage_110V", lambda: lib.pamc204_set_voltage(address, 3000)),
    ("set_voltage_70V", lambda: lib.pamc204_set_voltage(address, 1900)),
    ("rotate_positive_1500Hz_1500pulses", lambda: lib.pamc204_rotate_positive(address, 1500, 1500, b"A")),
    ("rotate_positive_ex_1500Hz_100000pulses", lambda: lib.pamc204_rotate_positive_ex(address, 1500, 100000, b"A")),
    ("rotate_positive_continuous", lambda: lib.pamc204_rotate_positive(address, 1500, 0, b"A")),
    ("rotate_negative_1500Hz_1500pulses", lambda: lib.pamc204_rotate_negative(address, 1500, 1500, b"A")),
    ("rotate_negative_ex_1500Hz_100000pulses", lambda: lib.pamc204_rotate_negative_ex(address, 1500, 100000, b"A")),
    ("rotate_negative_continuous", lambda: lib.pamc204_rotate_negative(address, 1500, 0, b"A")),
    ("stop", lambda: lib.pamc204_stop(address)),
    ("set_acceleration_10000", lambda: lib.pamc204_set_acceleration(address, 1, 10000)),
    ("query_acceleration", lambda: lib.pamc204_query_acceleration(address, 1)),
    ("set_velocity_1500", lambda: lib.pamc204_set_velocity(address, 1, 1500)),
    ("move_absolute_10000", lambda: lib.pamc204_move_absolute(address, 1, 10000)),
    ("move_relative_5000", lambda: lib.pamc204_move_relative(address, 1, 5000)),
    ("query_actual_position", lambda: lib.pamc204_query_actual_position(address, 1)),
    ("move_infinite_positive", lambda: lib.pamc204_move_infinite(address, 1, b"+")),
    ("stop_motion", lambda: lib.pamc204_stop_motion(address, 1)),
    ("abort_motion", lambda: lib.pamc204_abort_motion(address)),
]

# 順に試す
for name, func in tests:
    print(f"\n- Testing {name}...")
    ok = func()
    if ok:
        print(f"  {name} succeeded")
    else:
        print(f"  {name} failed")