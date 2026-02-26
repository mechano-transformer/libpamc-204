"""
demo パッケージ
Autocollimator & PAMC-204 Alignment Demo の分割実装。

モジュール構成:
  pamc204_wrapper  - PAMC-204 DLL ラッパークラス
  ac_thread        - オートコリメータ読み取りスレッド
  adc_thread       - ADC 制御スレッド（自動ドリフト補正）
  position_routine - ポジションルーティンスレッド
  gui              - メイン GUI クラス（ADCGUI）
  main             - エントリーポイント

起動方法:
  python -m demo
  python demo/main.py
"""
from .pamc204_wrapper import PAMC204
from .ac_thread import AcThread
from .adc_thread import ADCControlThread
from .position_routine import PositionRoutineThread
from .gui import ADCGUI

__all__ = [
    "PAMC204",
    "AcThread",
    "ADCControlThread",
    "PositionRoutineThread",
    "ADCGUI",
]
