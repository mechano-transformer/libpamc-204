"""
demo パッケージ
Autocollimator & Piezo Motor Alignment Demo の分割実装。

モジュール構成:
  pamc204_wrapper  - PAMC-204 DLL ラッパークラス（PAMC204）
  pamc104_wrapper  - PAMC-104 RS232C 直接通信ラッパークラス（PAMC104）
  ac_thread        - オートコリメータ読み取りスレッド
  adc_thread       - ADC 制御スレッド（自動ドリフト補正）
  position_routine - ポジションルーティンスレッド
  gui              - メイン GUI クラス（ADCGUI）・モード定義（PiezoMode）
  main             - エントリーポイント

起動方法:
  python -m demo                    # PAMC-204 DLL モード（デフォルト）
  python -m demo --mode pamc104     # PAMC-104 RS232C 直接通信モード
  python demo/main.py --mode pamc104
"""
from .pamc204_wrapper import PAMC204
from .pamc104_wrapper import PAMC104
from .ac_thread import AcThread
from .adc_thread import ADCControlThread
from .position_routine import PositionRoutineThread
from .gui import ADCGUI, PiezoMode

__all__ = [
    "PAMC204",
    "PAMC104",
    "AcThread",
    "ADCControlThread",
    "PositionRoutineThread",
    "ADCGUI",
    "PiezoMode",
]
