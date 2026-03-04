"""
PAMC-104 シリアル通信ラッパー（pamc104_wrapper.py）
RS232C 経由で直接コマンドを送信する（DLL 不使用）。

PAMC-104 コマンド仕様（PAM-DOC-MAN-251001-007 6.3節）:
  通信確認  : CON          → OK
  バージョン: INF          → PAMC-104 Ver:x.x.x
  正方向駆動: NRffffnnnnA  → OK（駆動開始）、FIN（駆動完了）
  逆方向駆動: RRffffnnnnA  → OK（駆動開始）、FIN（駆動完了）
  6桁拡張  : NRffffXnnnnnnA（ファームウェア 0.8.0 以降）
  停止      : S            → FIN（実際に移動したパルス数付き）

  ffff : 駆動周波数（1～1500 Hz、4桁）
  nnnn : 駆動パルス数（0000～9999、0000=連続駆動）
  A    : 軸指定（A=ch1, B=ch2, C=ch3, D=ch4）

  返答メッセージ:
    OK    : コマンドを正常に受信
    FIN   : 駆動終了（パルス数指定時）
    ERROR : コマンド入力間違い
    BUSY  : 駆動中

通信パラメータ:
  ボーレート  : 115200 bps
  データビット: 8 bit
  パリティ    : なし
  ストップビット: 1 bit
  フロー制御  : なし
  デリミタ    : CR+LF

注意:
  - PAMC-104 はアドレス指定なし（E%02d 形式は PAMC-204 専用）
  - PAMC-204 との互換性のため move_relative(channel, pulses) メソッドを提供する
"""
import serial
import serial.tools.list_ports
import time

# 軸番号 → チャンネル文字 変換テーブル
_CH_LETTER = {1: 'A', 2: 'B', 3: 'C', 4: 'D'}

# 固定周波数 [Hz]
VELOCITY_HZ: int = 1500

# シリアル通信パラメータ
_BAUD_RATE   = 115200
_TIMEOUT_SEC = 2.0


