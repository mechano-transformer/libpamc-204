"""
PAMC-204 DLL (pamc204.dll) の Python ラッパー
Windows 前提: test_windows_all_apis.py と同じシグネチャ定義を使用
"""
import ctypes
from ctypes import wintypes, c_char_p, c_char
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
    """ctypes 関数シグネチャを設定する（test_windows_all_apis.py と同じ定義）。"""
    lib.pamc204_send_command.restype  = wintypes.BOOL
    lib.pamc204_send_command.argtypes = [c_char_p]

    lib.pamc204_get_firmware_version.restype  = wintypes.BOOL
    lib.pamc204_get_firmware_version.argtypes = [wintypes.INT]

    lib.pamc204_check_device.restype  = wintypes.BOOL
    lib.pamc204_check_device.argtypes = [wintypes.INT]

    lib.pamc204_set_voltage.restype  = wintypes.BOOL
    lib.pamc204_set_voltage.argtypes = [wintypes.INT, wintypes.INT]

    lib.pamc204_set_acceleration.restype  = wintypes.BOOL
    lib.pamc204_set_acceleration.argtypes = [wintypes.INT, wintypes.INT, wintypes.INT]

    lib.pamc204_set_velocity.restype  = wintypes.BOOL
    lib.pamc204_set_velocity.argtypes = [wintypes.INT, wintypes.INT, wintypes.INT]

    lib.pamc204_move_absolute.restype  = wintypes.BOOL
    lib.pamc204_move_absolute.argtypes = [wintypes.INT, wintypes.INT, wintypes.INT]

    lib.pamc204_move_relative.restype  = wintypes.BOOL
    lib.pamc204_move_relative.argtypes = [wintypes.INT, wintypes.INT, wintypes.INT]

    lib.pamc204_query_actual_position.restype  = wintypes.BOOL
    lib.pamc204_query_actual_position.argtypes = [wintypes.INT, wintypes.INT]

    lib.pamc204_query_motion_status.restype  = wintypes.BOOL
    lib.pamc204_query_motion_status.argtypes = [wintypes.INT, wintypes.INT]

    lib.pamc204_move_infinite.restype  = wintypes.BOOL
    lib.pamc204_move_infinite.argtypes = [wintypes.INT, wintypes.INT, c_char]

    lib.pamc204_stop_motion.restype  = wintypes.BOOL
    lib.pamc204_stop_motion.argtypes = [wintypes.INT, wintypes.INT]

    lib.pamc204_abort_motion.restype  = wintypes.BOOL
    lib.pamc204_abort_motion.argtypes = [wintypes.INT]

    lib.pamc204_set_home_position.restype  = wintypes.BOOL
    lib.pamc204_set_home_position.argtypes = [wintypes.INT, wintypes.INT, wintypes.INT]

    lib.pamc204_stop_motion_all_channels.restype  = wintypes.BOOL
    lib.pamc204_stop_motion_all_channels.argtypes = [wintypes.INT]


# モジュールロード時に DLL を読み込む（パス未指定 = 自動検索）
pamc204_lib = _load_pamc204_dll()


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
        """実位置問い合わせ（ExxmTP?）。例: E011TP?"""
        if not self.is_connected:
            return False
        return bool(self.lib.pamc204_query_actual_position(self.address, channel))

    def query_motion_status(self, channel):
        """動作状態確認（ExxmMD?）。例: E011MD?"""
        if not self.is_connected:
            return False
        return bool(self.lib.pamc204_query_motion_status(self.address, channel))

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

    def wait_for_stop(self, channel, poll_interval=0.05):
        """動作完了待ち（ExxmMD? を送信して短時間待機）。

        現 DLL は戻り値が BOOL のみで停止状態を直接取得できないため、
        MD? コマンドを送信しながら一定時間待機する。
        実用上は ADC の sample_period が十分長ければ動作完了後に次のコマンドが送られる。
        """
        if not self.is_connected:
            return True
        self.lib.pamc204_query_motion_status(self.address, channel)
        time.sleep(poll_interval)
        return True
