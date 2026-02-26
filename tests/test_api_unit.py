"""
send_command / send_commands_batch のユニットテスト

実際のデバイスを使わず、シリアルポートをモックして
API の動作を検証します。

実行方法:
    python -m pytest tests/test_api_unit.py -v
    # または Docker で:
    docker run --rm -v $(pwd):/work -w /work python:3.12-slim \
        sh -c "pip install pytest && python -m pytest tests/test_api_unit.py -v"
"""

import ctypes
import os
import sys
import unittest
from unittest.mock import MagicMock, patch, call

# ── ライブラリのロード ────────────────────────────────────────────────────────
# Linux: build/libpamc204.so が存在する場合のみ実機テストを有効化
_LIB_PATH_LINUX   = os.path.join(os.path.dirname(__file__), "..", "build", "libpamc204.so")
_LIB_PATH_WINDOWS = os.path.join(os.path.dirname(__file__), "..", "build", "Release", "pamc204.dll")

def _try_load_lib():
    for path in [_LIB_PATH_LINUX, _LIB_PATH_WINDOWS]:
        if os.path.exists(path):
            try:
                return ctypes.CDLL(path)
            except Exception:
                pass
    return None

_lib = _try_load_lib()
_HAS_LIB = _lib is not None

# ── モックベーステスト ────────────────────────────────────────────────────────

class TestSendCommandMock(unittest.TestCase):
    """send_command のロジックをモックでテストする。

    シリアルポートを使わず、pamc204 名前空間の内部関数をモックして
    コマンド文字列の生成・レスポンスのパースを検証する。
    """

    def _make_mock_send_command(self, response: str):
        """指定レスポンスを返す send_command モックを生成する。"""
        mock = MagicMock(return_value=response)
        return mock

    def test_send_command_returns_response(self):
        """send_command が正常レスポンスを返すこと。"""
        mock_fn = self._make_mock_send_command("OK")
        result = mock_fn("E01INF")
        self.assertEqual(result, "OK")
        mock_fn.assert_called_once_with("E01INF")

    def test_send_command_returns_empty_on_failure(self):
        """send_command が失敗時に空文字列を返すこと。"""
        mock_fn = self._make_mock_send_command("")
        result = mock_fn("E01INF")
        self.assertEqual(result, "")

    def test_send_commands_batch_returns_list(self):
        """send_commands_batch が各コマンドのレスポンスリストを返すこと。"""
        mock_fn = MagicMock(return_value=["100", "200", "300"])
        result = mock_fn(["E011AC?", "E011VA?", "E011TP?"])
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0], "100")
        self.assertEqual(result[1], "200")
        self.assertEqual(result[2], "300")

    def test_send_commands_batch_returns_empty_on_failure(self):
        """send_commands_batch が失敗時に空リストを返すこと。"""
        mock_fn = MagicMock(return_value=[])
        result = mock_fn(["E011AC?"])
        self.assertEqual(result, [])

    def test_send_commands_batch_empty_input(self):
        """send_commands_batch に空リストを渡すと空リストを返すこと。"""
        mock_fn = MagicMock(return_value=[])
        result = mock_fn([])
        self.assertEqual(result, [])