class PAMC104:
    """PAMC-104 シリアル通信ラッパークラス。

    RS232C 経由で直接コマンドを送信する（DLL 不使用）。
    PAMC-204 ラッパー（PAMC204 クラス）との互換性のため、
    move_relative(channel, pulses) / wait_for_stop(channel) メソッドを提供する。

    Args:
        address:  未使用（PAMC-104 はアドレス指定なし）。互換性のため残す。
        dll_path: 未使用（PAMC-104 は DLL 不使用）。互換性のため残す。
        port:     シリアルポート名（例: 'COM3', '/dev/ttyUSB0'）。
                  None の場合は connect() 時に自動検索する。
    """

    VELOCITY_HZ: int = VELOCITY_HZ

    def __init__(self, address: int = 1, dll_path: str | None = None,
                 port: str | None = None):
        # address / dll_path は PAMC-204 との互換性のため受け取るが使用しない
        self.address = address
        self._port_name: str | None = port
        self._ser: serial.Serial | None = None
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected and self._ser is not None and self._ser.is_open

    # ================================================================
    # 接続管理
    # ================================================================

    def connect(self, port: str | None = None) -> bool:
        """PAMC-104 に接続する。

        port が指定された場合はそのポートを使用する。
        未指定の場合は self._port_name を使用し、それも None なら
        利用可能なシリアルポートを順に試して CON コマンドで確認する。

        Returns:
            bool: 接続成功なら True
        """
        if port is not None:
            self._port_name = port

        if self._port_name is not None:
            return self._try_connect(self._port_name)

        # ポート自動検索
        ports = [p.device for p in serial.tools.list_ports.comports()]
        print(f"[PAMC104] Auto-searching ports: {ports}")
        for p in ports:
            if self._try_connect(p):
                return True
        print("[PAMC104] Device not found on any port.")
        return False

    def _try_connect(self, port: str) -> bool:
        """指定ポートで接続を試みる。"""
        try:
            if self._ser and self._ser.is_open:
                self._ser.close()
            self._ser = serial.Serial(
                port=port,
                baudrate=_BAUD_RATE,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=_TIMEOUT_SEC,
                write_timeout=_TIMEOUT_SEC,
            )
            # CON コマンドで通信確認
            resp = self._send_cmd("CON")
            if "OK" in resp:
                self._connected = True
                self._port_name = port
                print(f"[PAMC104] Connected on {port} (CON -> {resp!r})")
                return True
            # CON が失敗した場合は INF でも試みる
            resp = self._send_cmd("INF")
            if resp:
                self._connected = True
                self._port_name = port
                print(f"[PAMC104] Connected on {port} (INF -> {resp!r})")
                return True
            self._ser.close()
        except Exception as e:
            print(f"[PAMC104] Failed to connect on {port}: {e}")
            if self._ser:
                try:
                    self._ser.close()
                except Exception:
                    pass
        return False

    def disconnect(self) -> None:
        """接続を切断する。"""
        self._connected = False
        if self._ser and self._ser.is_open:
            try:
                self._ser.close()
            except Exception:
                pass
        print("[PAMC104] Disconnected")

    def set_port(self, port: str) -> None:
        """シリアルポートを設定する（connect() 前に呼ぶ）。"""
        self._port_name = port

    # ================================================================
    # シリアル通信ヘルパー
    # ================================================================

    def _send_cmd(self, cmd: str, wait_fin: bool = False,
                  fin_timeout: float = 10.0,
                  flush_before: bool = True) -> str:
        """コマンドを送信してレスポンスを返す。

        Args:
            cmd:          送信コマンド文字列（CR+LF は自動付加）
            wait_fin:     True の場合、FIN が返るまで待機する（駆動コマンド用）
            fin_timeout:  FIN 待機タイムアウト（秒）
            flush_before: True の場合、送信前に受信バッファをクリアする。
                          駆動コマンド（NR/RR）の後に wait_for_stop() で FIN を
                          待つ場合は False にすること（FIN を消去しないため）。
        Returns:
            str: レスポンス文字列（複数行の場合は最後の行）
        """
        if self._ser is None or not self._ser.is_open:
            return ""
        try:
            if flush_before:
                self._ser.reset_input_buffer()
            self._ser.write(f"{cmd}\r\n".encode("ascii"))
            # 最初のレスポンス（OK / ERROR / BUSY）を読む
            line = self._ser.readline().decode("ascii", errors="replace").strip()
            print(f"[PAMC104] CMD: {cmd!r} -> {line!r}")

            if wait_fin and line == "OK":
                # FIN が返るまで待機
                deadline = time.time() + fin_timeout
                while time.time() < deadline:
                    fin_line = self._ser.readline().decode("ascii", errors="replace").strip()
                    print(f"[PAMC104] (wait FIN) -> {fin_line!r}")
                    if fin_line.startswith("FIN"):
                        return fin_line
                    if fin_line in ("ERROR", "BUSY"):
                        return fin_line
                print(f"[PAMC104] wait_fin timeout for cmd={cmd!r}")
            return line
        except Exception as e:
            print(f"[PAMC104] Serial error (cmd={cmd!r}): {e}")
            return ""

    # ================================================================
    # 駆動コマンド
    # ================================================================

    def move_pulses(self, channel: int, pulses: int) -> bool:
        """指定チャンネルを相対移動させる（駆動開始のみ、完了待ちなし）。

        pulses > 0 → 正方向（NR コマンド）
        pulses < 0 → 逆方向（RR コマンド）
        pulses == 0 → 何もしない

        コマンド形式:
          NRffffnnnnA  (正方向、4桁パルス)
          NRffffXnnnnnnA  (正方向、6桁拡張パルス)
          RRffffnnnnA  (逆方向、4桁パルス)
          RRffffXnnnnnnA  (逆方向、6桁拡張パルス)

        シーケンス:
          1. reset_input_buffer() で前回の残留データを除去（flush_before=True）
          2. NR/RR コマンドを送信
          3. "OK" を受信して返る
          4. 呼び出し元が wait_for_stop() で FIN を待つ
          ※ flush_before は write() の前に実行されるため、
            後続の FIN（手順4）を消去しない。

        Returns:
            bool: コマンド送信成功（OK 受信）かどうか
        """
        if not self.is_connected:
            return False
        if pulses == 0:
            return True

        ch = _CH_LETTER.get(channel, 'A')
        direction = "NR" if pulses > 0 else "RR"
        abs_pulses = abs(pulses)

        if abs_pulses <= 9999:
            cmd = f"{direction}{self.VELOCITY_HZ:04d}{abs_pulses:04d}{ch}"
        else:
            cmd = f"{direction}{self.VELOCITY_HZ:04d}X{abs_pulses:06d}{ch}"

        resp = self._send_cmd(cmd, flush_before=True)
        return resp == "OK"

    def move_relative(self, channel: int, pulses: int) -> bool:
        """PAMC204 クラスとの互換性のため move_pulses の別名として提供。"""
        return self.move_pulses(channel, pulses)

    def stop(self) -> str:
        """駆動停止（S コマンド）。

        Returns:
            str: FIN + 実際に移動したパルス数（例: 'FIN 0042'）
        """
        if not self.is_connected:
            return ""
        resp = self._send_cmd("S")
        return resp

    def stop_motion(self, channel: int) -> bool:
        """PAMC204 クラスとの互換性のため stop の別名として提供。"""
        resp = self.stop()
        return bool(resp)

    def abort_motion(self) -> bool:
        """全軸即停止（S コマンド）。"""
        resp = self.stop()
        return bool(resp)

    # ================================================================
    # 動作完了待ち
    # ================================================================

    def wait_for_stop(self, channel: int, poll_interval: float = 0.05,
                      timeout: float = 10.0) -> bool:
        """動作完了待ち。

        PAMC-104 は駆動完了時に FIN を返す。
        move_pulses() 後に FIN が届くまで readline() でポーリングする。

        Args:
            channel:       待機対象チャンネル番号（PAMC-104 では使用しない）
            poll_interval: ポーリング間隔（秒）
            timeout:       タイムアウト（秒）
        Returns:
            bool: 停止確認できたら True、タイムアウトなら False
        """
        if not self.is_connected:
            return True
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                line = self._ser.readline().decode("ascii", errors="replace").strip()
                if line:
                    print(f"[PAMC104] wait_for_stop -> {line!r}")
                if line.startswith("FIN"):
                    return True
                if line in ("ERROR", "BUSY"):
                    print(f"[PAMC104] wait_for_stop: unexpected response {line!r}")
                    return False
            except Exception as e:
                print(f"[PAMC104] wait_for_stop error: {e}")
                return False
            time.sleep(poll_interval)
        print(f"[PAMC104] wait_for_stop: timeout ch{channel}")
        return False

    # ================================================================
    # 情報取得（PAMC204 互換スタブ）
    # ================================================================

    def query_actual_position(self, channel: int):
        """PAMC-104 は位置問い合わせ非対応のため None を返す。"""
        return None

    def query_motion_status(self, channel: int):
        """PAMC-104 は動作状態問い合わせ非対応のため None を返す。"""
        return None

    def set_home_position(self, channel: int, position: int = 0) -> bool:
        """PAMC-104 はホームポジション設定非対応のため False を返す。"""
        print("[PAMC104] set_home_position: not supported")
        return False

    def move_absolute(self, channel: int, position: int) -> bool:
        """PAMC-104 は絶対位置移動非対応のため False を返す。"""
        print("[PAMC104] move_absolute: not supported")
        return False
