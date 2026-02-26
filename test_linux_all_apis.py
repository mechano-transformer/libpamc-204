"""Linux環境で全APIを順に試すスクリプト"""
from ctypes import CDLL, c_char, c_char_p, c_bool, c_int
import time

# 共有ライブラリをロード
lib = CDLL("./build/libpamc204.so")

# ── 低レベルAPI ──────────────────────────────────────────────────────────────
# pamc204_send_command(command, out_response, out_size) -> bool
lib.pamc204_send_command.restype  = c_bool
lib.pamc204_send_command.argtypes = [c_char_p, c_char_p, c_int]

# ── 高レベルAPI（設定系: bool を返す） ────────────────────────────────────────
lib.pamc204_get_firmware_version.restype  = c_bool
lib.pamc204_get_firmware_version.argtypes = [c_int]

lib.pamc204_check_device.restype  = c_bool
lib.pamc204_check_device.argtypes = [c_int]

lib.pamc204_set_address.restype  = c_bool
lib.pamc204_set_address.argtypes = [c_int]

lib.pamc204_set_voltage.restype  = c_bool
lib.pamc204_set_voltage.argtypes = [c_int, c_int]

lib.pamc204_rotate_positive.restype  = c_bool
lib.pamc204_rotate_positive.argtypes = [c_int, c_int, c_int, c_char]

lib.pamc204_rotate_positive_ex.restype  = c_bool
lib.pamc204_rotate_positive_ex.argtypes = [c_int, c_int, c_int, c_char]

lib.pamc204_rotate_negative.restype  = c_bool
lib.pamc204_rotate_negative.argtypes = [c_int, c_int, c_int, c_char]

lib.pamc204_rotate_negative_ex.restype  = c_bool
lib.pamc204_rotate_negative_ex.argtypes = [c_int, c_int, c_int, c_char]

lib.pamc204_stop.restype  = c_bool
lib.pamc204_stop.argtypes = [c_int]

lib.pamc204_abort_motion.restype  = c_bool
lib.pamc204_abort_motion.argtypes = [c_int]

lib.pamc204_set_acceleration.restype  = c_bool
lib.pamc204_set_acceleration.argtypes = [c_int, c_int, c_int]

lib.pamc204_set_velocity.restype  = c_bool
lib.pamc204_set_velocity.argtypes = [c_int, c_int, c_int]

lib.pamc204_set_home_position.restype  = c_bool
lib.pamc204_set_home_position.argtypes = [c_int, c_int, c_int]

lib.pamc204_move_absolute.restype  = c_bool
lib.pamc204_move_absolute.argtypes = [c_int, c_int, c_int]

lib.pamc204_move_relative.restype  = c_bool
lib.pamc204_move_relative.argtypes = [c_int, c_int, c_int]

lib.pamc204_move_infinite.restype  = c_bool
lib.pamc204_move_infinite.argtypes = [c_int, c_int, c_char]

lib.pamc204_stop_motion.restype  = c_bool
lib.pamc204_stop_motion.argtypes = [c_int, c_int]

# ── 高レベルAPI（問い合わせ系: 値を int/char で返す） ─────────────────────────
# 失敗時: query_acceleration/velocity → -1、その他 → INT_MIN (-2147483648)
lib.pamc204_query_acceleration.restype  = c_int
lib.pamc204_query_acceleration.argtypes = [c_int, c_int]

lib.pamc204_query_velocity.restype  = c_int
lib.pamc204_query_velocity.argtypes = [c_int, c_int]

lib.pamc204_query_home_position.restype  = c_int
lib.pamc204_query_home_position.argtypes = [c_int, c_int]

lib.pamc204_query_absolute_position.restype  = c_int
lib.pamc204_query_absolute_position.argtypes = [c_int, c_int]

lib.pamc204_query_relative_position.restype  = c_int
lib.pamc204_query_relative_position.argtypes = [c_int, c_int]

lib.pamc204_query_actual_position.restype  = c_int
lib.pamc204_query_actual_position.argtypes = [c_int, c_int]

lib.pamc204_query_motion_status.restype  = c_int
lib.pamc204_query_motion_status.argtypes = [c_int, c_int]

lib.pamc204_query_move_direction.restype  = c_char
lib.pamc204_query_move_direction.argtypes = [c_int, c_int]

# ── 4軸同時操作API ────────────────────────────────────────────────────────────
lib.pamc204_move_relative_all_channels.restype  = c_bool
lib.pamc204_move_relative_all_channels.argtypes = [c_int, c_int]

lib.pamc204_query_actual_position_all_channels.restype  = c_bool
lib.pamc204_query_actual_position_all_channels.argtypes = [c_int, c_int * 4]

lib.pamc204_query_motion_status_all_channels.restype  = c_bool
lib.pamc204_query_motion_status_all_channels.argtypes = [c_int, c_int * 4]

lib.pamc204_move_infinite_all_channels.restype  = c_bool
lib.pamc204_move_infinite_all_channels.argtypes = [c_int, c_char]

lib.pamc204_stop_motion_all_channels.restype  = c_bool
lib.pamc204_stop_motion_all_channels.argtypes = [c_int]

