"""
PAMC-204 DLL (pamc204.dll) の Python ラッパー
Windows 前提: test_windows_all_apis.py と同じシグネチャ定義を使用
"""
import ctypes
from ctypes import wintypes, c_char_p, c_char, c_int
import os
import time


def _load_pamc204_dll(dll_path: str | None = None):
    """pamc204.dll をロードして返す。失敗時は None を返す。

    Args:
        dll_path: DLL の絶対/相対パスを直接指定する場合に渡す。
                  None の場合は既定の候補パスを順に探す。
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    if dll_path is not None:
        # 明示的にパスが指定された場合はそのパスのみ試す
        candidates = [dll_path]
    else:
        candidates = [
            os.path.join(base_dir, "build", "Release", "pamc204.dll"),
            os.path.join(base_dir, "pamc204.dll"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "pamc204.dll"),
            "./build/Release/pamc204.dll",
            "./pamc204.dll",
        ]

    for path in candidates:
        if os.path.exists(path):
            try:
                lib = ctypes.CDLL(path)
                _setup_signatures(lib)
                print(f"[PAMC204] Loaded DLL: {path}")
                return lib
            except Exception as e:
                print(f"[PAMC204] Failed to load {path}: {e}")
    print("[PAMC204] WARNING: pamc204.dll not found. Piezo motor commands will be disabled.")
    print("[PAMC204] Build: cd build && cmake -DCMAKE_BUILD_TYPE=Release .. && cmake --build . --config Release")
    return None


def _setup_signatures(lib):
    """ctypes 関数シグネチャを設定する。"""
    # 低レベルAPI: out_response バッファ付き
    lib.pamc204_send_command.restype  = wintypes.BOOL
    lib.pamc204_send_command.argtypes = [c_char_p, c_char_p, c_int]

    lib.pamc204_get_firmware_version.restype  = wintypes.BOOL
    lib.pamc204_get_firmware_version.argtypes = [wintypes.INT]

    lib.pamc204_check_device.restype  = wintypes.BOOL
    lib.pamc204_check_device.argtypes = [wintypes.INT]

    lib.pamc204_set_voltage.restype  = wintypes.BOOL
    lib.pamc204_set_voltage.argtypes = [wintypes.INT, wintypes.INT]

    lib.pamc204_set_acceleration.restype  = wintypes.BOOL
    lib.pamc204_set_acceleration.argtypes = [wintypes.INT, wintypes.INT, wintypes.INT]

    # query系: 値を int で直接返す（失敗時は -1 または INT_MIN）
    lib.pamc204_query_acceleration.restype  = c_int
    lib.pamc204_query_acceleration.argtypes = [wintypes.INT, wintypes.INT]

    lib.pamc204_set_velocity.restype  = wintypes.BOOL
    lib.pamc204_set_velocity.argtypes = [wintypes.INT, wintypes.INT, wintypes.INT]

    lib.pamc204_query_velocity.restype  = c_int
    lib.pamc204_query_velocity.argtypes = [wintypes.INT, wintypes.INT]

    lib.pamc204_set_home_position.restype  = wintypes.BOOL
    lib.pamc204_set_home_position.argtypes = [wintypes.INT, wintypes.INT, wintypes.INT]

    lib.pamc204_query_home_position.restype  = c_int
    lib.pamc204_query_home_position.argtypes = [wintypes.INT, wintypes.INT]

    lib.pamc204_move_absolute.restype  = wintypes.BOOL
    lib.pamc204_move_absolute.argtypes = [wintypes.INT, wintypes.INT, wintypes.INT]

    lib.pamc204_query_absolute_position.restype  = c_int
    lib.pamc204_query_absolute_position.argtypes = [wintypes.INT, wintypes.INT]

    lib.pamc204_move_relative.restype  = wintypes.BOOL
    lib.pamc204_move_relative.argtypes = [wintypes.INT, wintypes.INT, wintypes.INT]

    lib.pamc204_query_relative_position.restype  = c_int
    lib.pamc204_query_relative_position.argtypes = [wintypes.INT, wintypes.INT]

    lib.pamc204_query_actual_position.restype  = c_int
    lib.pamc204_query_actual_position.argtypes = [wintypes.INT, wintypes.INT]

    lib.pamc204_query_motion_status.restype  = c_int
    lib.pamc204_query_motion_status.argtypes = [wintypes.INT, wintypes.INT]

    lib.pamc204_move_infinite.restype  = wintypes.BOOL
    lib.pamc204_move_infinite.argtypes = [wintypes.INT, wintypes.INT, c_char]

    lib.pamc204_query_move_direction.restype  = c_char
    lib.pamc204_query_move_direction.argtypes = [wintypes.INT, wintypes.INT]

    lib.pamc204_stop_motion.restype  = wintypes.BOOL
    lib.pamc204_stop_motion.argtypes = [wintypes.INT, wintypes.INT]

    lib.pamc204_abort_motion.restype  = wintypes.BOOL
    lib.pamc204_abort_motion.argtypes = [wintypes.INT]

    lib.pamc204_stop_motion_all_channels.restype  = wintypes.BOOL
    lib.pamc204_stop_motion_all_channels.argtypes = [wintypes.INT]

    lib.pamc204_query_actual_position_all_channels.restype  = wintypes.BOOL
    lib.pamc204_query_actual_position_all_channels.argtypes = [wintypes.INT, wintypes.INT * 4]

    lib.pamc204_query_motion_status_all_channels.restype  = wintypes.BOOL
    lib.pamc204_query_motion_status_all_channels.argtypes = [wintypes.INT, wintypes.INT * 4]


# モジュールロード時に DLL を読み込む（パス未指定 = 自動検索）
pamc204_lib = _load_pamc204_dll()

# INT_MIN: query系の失敗時戻り値
_INT_MIN = -2147483648


class PAMC204:
    """PAMC-204 ドライバの Python ラッパークラス（Windows / pamc204.dll 使用）。

    使用前提:
      - E011（アドレス01, 軸1）と E012（アドレス01, 軸2）を使用
      - PAMC-204 は同時2軸駆動非対応のため、X軸・Y軸を順次駆動する

    コマンド対応表:
      connect()              -> Exx       (check_device)
      move_relative(ch, n)   -> ExxmPRn   (例: E011PR100)
      move_absolute(ch, n)   -> ExxmPAn   (例: E011PA500)
      set_home_position(ch)  -> ExxmDH0   (例: E011DH0)
      query_actual_position  -> ExxmTP?   (例: E011TP?)
      query_motion_status    -> ExxmMD?   (例: E011MD?)
      stop_motion(ch)        -> ExxmST    (例: E011ST)
      abort_motion()         -> ExxAB     (例: E01AB)

    Args:
        address:  PAMC-204 のデバイスアドレス（デフォルト: 1）
        dll_path: pamc204.dll のパスを明示指定する場合に渡す。
                  None の場合はモジュールロード時に自動検索した DLL を使用する。
    """

    def __init__(self, address: int = 1, dll_path: str | None = None):
        self.address = address
        # dll_path が指定された場合は再ロード、未指定はモジュールレベルの共有 lib を使用
        if dll_path is not None:
            self.lib = _load_pamc204_dll(dll_path)
        else:
            self.lib = pamc204_lib
        self._connected = False

    @property
    def is_connected(self):
        return self._connected and self.lib is not None

    # モーター速度（周波数）固定値 [Hz]
    VELOCITY_HZ: int = 1500

    def connect(self):
        """デバイス存在確認（Exx）を行い、接続状態にする。

        接続成功後、全チャンネルの速度を VELOCITY_HZ (1500 Hz) に固定設定する。
        コマンド例: E011SV1500（アドレス01, 軸1, 速度1500Hz）
        """
        if self.lib is None:
            print("[PAMC204] DLL not loaded.")
            return False
        ok = bool(self.lib.pamc204_check_device(self.address))
        if ok:
            self._connected = True
            print(f"[PAMC204] Connected to device at address {self.address}")
            # 全チャンネルの速度を 1500 Hz に固定設定
            for ch in (1, 2):
                v_ok = bool(self.lib.pamc204_set_velocity(self.address, ch, self.VELOCITY_HZ))
                print(f"[PAMC204] set_velocity ch{ch} = {self.VELOCITY_HZ} Hz: {'OK' if v_ok else 'FAIL'}")
        else:
            print(f"[PAMC204] Device not found at address {self.address}")
        return ok

    def disconnect(self):
        self._connected = False

    def move_relative(self, channel, pulses):
        """相対位置移動（ExxmPRnnnn）。例: E011PR100"""
        if not self.is_connected:
            return False
        return bool(self.lib.pamc204_move_relative(self.address, channel, pulses))

    def move_absolute(self, channel, position):
        """絶対位置移動（ExxmPAnnnn）。例: E011PA500"""
        if not self.is_connected:
            return False
        return bool(self.lib.pamc204_move_absolute(self.address, channel, position))

    def set_home_position(self, channel, position=0):
        """ホームポジション設定（ExxmDHnnnn）。例: E011DH0"""
        if not self.is_connected:
            return False
        return bool(self.lib.pamc204_set_home_position(self.address, channel, position))

    def query_actual_position(self, channel):
        """実位置問い合わせ（ExxmTP?）。例: E011TP?

        Returns:
            int | None: 実位置。失敗時（INT_MIN）は None。
        """
        if not self.is_connected:
            return None
        val = self.lib.pamc204_query_actual_position(self.address, channel)
        return None if val == _INT_MIN else val

    def query_motion_status(self, channel):
        """動作状態確認（ExxmMD?）。例: E011MD?

        Returns:
            int | None: 0=動作中(Moving), 1=停止(Stopped)。失敗時（-1）は None。
        """
        if not self.is_connected:
            return None
        val = self.lib.pamc204_query_motion_status(self.address, channel)
        return None if val == -1 else val

    def stop_motion(self, channel):
        """動作停止（ExxmST）。例: E011ST"""
        if not self.is_connected:
            return False
        return bool(self.lib.pamc204_stop_motion(self.address, channel))

    def abort_motion(self):
        """モーション停止（ExxAB）- 全軸即停止。例: E01AB"""
        if not self.is_connected:
            return False
        return bool(self.lib.pamc204_abort_motion(self.address))

    def query_actual_position_all_channels(self):
        """全チャンネルの実位置を取得する（ExxmTP? × 4ch）。

        Returns:
            list[int] | None: 各チャンネルの位置 [ch1, ch2, ch3, ch4]。失敗時は None。
        """
        if not self.is_connected:
            return None
        positions = (wintypes.INT * 4)()
        ok = bool(self.lib.pamc204_query_actual_position_all_channels(self.address, positions))
        if ok:
            return list(positions)
        return None

    def query_motion_status_all_channels(self):
        """全チャンネルの動作状態を取得する（ExxmMD? × 4ch）。

        Returns:
            list[int] | None: 各チャンネルの状態 [ch1, ch2, ch3, ch4]。
                              値: 1=停止(Stopped), 0=動作中(Moving), -1=エラー。
                              失敗時は None。
        """
        if not self.is_connected:
            return None
        statuses = (wintypes.INT * 4)()
        ok = bool(self.lib.pamc204_query_motion_status_all_channels(self.address, statuses))
        if ok:
            return list(statuses)
        return None

    def wait_for_stop(self, channel, poll_interval=0.05, timeout=5.0):
        """動作完了待ち（ExxmMD? でポーリング）。

        pamc204_query_motion_status を使って指定チャンネルの
        停止状態（status == 1）を確認するまでポーリングする。

        Args:
            channel:       待機対象チャンネル番号（1-4）
            poll_interval: ポーリング間隔（秒）
            timeout:       タイムアウト（秒）。超過時は警告を出して返る。

        Notes:
            query_motion_status が None を返す（DLL 失敗）場合は、
            移動コマンドは送信済みとみなし True を返す。
            これにより DLL の status 問い合わせが使えない環境でも
            timeout 遅延なしに動作を継続できる。
        """
        if not self.is_connected:
            return True
        deadline = time.time() + timeout
        while time.time() < deadline:
            status = self.query_motion_status(channel)
            if status is None:
                # DLL の status 問い合わせが失敗 → 移動済みとみなして続行
                print(f"[PAMC204] wait_for_stop: query_motion_status returned None for ch{channel}, assuming stopped")
                return True
            if status == 1:
                return True  # 停止確認
            time.sleep(poll_interval)
        print(f"[PAMC204] wait_for_stop: timeout waiting for ch{channel} to stop")
        return False