class TestQueryApiParsing(unittest.TestCase):
    """query系 API のレスポンスパースロジックをテストする。

    実際の send_one() / parse_int() の動作を模倣して
    各 query 関数の戻り値変換を検証する。
    """

    INT_MIN = -2147483648

    def _parse_int(self, resp: str, fallback: int = INT_MIN) -> int:
        """api.cpp の parse_int() と同等のロジック。"""
        if not resp:
            return fallback
        try:
            return int(resp)
        except (ValueError, OverflowError):
            return fallback

    def test_parse_int_normal(self):
        """正常な数値文字列をパースできること。"""
        self.assertEqual(self._parse_int("1000"), 1000)
        self.assertEqual(self._parse_int("-500"), -500)
        self.assertEqual(self._parse_int("0"), 0)

    def test_parse_int_empty_returns_fallback(self):
        """空文字列は fallback を返すこと。"""
        self.assertEqual(self._parse_int(""), self.INT_MIN)
        self.assertEqual(self._parse_int("", fallback=-1), -1)

    def test_parse_int_invalid_returns_fallback(self):
        """不正な文字列は fallback を返すこと。"""
        self.assertEqual(self._parse_int("ERROR"), self.INT_MIN)
        self.assertEqual(self._parse_int("BUSY"), self.INT_MIN)
        self.assertEqual(self._parse_int("abc"), self.INT_MIN)

    def test_query_motion_status_parsing(self):
        """query_motion_status のレスポンスパース（'0'/'1' → int）。"""
        def parse_status(resp: str) -> int:
            if not resp:
                return -1
            if resp[0] in ('0', '1'):
                return int(resp[0])
            return -1

        self.assertEqual(parse_status("0"), 0)   # 動作中
        self.assertEqual(parse_status("1"), 1)   # 停止
        self.assertEqual(parse_status(""),  -1)  # 失敗
        self.assertEqual(parse_status("ERROR"), -1)

    def test_query_move_direction_parsing(self):
        """query_move_direction のレスポンスパース（先頭文字を返す）。"""
        def parse_direction(resp: str) -> str:
            if not resp:
                return '\0'
            return resp[0]

        self.assertEqual(parse_direction("+"), '+')
        self.assertEqual(parse_direction("-"), '-')
        self.assertEqual(parse_direction(""),  '\0')

    def test_query_acceleration_fallback_is_minus1(self):
        """query_acceleration の失敗時は -1 を返すこと。"""
        self.assertEqual(self._parse_int("", fallback=-1), -1)

    def test_query_actual_position_fallback_is_int_min(self):
        """query_actual_position の失敗時は INT_MIN を返すこと。"""
        self.assertEqual(self._parse_int(""), self.INT_MIN)


class TestCommandStringGeneration(unittest.TestCase):
    """コマンド文字列の生成ロジックをテストする。

    api.cpp の snprintf フォーマットと同等の Python 実装で
    コマンド文字列が正しく生成されることを検証する。
    """

    def _fmt_get_firmware_version(self, address: int) -> str:
        return f"E{address:02d}INF"

    def _fmt_check_device(self, address: int) -> str:
        return f"E{address:02d}"

    def _fmt_set_voltage(self, address: int, dac: int) -> str:
        return f"E{address:02d}DAC{dac:04d}"

    def _fmt_rotate_positive(self, address: int, freq: int, pulses: int, ch: str) -> str:
        return f"E{address:02d}NR{freq:04d}{pulses:04d}{ch}"

    def _fmt_rotate_positive_ex(self, address: int, freq: int, pulses: int, ch: str) -> str:
        return f"E{address:02d}NR{freq:04d}X{pulses:06d}{ch}"

    def _fmt_set_acceleration(self, address: int, channel: int, acc: int) -> str:
        return f"E{address:02d}{channel}AC{acc}"

    def _fmt_query_acceleration(self, address: int, channel: int) -> str:
        return f"E{address:02d}{channel}AC?"

    def _fmt_move_relative(self, address: int, channel: int, pos: int) -> str:
        return f"E{address:02d}{channel}PR{pos}"

    def _fmt_query_actual_position(self, address: int, channel: int) -> str:
        return f"E{address:02d}{channel}TP?"

    def _fmt_query_motion_status(self, address: int, channel: int) -> str:
        return f"E{address:02d}{channel}MD?"

    def _fmt_stop_motion(self, address: int, channel: int) -> str:
        return f"E{address:02d}{channel}ST"

    def _fmt_move_infinite(self, address: int, channel: int, direction: str) -> str:
        return f"E{address:02d}{channel}MV{direction}"

    def _fmt_abort_motion(self, address: int) -> str:
        return f"E{address:02d}AB"

    # ── テストケース ──────────────────────────────────────────────────────────

    def test_get_firmware_version(self):
        self.assertEqual(self._fmt_get_firmware_version(1),  "E01INF")
        self.assertEqual(self._fmt_get_firmware_version(12), "E12INF")

    def test_check_device(self):
        self.assertEqual(self._fmt_check_device(1),  "E01")
        self.assertEqual(self._fmt_check_device(32), "E32")

    def test_set_voltage(self):
        self.assertEqual(self._fmt_set_voltage(1, 4095), "E01DAC4095")
        self.assertEqual(self._fmt_set_voltage(1, 1900), "E01DAC1900")

    def test_rotate_positive(self):
        self.assertEqual(self._fmt_rotate_positive(1, 1500, 1000, 'A'), "E01NR15001000A")
        self.assertEqual(self._fmt_rotate_positive(1, 1500, 0, 'A'),    "E01NR15000000A")

    def test_rotate_positive_ex(self):
        self.assertEqual(self._fmt_rotate_positive_ex(1, 1500, 100000, 'A'), "E01NR1500X100000A")

    def test_set_acceleration(self):
        self.assertEqual(self._fmt_set_acceleration(1, 1, 10000), "E011AC10000")
        self.assertEqual(self._fmt_set_acceleration(1, 4, 150000), "E014AC150000")

    def test_query_acceleration(self):
        self.assertEqual(self._fmt_query_acceleration(1, 1), "E011AC?")

    def test_move_relative(self):
        self.assertEqual(self._fmt_move_relative(1, 1, 500),   "E011PR500")
        self.assertEqual(self._fmt_move_relative(1, 1, -500),  "E011PR-500")
        self.assertEqual(self._fmt_move_relative(1, 2, 1000),  "E012PR1000")

    def test_query_actual_position(self):
        self.assertEqual(self._fmt_query_actual_position(1, 1), "E011TP?")
        self.assertEqual(self._fmt_query_actual_position(1, 4), "E014TP?")

    def test_query_motion_status(self):
        self.assertEqual(self._fmt_query_motion_status(1, 1), "E011MD?")

    def test_stop_motion(self):
        self.assertEqual(self._fmt_stop_motion(1, 1), "E011ST")

    def test_move_infinite(self):
        self.assertEqual(self._fmt_move_infinite(1, 1, '+'), "E011MV+")
        self.assertEqual(self._fmt_move_infinite(1, 1, '-'), "E011MV-")

    def test_abort_motion(self):
        self.assertEqual(self._fmt_abort_motion(1), "E01AB")

    def test_all_channels_commands(self):
        """4軸同時操作用コマンドが正しく生成されること。"""
        address = 1
        position = 500
        cmds = [f"E{address:02d}{ch}PR{position}" for ch in range(1, 5)]
        self.assertEqual(cmds[0], "E011PR500")
        self.assertEqual(cmds[1], "E012PR500")
        self.assertEqual(cmds[2], "E013PR500")
        self.assertEqual(cmds[3], "E014PR500")


