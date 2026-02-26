"""
PAMC-104/PAMC-204 共通ラッパー
pamc204.dll の pamc204_send_command() を使い、
ExxNR1500nnnnA / ExxRR1500nnnnA 形式のコマンドを直接送信する。

コマンド仕様:
  ExxNR1500nnnnA  … 正方向（+）駆動
  ExxRR1500nnnnA  … 逆方向（-）駆動
  ExxS            … 連続駆動停止
  ExxAB           … 全軸即停止
  ExxmMD?         … 動作状態確認（0=動作中, 1=停止）
  Exx             … デバイス存在確認

  xx   : アドレス（2桁, 01〜32）
  1500 : 周波数固定（steps/sec）
  nnnn : パルス数（4桁, 0001〜9999）
         ※ 9999 超は X 拡張コマンド ExxNR1500Xnnnnnnz を使用
  y    : 軸指定（A=ch1, B=ch2, C=ch3, D=ch4）
"""
import ctypes
from ctypes import c_char_p, c_int, create_string_buffer
import os
import time

# 軸番号 → チャンネル文字 変換テーブル
_CH_LETTER = {1: 'A', 2: 'B', 3: 'C', 4: 'D'}

# 周波数固定値
VELOCITY_HZ: int = 1500

# レスポンスバッファサイズ
_RESP_BUF = 256


