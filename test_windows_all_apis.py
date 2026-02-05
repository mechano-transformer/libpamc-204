"""Windows環境で全APIを順に試すスクリプト"""
from ctypes import CDLL, c_char, c_char_p
from ctypes import wintypes
import time

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
lib.pamc204_rotate_positive.argtypes = [wintypes.INT, wintypes.INT, wintypes.INT, c_char]

lib.pamc204_rotate_positive_ex.restype = wintypes.BOOL
lib.pamc204_rotate_positive_ex.argtypes = [wintypes.INT, wintypes.INT, wintypes.INT, c_char]

lib.pamc204_rotate_negative.restype = wintypes.BOOL
lib.pamc204_rotate_negative.argtypes = [wintypes.INT, wintypes.INT, wintypes.INT, c_char]

lib.pamc204_rotate_negative_ex.restype = wintypes.BOOL
lib.pamc204_rotate_negative_ex.argtypes = [wintypes.INT, wintypes.INT, wintypes.INT, c_char]

lib.pamc204_stop.restype = wintypes.BOOL
lib.pamc204_stop.argtypes = [wintypes.INT]

lib.pamc204_set_acceleration.restype = wintypes.BOOL
lib.pamc204_set_acceleration.argtypes = [wintypes.INT, wintypes.INT, wintypes.INT]

lib.pamc204_query_acceleration.restype = wintypes.BOOL
lib.pamc204_query_acceleration.argtypes = [wintypes.INT, wintypes.INT]

lib.pamc204_set_velocity.restype = wintypes.BOOL
lib.pamc204_set_velocity.argtypes = [wintypes.INT, wintypes.INT, wintypes.INT]

lib.pamc204_move_absolute.restype = wintypes.BOOL
lib.pamc204_move_absolute.argtypes = [wintypes.INT, wintypes.INT, wintypes.INT]

lib.pamc204_move_relative.restype = wintypes.BOOL
lib.pamc204_move_relative.argtypes = [wintypes.INT, wintypes.INT, wintypes.INT]

lib.pamc204_query_actual_position.restype = wintypes.BOOL
lib.pamc204_query_actual_position.argtypes = [wintypes.INT, wintypes.INT]

lib.pamc204_move_infinite.restype = wintypes.BOOL
lib.pamc204_move_infinite.argtypes = [wintypes.INT, wintypes.INT, c_char]

lib.pamc204_stop_motion.restype = wintypes.BOOL
lib.pamc204_stop_motion.argtypes = [wintypes.INT, wintypes.INT]

lib.pamc204_abort_motion.restype = wintypes.BOOL
lib.pamc204_abort_motion.argtypes = [wintypes.INT]

# 4軸同時操作API
lib.pamc204_move_relative_all_channels.restype = wintypes.BOOL
lib.pamc204_move_relative_all_channels.argtypes = [wintypes.INT, wintypes.INT]

lib.pamc204_query_actual_position_all_channels.restype = wintypes.BOOL
lib.pamc204_query_actual_position_all_channels.argtypes = [wintypes.INT, wintypes.INT * 4]

lib.pamc204_query_motion_status_all_channels.restype = wintypes.BOOL
lib.pamc204_query_motion_status_all_channels.argtypes = [wintypes.INT, wintypes.INT * 4]

lib.pamc204_move_infinite_all_channels.restype = wintypes.BOOL
lib.pamc204_move_infinite_all_channels.argtypes = [wintypes.INT, c_char]

lib.pamc204_stop_motion_all_channels.restype = wintypes.BOOL
lib.pamc204_stop_motion_all_channels.argtypes = [wintypes.INT]

# テスト対象アドレス（E01）
address = 1

# 4軸同時操作API用のヘルパー関数
def test_query_actual_position_all_channels():
    """全チャンネルの位置を取得して表示"""
    positions = (wintypes.INT * 4)()
    result = lib.pamc204_query_actual_position_all_channels(address, positions)
    print(f"  Positions: CH1={positions[0]}, CH2={positions[1]}, CH3={positions[2]}, CH4={positions[3]}")
    return result