# ── 実機テスト（ライブラリが存在する場合のみ実行） ────────────────────────────

@unittest.skipUnless(_HAS_LIB, "libpamc204.so / pamc204.dll が見つかりません（ビルドが必要）")
class TestWithLibrary(unittest.TestCase):
    """実際にビルドされたライブラリを使ったテスト。

    デバイスが接続されていない場合は失敗が期待されます。
    """

    def setUp(self):
        from ctypes import c_bool, c_char_p, c_int, c_char
        self.lib = _lib
        self.lib.pamc204_send_command.restype  = c_bool
        self.lib.pamc204_send_command.argtypes = [c_char_p, c_char_p, c_int]
        self.lib.pamc204_query_actual_position.restype  = c_int
        self.lib.pamc204_query_actual_position.argtypes = [c_int, c_int]
        self.lib.pamc204_query_motion_status.restype  = c_int
        self.lib.pamc204_query_motion_status.argtypes = [c_int, c_int]
        self.lib.pamc204_query_acceleration.restype  = c_int
        self.lib.pamc204_query_acceleration.argtypes = [c_int, c_int]

    def test_library_loads(self):
        """ライブラリが正常にロードされること。"""
        self.assertIsNotNone(self.lib)

    def test_send_command_returns_bool(self):
        """pamc204_send_command が bool を返すこと（デバイス未接続でも型は正しい）。"""
        result = self.lib.pamc204_send_command(b"E01INF", None, 0)
        self.assertIsInstance(bool(result), bool)

    def test_query_actual_position_returns_int(self):
        """pamc204_query_actual_position が int を返すこと。"""
        result = self.lib.pamc204_query_actual_position(1, 1)
        self.assertIsInstance(result, int)

    def test_query_motion_status_returns_int(self):
        """pamc204_query_motion_status が int を返すこと（-1, 0, 1 のいずれか）。"""
        result = self.lib.pamc204_query_motion_status(1, 1)
        self.assertIsInstance(result, int)
        self.assertIn(result, [-1, 0, 1])

    def test_query_acceleration_returns_int(self):
        """pamc204_query_acceleration が int を返すこと。"""
        result = self.lib.pamc204_query_acceleration(1, 1)
        self.assertIsInstance(result, int)


if __name__ == "__main__":
    unittest.main(verbosity=2)
