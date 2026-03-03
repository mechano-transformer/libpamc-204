"""
エントリーポイント
Autocollimator & Piezo Motor Alignment Demo を起動する。

使い方（demo/ フォルダ内から実行）:
    python main.py                              # PAMC-204 DLL モード（デフォルト）
    python main.py --dll ./pamc204.dll          # DLL パスを明示指定
    python main.py --mode pamc104               # PAMC-104 RS232C 直接通信モード
    python main.py --mode pamc104 --port COM3   # PAMC-104 + COMポート指定
"""
import sys
import os
import argparse

# スクリプトとして直接実行された場合、親ディレクトリを sys.path に追加する
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from demo.gui import ADCGUI, PiezoMode


def main():
    parser = argparse.ArgumentParser(
        description="Autocollimator & Piezo Motor Alignment Demo"
    )
    parser.add_argument(
        "--dll",
        metavar="PATH",
        default=None,
        help="pamc204.dll のパスを明示指定する（省略時は自動検索）",
    )
    parser.add_argument(
        "--mode",
        metavar="MODE",
        default=PiezoMode.PAMC204.value,
        choices=[m.value for m in PiezoMode],
        help=(
            "ピエゾモーター制御モード。"
            f"選択肢: {', '.join(m.value for m in PiezoMode)} "
            f"（デフォルト: {PiezoMode.PAMC204.value}）"
        ),
    )
    parser.add_argument(
        "--port",
        metavar="PORT",
        default=None,
        help=(
            "PAMC-104 のシリアルポートを指定する（例: COM3, /dev/ttyUSB0）。"
            "--mode pamc104 のときのみ有効。省略時は GUI で選択。"
        ),
    )
    args = parser.parse_args()

    try:
        mode = PiezoMode.from_str(args.mode)
    except ValueError as e:
        parser.error(str(e))

    app = ADCGUI(dll_path=args.dll, mode=mode, port=args.port)
    app.mainloop()


if __name__ == "__main__":
    main()