# テスト対象アドレス
address = 1  # E01

INT_MIN = -2147483648

# 4軸同時操作API用のヘルパー関数
def test_query_actual_position_all_channels():
    """全チャンネルの位置を取得して表示"""
    positions = (c_int * 4)()
    result = lib.pamc204_query_actual_position_all_channels(address, positions)
    print(f"  Positions: CH1={positions[0]}, CH2={positions[1]}, CH3={positions[2]}, CH4={positions[3]}")
    return result

def test_query_motion_status_all_channels():
    """全チャンネルのモーション状態を取得して表示"""
    statuses = (c_int * 4)()
    result = lib.pamc204_query_motion_status_all_channels(address, statuses)
    print(f"  Statuses:")
    # レスポンス: 0=駆動中(Moving), 1=停止(Stopped), -1=エラー/未接続
    for i in range(4):
        if statuses[i] == 1:
            status_str = "Stopped"
        elif statuses[i] == 0:
            status_str = "Moving"
        else:
            status_str = "Error/Disconnected"
        print(f"    CH{i+1}: {status_str} (value={statuses[i]})")
    return result

def test_query_actual_position(ch):
    """単チャンネルの位置を取得して表示"""
    val = lib.pamc204_query_actual_position(address, ch)
    if val == INT_MIN:
        print(f"  query_actual_position ch{ch}: FAIL (INT_MIN)")
        return False
    print(f"  query_actual_position ch{ch}: {val}")
    return True

def test_query_acceleration(ch):
    """加速度を取得して表示"""
    val = lib.pamc204_query_acceleration(address, ch)
    if val == -1:
        print(f"  query_acceleration ch{ch}: FAIL (-1)")
        return False
    print(f"  query_acceleration ch{ch}: {val}")
    return True

# 呼び出し例をリスト化（BUSYエラーを避けるため、モーション完了を待つ）
tests = [
    ("send_command_E01INF", lambda: lib.pamc204_send_command(b"E01INF", None, 0), 0),
    ("send_command_E01",    lambda: lib.pamc204_send_command(b"E01",    None, 0), 0),
    ("set_address",         lambda: lib.pamc204_set_address(1), 0),  # E01
    ("set_voltage_150V",    lambda: lib.pamc204_set_voltage(address, 4095), 0),
    ("set_voltage_110V",    lambda: lib.pamc204_set_voltage(address, 3000), 0),
    ("set_voltage_70V",     lambda: lib.pamc204_set_voltage(address, 1900), 0),

    # パルス駆動テスト（短いパルス数で完了を待つ）
    ("rotate_positive_100pulses", lambda: lib.pamc204_rotate_positive(address, 1500, 100, b"A"), 0.5),
    ("rotate_negative_100pulses", lambda: lib.pamc204_rotate_negative(address, 1500, 100, b"A"), 0.5),

    # 加速度・速度設定テスト（NPコマンド）
    ("set_acceleration_10000", lambda: lib.pamc204_set_acceleration(address, 1, 10000), 0),
    ("query_acceleration",     lambda: test_query_acceleration(1), 0),
    ("set_velocity_1500",      lambda: lib.pamc204_set_velocity(address, 1, 1500), 0),

    # 位置制御テスト（NPコマンド、加速度対応）
    ("move_absolute_1000",       lambda: lib.pamc204_move_absolute(address, 1, 1000), 1.0),
    ("query_actual_position",    lambda: test_query_actual_position(1), 0),
    ("move_relative_500",        lambda: lib.pamc204_move_relative(address, 1, 500), 1.0),
    ("query_actual_position_2",  lambda: test_query_actual_position(1), 0),

    # 無限移動と停止テスト（加速度対応）
    ("move_infinite_positive", lambda: lib.pamc204_move_infinite(address, 1, b"+"), 0.5),
    ("stop_motion",            lambda: lib.pamc204_stop_motion(address, 1), 0.5),

    # 最終確認
    ("query_actual_position_final", lambda: test_query_actual_position(1), 0),

    # 4軸同時操作APIテスト
    ("move_relative_all_channels",         lambda: lib.pamc204_move_relative_all_channels(address, 500), 2.0),
    ("query_actual_position_all_channels", test_query_actual_position_all_channels, 0),
    ("query_motion_status_all_channels",   test_query_motion_status_all_channels, 0),

    # 4軸同時無限移動と停止テスト
    ("move_infinite_all_channels",                  lambda: lib.pamc204_move_infinite_all_channels(address, b"+"), 0.5),
    ("stop_motion_all_channels",                    lambda: lib.pamc204_stop_motion_all_channels(address), 0.5),
    ("query_motion_status_all_channels_after_stop", test_query_motion_status_all_channels, 0),
]

# 順に試す
for name, func, wait_time in tests:
    print(f"\n- Testing {name}...")
    ok = func()
    if ok:
        print(f"  {name} succeeded")
    else:
        print(f"  {name} failed")

    # 次のコマンドの前に待機（モーション完了やコマンド処理を待つ）
    if wait_time > 0:
        print(f"  Waiting {wait_time}s for motion to complete...")
        time.sleep(wait_time)