def _load_dll(dll_path: str | None = None):
    """pamc204.dll をロードして返す。失敗時は None。"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    if dll_path is not None:
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
                # pamc204_send_command シグネチャ設定
                lib.pamc204_send_command.restype  = ctypes.c_bool
                lib.pamc204_send_command.argtypes = [c_char_p, c_char_p, c_int]
                # check_device
                lib.pamc204_check_device.restype  = ctypes.c_bool
                lib.pamc204_check_device.argtypes = [c_int]
                print(f"[PAMC104/204] Loaded DLL: {path}")
                return lib
            except Exception as e:
                print(f"[PAMC104/204] Failed to load {path}: {e}")

    print("[PAMC104/204] WARNING: pamc204.dll not found. Motor commands will be disabled.")
    return None


# モジュールロード時に自動検索
_pamc_lib = _load_dll()


def _send(lib, command: str) -> str:
    """pamc204_send_command を呼び出してレスポンス文字列を返す。失敗時は空文字列。"""
    if lib is None:
        return ""
    buf = create_string_buffer(_RESP_BUF)
    ok = lib.pamc204_send_command(command.encode(), buf, _RESP_BUF)
    resp = buf.value.decode(errors="replace").strip()
    print(f"[CMD] {command!r} -> {resp!r} ({'OK' if ok else 'NG'})")
    return resp if ok else ""


class PAMC104_204:
    """PAMC-104 / PAMC-204 共通ラッパークラス。

    ExxNR1500nnnnA / ExxRR1500nnnnA 形式のコマンドを
    pamc204_send_command() 経由で送信する。

    PAMC-204 DLL ラッパー（PAMC204 クラス）との互換性のため、
    move_relative(channel, pulses) メソッドも提供する。

    Args:
        address:  デバイスアドレス（1〜32、デフォルト: 1）
        dll_path: pamc204.dll のパスを明示指定する場合に渡す。
    """

    VELOCITY_HZ: int = VELOCITY_HZ

    def __init__(self, address: int = 1, dll_path: str | None = None):
        self.address = address
        self.lib = _load_dll(dll_path) if dll_path is not None else _pamc_lib
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected and self.lib is not None

    def _addr_str(self) -> str:
        """アドレスを2桁ゼロ埋め文字列で返す。例: 1 -> '01'"""
        return f"{self.address:02d}"

    def _ch_letter(self, channel: int) -> str:
        """チャンネル番号をアルファベットに変換。1->A, 2->B, 3->C, 4->D"""
        return _CH_LETTER.get(channel, 'A')

    def connect(self) -> bool:
        """デバイス存在確認（Exx）を行い、接続状態にする。"""
        if self.lib is None:
            print("[PAMC104/204] DLL not loaded.")
            return False
        ok = bool(self.lib.pamc204_check_device(self.address))
        if ok:
            self._connected = True
            print(f"[PAMC104/204] Connected to device at address {self.address}")
        else:
            print(f"[PAMC104/204] Device not found at address {self.address}")
        return ok

    def disconnect(self) -> None:
        self._connected = False

    def move_pulses(self, channel: int, pulses: int) -> bool:
        """指定チャンネルを相対移動させる。

        pulses > 0 → 正方向（NR コマンド）
        pulses < 0 → 逆方向（RR コマンド）
        pulses == 0 → 何もしない

        コマンド形式:
          ExxNR1500nnnnA  (正方向、4桁パルス)
          ExxNR1500Xnnnnnnz  (正方向、6桁拡張パルス)
          ExxRR1500nnnnA  (逆方向、4桁パルス)
          ExxRR1500Xnnnnnnz  (逆方向、6桁拡張パルス)

        Returns:
            bool: コマンド送信成功かどうか
        """
        if not self.is_connected:
            return False
        if pulses == 0:
            return True

        addr = self._addr_str()
        ch   = self._ch_letter(channel)
        direction = "NR" if pulses > 0 else "RR"
        abs_pulses = abs(pulses)

        if abs_pulses <= 9999:
            # 4桁形式: ExxNR1500nnnnA
            cmd = f"E{addr}{direction}{self.VELOCITY_HZ:04d}{abs_pulses:04d}{ch}"
        else:
            # 6桁拡張形式: ExxNR1500Xnnnnnnz
            cmd = f"E{addr}{direction}{self.VELOCITY_HZ:04d}X{abs_pulses:06d}{ch}"

        resp = _send(self.lib, cmd)
        # 成功レスポンスは "ExxOK"
        return "OK" in resp

    def move_relative(self, channel: int, pulses: int) -> bool:
        """PAMC204 クラスとの互換性のため move_pulses の別名として提供。"""
        return self.move_pulses(channel, pulses)

    def stop(self) -> bool:
        """連続駆動停止（ExxS）。"""
        if not self.is_connected:
            return False
        resp = _send(self.lib, f"E{self._addr_str()}S")
        return bool(resp)  # FIN応答あれば成功

    def abort_motion(self) -> bool:
        """全軸即停止（ExxAB）。"""
        if not self.is_connected:
            return False
        _send(self.lib, f"E{self._addr_str()}AB")
        return True  # AB はレスポンスなし仕様

    def stop_motion(self, channel: int) -> bool:
        """PAMC204 クラスとの互換性のため abort_motion の別名として提供。"""
        return self.abort_motion()

    def query_motion_status(self, channel: int) -> int | None:
        """動作状態確認（ExxmMD?）。

        Returns:
            0=動作中(Moving), 1=停止(Stopped), None=失敗
        """
        if not self.is_connected:
            return None
        addr = self._addr_str()
        resp = _send(self.lib, f"E{addr}{channel}MD?")
        try:
            val = int(resp.strip())
            return val  # 0 or 1
        except ValueError:
            return None

    def wait_for_stop(self, channel: int, poll_interval: float = 0.05,
                      timeout: float = 10.0) -> bool:
        """動作完了待ち（ExxmMD? でポーリング）。

        Args:
            channel:       待機対象チャンネル番号（1-4）
            poll_interval: ポーリング間隔（秒）
            timeout:       タイムアウト（秒）
        Returns:
            bool: 停止確認できたら True、タイムアウトなら False
        """
        if not self.is_connected:
            return True
        deadline = time.time() + timeout
        while time.time() < deadline:
            status = self.query_motion_status(channel)
            if status == 1:
                return True  # 停止確認
            time.sleep(poll_interval)
        print(f"[PAMC104/204] wait_for_stop: timeout ch{channel}")
        return False
