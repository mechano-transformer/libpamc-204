"""
ADC 制御スレッド（自動ドリフト補正）
PAMC-204 を使って X/Y 軸を順次駆動し、オートコリメータの誤差をゼロに近づける。

PAMC-204 は同時2軸駆動非対応のため、X軸 → Y軸 の順に順次駆動する。
コマンド例:
  E011PR100  … アドレス01, 軸1, 相対+100パルス  (move_relative(1, 1, 100))
  E012PR-50  … アドレス01, 軸2, 相対-50パルス   (move_relative(1, 2, -50))
"""
import threading
import time
import numpy as np


class ADCControlThread(threading.Thread):
    """PAMC-204 を使った自動ドリフト補正スレッド。"""

    def __init__(self, master, sample_period: float = 0.5):
        super().__init__()
        self.daemon = True
        self.master = master
        self.sample_period = float(sample_period)
        self.running = False
        self.paused = False

        # キャリブレーション: 1000パルス = 2.74単位角度
        self.pulses_per_unit: float = round(1000 / 2.74, 2)  # ~365 pulses/unit

        # 制御パラメータ
        self.learning_rate_x: float = 0.3
        self.learning_rate_y: float = 0.3
        self.min_step_pulses: int = 1
        self.max_step_pulses: int = 500
        self.convergence_threshold: float = 0.01

        self.prev_error_x: float = 0.0
        self.prev_error_y: float = 0.0
        self.prev_pulses_x: int = 0
        self.prev_pulses_y: int = 0

    def run(self) -> None:
        self.running = True
        iteration = 0
        print("ADC control thread started")

        while self.running:
            if not self.paused and self.master.ADC_active:
                try:
                    self._control_step(iteration)
                    iteration += 1
                except Exception as e:
                    print(f"ADC control error: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                if iteration % 10 == 0:
                    status = "paused" if self.paused else "inactive"
                    print(f"ADC thread running but {status} (ADC_active={self.master.ADC_active})")
            time.sleep(self.sample_period)

        print("ADC control thread stopped")

    def _control_step(self, iteration: int) -> None:
        """1ステップの ADC 制御を実行する（勾配降下法）。"""
        pamc = self.master.pamc
        if not pamc.is_connected:
            print("ADC: PAMC-204 not connected")
            return

        # 現在の角度誤差を計算
        current_x = self.master.alnx_smooth if self.master.smoothing_enabled else self.master.alnx
        current_y = self.master.alny_smooth if self.master.smoothing_enabled else self.master.alny
        error_x = current_x - self.master.ADC_target_x
        error_y = current_y - self.master.ADC_target_y

        self.master.ADC_error_x = error_x
        self.master.ADC_error_y = error_y

        # 適応ステップサイズ（誤差が大きいほど大きなステップ）
        adaptive_lr_x = self.learning_rate_x * min(1.0, max(0.1, abs(error_x) / 0.1))
        adaptive_lr_y = self.learning_rate_y * min(1.0, max(0.1, abs(error_y) / 0.1))

        pulses_x = -int(round(adaptive_lr_x * error_x * self.pulses_per_unit))
        pulses_y = -int(round(adaptive_lr_y * error_y * self.pulses_per_unit))

        # 軸割り当て（デフォルト: X→ch2, Y→ch1 / スワップ時: X→ch1, Y→ch2）
        if self.master.swap_axes:
            axis_x, axis_y = 1, 2
        else:
            axis_x, axis_y = 2, 1

        # 軸反転
        if axis_x == 1 and self.master.reverse_axis1:
            pulses_x = -pulses_x
        elif axis_x == 2 and self.master.reverse_axis2:
            pulses_x = -pulses_x

        if axis_y == 1 and self.master.reverse_axis1:
            pulses_y = -pulses_y
        elif axis_y == 2 and self.master.reverse_axis2:
            pulses_y = -pulses_y

        # クランプ
        pulses_x = int(np.clip(pulses_x, -self.max_step_pulses, self.max_step_pulses))
        pulses_y = int(np.clip(pulses_y, -self.max_step_pulses, self.max_step_pulses))

        # 最小ステップ適用（収束閾値以下なら補正なし）
        if abs(error_x) > self.convergence_threshold:
            if abs(pulses_x) < self.min_step_pulses:
                pulses_x = self.min_step_pulses if pulses_x >= 0 else -self.min_step_pulses
        else:
            pulses_x = 0

        if abs(error_y) > self.convergence_threshold:
            if abs(pulses_y) < self.min_step_pulses:
                pulses_y = self.min_step_pulses if pulses_y >= 0 else -self.min_step_pulses
        else:
            pulses_y = 0

        # PAMC-204 は同時2軸駆動非対応のため、X軸 → Y軸 の順に順次駆動
        if pulses_x != 0:
            print(f"ADC Step {iteration}: X error={error_x:.4f}, sending {pulses_x:+d} pulses to ch{axis_x}")
            self._move_axis(axis_x, pulses_x)
            self.master.ADC_total_pulses_x += pulses_x

        if pulses_y != 0:
            print(f"ADC Step {iteration}: Y error={error_y:.4f}, sending {pulses_y:+d} pulses to ch{axis_y}")
            self._move_axis(axis_y, pulses_y)
            self.master.ADC_total_pulses_y += pulses_y

        if pulses_x == 0 and pulses_y == 0:
            print(f"ADC Step {iteration}: X error={error_x:.4f}, Y error={error_y:.4f}, no correction needed")

        self.prev_error_x = error_x
        self.prev_error_y = error_y
        self.prev_pulses_x = pulses_x
        self.prev_pulses_y = pulses_y

        self.master.update_ADC_display()

    def _move_axis(self, channel: int, pulses: int) -> None:
        """PAMC-204 の指定チャンネルを相対移動させ、完了を待つ。

        コマンド: ExxmPRnnnn（例: E011PR100）
        """
        pamc = self.master.pamc
        if not pamc.is_connected:
            print(f"[ADC] PAMC-204 not connected, skip move ch{channel} {pulses:+d} pulses")
            return

        print(f"[ADC] move_relative: address={pamc.address}, channel={channel}, pulses={pulses:+d}")
        ok = pamc.move_relative(channel, pulses)
        if not ok:
            print(f"[ADC] move_relative failed: ch{channel} {pulses:+d} pulses")
            return

        # 動作完了待ち（ExxmMD? を送信して短時間待機）
        pamc.wait_for_stop(channel)

    def stop(self) -> None:
        self.running = False