def test_query_motion_status_all_channels():
    """全チャンネルのモーション状態を取得して表示"""
    statuses = (wintypes.INT * 4)()
    result = lib.pamc204_query_motion_status_all_channels(address, statuses)
    print(f"  Statuses:")
    print(f"    CH1: {'Stopped' if statuses[0] else 'Moving'}")
    print(f"    CH2: {'Stopped' if statuses[1] else 'Moving'}")
    print(f"    CH3: {'Stopped' if statuses[2] else 'Moving'}")
    print(f"    CH4: {'Stopped' if statuses[3] else 'Moving'}")
    return result

# 呼び出し例をリスト化（BUSYエラーを避けるため、モーション完了を待つ）
tests = [
    ("send_command_E01INF", lambda: lib.pamc204_send_command(b"E01INF"), 0),
    ("send_command_E01", lambda: lib.pamc204_send_command(b"E01"), 0),
    ("get_firmware_version", lambda: lib.pamc204_get_firmware_version(address), 0),
    ("check_device", lambda: lib.pamc204_check_device(address), 0),
    ("set_address", lambda: lib.pamc204_set_address(1), 0),  # E01
    ("set_voltage_150V", lambda: lib.pamc204_set_voltage(address, 4095), 0),
    ("set_voltage_110V", lambda: lib.pamc204_set_voltage(address, 3000), 0),
    ("set_voltage_70V", lambda: lib.pamc204_set_voltage(address, 1900), 0),
    
    # パルス駆動テスト（短いパルス数で完了を待つ）
    ("rotate_positive_100pulses", lambda: lib.pamc204_rotate_positive(address, 1500, 100, b"A"), 0.5),
    ("rotate_negative_100pulses", lambda: lib.pamc204_rotate_negative(address, 1500, 100, b"A"), 0.5),
    
    # 加速度・速度設定テスト（NPコマンド）
    ("set_acceleration_10000", lambda: lib.pamc204_set_acceleration(address, 1, 10000), 0),
    ("query_acceleration", lambda: lib.pamc204_query_acceleration(address, 1), 0),
    ("set_velocity_1500", lambda: lib.pamc204_set_velocity(address, 1, 1500), 0),
    
    # 位置制御テスト（NPコマンド、加速度対応）
    ("move_absolute_1000", lambda: lib.pamc204_move_absolute(address, 1, 1000), 1.0),
    ("query_actual_position", lambda: lib.pamc204_query_actual_position(address, 1), 0),
    ("move_relative_500", lambda: lib.pamc204_move_relative(address, 1, 500), 1.0),
    ("query_actual_position_2", lambda: lib.pamc204_query_actual_position(address, 1), 0),
    
    # 無限移動と停止テスト（加速度対応）
    ("move_infinite_positive", lambda: lib.pamc204_move_infinite(address, 1, b"+"), 0.5),
    ("stop_motion", lambda: lib.pamc204_stop_motion(address, 1), 0.5),
    
    # 最終確認
    ("query_actual_position_final", lambda: lib.pamc204_query_actual_position(address, 1), 0),
    
    # 4軸同時操作APIテスト
    ("move_relative_all_channels", lambda: lib.pamc204_move_relative_all_channels(address, 500), 2.0),
    ("query_actual_position_all_channels", test_query_actual_position_all_channels, 0),
    ("query_motion_status_all_channels", test_query_motion_status_all_channels, 0),
    
    # 4軸同時無限移動と停止テスト
    ("move_infinite_all_channels", lambda: lib.pamc204_move_infinite_all_channels(address, b"+"), 0.5),
    ("stop_motion_all_channels", lambda: lib.pamc204_stop_motion_all_channels(address), 0.5),
    ("query_motion_status_all_channels_after_stop", test_query_motion_status_all_channels, 0),
]

# 順に試す
for name, func, wait_time in tests:
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
    
    # 次のコマンドの前に待機（モーション完了やコマンド処理を待つ）
    if wait_time > 0:
        print(f"  Waiting {wait_time}s for motion to complete...")
        time.sleep(wait_time)