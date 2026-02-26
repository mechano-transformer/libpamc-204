"""
エントリーポイント
Autocollimator & PAMC-204 Alignment Demo を起動する。

使い方:
    python -m demo                          # 自動検索（build/Release/pamc204.dll など）
    python -m demo --dll C:/path/to/pamc204.dll  # DLL パスを明示指定
    python demo/main.py --dll C:/path/to/pamc204.dll
"""
import sys
import os
import argparse

# スクリプトとして直接実行された場合、親ディレクトリを sys.path に追加する
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from demo.gui import ADCGUI


def main():
    parser = argparse.ArgumentParser(
        description="Autocollimator & PAMC-204 Alignment Demo"
    )
    parser.add_argument(
        "--dll",
        metavar="PATH",
        default=None,
        help="pamc204.dll のパスを明示指定する（省略時は自動検索）",
    )
    args = parser.parse_args()

    app = ADCGUI(dll_path=args.dll)
    app.mainloop()


if __name__ == "__main__":
    main()
