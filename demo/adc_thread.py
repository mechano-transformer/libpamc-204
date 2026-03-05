"""
ADC 制御スレッド（自動ドリフト補正）
PAMC-204 を使って X/Y 軸を順次駆動し、オートコリメータの誤差をゼロに近づける。

PAMC-204 DLL は同時2軸駆動 API を持たないため、X軸 → Y軸 の順に順次駆動する。
X・Y 両軸の誤差はステップ開始時に一度だけ計算し、X 駆動後に再計算しない。
コマンド例:
  E011PR100  … アドレス01, 軸1, 相対+100パルス  (move_relative(1, 1, 100))
  E012PR-50  … アドレス01, 軸2, 相対-50パルス   (move_relative(1, 2, -50))

--- デバイス・実験系に合わせて調整するパラメータ ---
  ADC_LEARNING_RATE    : 補正ゲイン（0〜1）。大きいほど積極的に補正するが振動しやすい
  ADC_MIN_STEP_PULSES  : 最小補正パルス数。小さすぎると補正が細かすぎて収束しない
  ADC_MAX_STEP_PULSES  : 最大補正パルス数。大きすぎるとオーバーシュートする
  ADC_PULSES_PER_UNIT  : キャリブレーション値（1単位角度あたりのパルス数）
  ADC_CONVERGENCE_THR  : 収束判定閾値。この誤差以下では補正しない
  ADC_SAMPLE_PERIOD    : 制御ループ周期（秒）
"""
import threading
import time
import numpy as np

# ---------------------------------------------------------------------------
# デバイス・実験系に合わせて調整するパラメータ
# ---------------------------------------------------------------------------

# 補正ゲイン（0〜1）。大きいほど積極的に補正するが振動しやすい。
# 適応学習率: 実効ゲイン = ADC_LEARNING_RATE * clamp(|error| / 0.1, 0.1, 1.0)
ADC_LEARNING_RATE: float = 0.3

# 最小補正パルス数。計算値がこれより小さい場合はこの値に切り上げる。
ADC_MIN_STEP_PULSES: int = 1

# 最大補正パルス数（1ステップの上限）。大きすぎるとオーバーシュートする。
ADC_MAX_STEP_PULSES: int = 500

# キャリブレーション: 1000パルス = 2.74単位角度 → ~365 pulses/unit
# デバイスや取り付け条件が変わった場合はここを変更する。
ADC_PULSES_PER_UNIT: float = round(1000 / 2.74, 2)  # ~365

# 収束判定閾値（単位角度）。誤差がこの値以下なら補正しない。
ADC_CONVERGENCE_THR: float = 0.01

# 制御ループ周期（秒）。短くすると応答が速くなるが CPU 負荷が増える。
ADC_SAMPLE_PERIOD: float = 0.5

# ---------------------------------------------------------------------------


class ADCControlThread(threading.Thread):
    """PAMC-204 を使った自動ドリフト補正スレッド。"""

    def __init__(self, master, sample_period: float = ADC_SAMPLE_PERIOD):
        super().__init__()
        self.daemon = True
        self.master = master
        self.sample_period = float(sample_period)
        self.running = False
        self.paused = False

        # キャリブレーション
        self.pulses_per_unit: float = ADC_PULSES_PER_UNIT

        # 制御パラメータ（モジュール定数から初期化。GUI から上書き可能）
        self.learning_rate_x: float = ADC_LEARNING_RATE
        self.learning_rate_y: float = ADC_LEARNING_RATE
        self.min_step_pulses: int = ADC_MIN_STEP_PULSES
        self.max_step_pulses: int = ADC_MAX_STEP_PULSES
        self.convergence_threshold: float = ADC_CONVERGENCE_THR

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

    def _calc_pulses(self, error: float, learning_rate: float) -> int:
        """誤差からパルス数を計算する（適応学習率）。

        誤差が大きいほど学習率を大きく、小さいほど小さくする。
        adaptive_lr = learning_rate * clamp(|error| / 0.1, 0.1, 1.0)
        """
        adaptive_lr = learning_rate * min(1.0, max(0.1, abs(error) / 0.1))
        return -int(round(adaptive_lr * error * self.pulses_per_unit))

    def _apply_reverse(self, pulses: int, axis: int) -> int:
        """指定軸の反転設定を適用してパルス数を返す。"""
        if axis == 1 and self.master.reverse_axis1:
            return -pulses
        if axis == 2 and self.master.reverse_axis2:
            return -pulses
        return pulses

    def _clamp_pulses(self, error: float, pulses: int) -> int:
        """クランプ・最小ステップ適用（収束閾値以下なら 0 を返す）。"""
        if abs(error) <= self.convergence_threshold:
            return 0
        pulses = int(np.clip(pulses, -self.max_step_pulses, self.max_step_pulses))
        if abs(pulses) < self.min_step_pulses:
            pulses = self.min_step_pulses if pulses >= 0 else -self.min_step_pulses
        return pulses

    def _read_errors(self):
        """現在の角度誤差を返す。スムージング設定を反映する。"""
        current_x = self.master.alnx_smooth if self.master.smoothing_enabled else self.master.alnx
        current_y = self.master.alny_smooth if self.master.smoothing_enabled else self.master.alny
        return current_x - self.master.ADC_target_x, current_y - self.master.ADC_target_y

    def _control_step(self, iteration: int) -> None:
        """1ステップの ADC 制御を実行する（勾配降下法）。

        X・Y 両軸の誤差をステップ開始時に一度だけ計算し、
        X軸 → Y軸 の順に順次駆動する（settle_time なし）。
        収束閾値内に入ったら補正しない（オーバーシュート防止）。
        """
        pamc = self.master.pamc
        if not pamc.is_connected:
            print("ADC: PAMC-204 not connected")
            return

        # 軸割り当て（デフォルト: X→ch2, Y→ch1 / スワップ時: X→ch1, Y→ch2）
        if self.master.swap_axes:
            axis_x, axis_y = 1, 2
        else:
            axis_x, axis_y = 2, 1

        # ── X・Y 両軸の誤差を同時に計算 ──────────────────────────────────────
        error_x, error_y = self._read_errors()
        self.master.ADC_error_x = error_x
        self.master.ADC_error_y = error_y

        pulses_x = self._calc_pulses(error_x, self.learning_rate_x)
        pulses_x = self._apply_reverse(pulses_x, axis_x)
        pulses_x = self._clamp_pulses(error_x, pulses_x)

        pulses_y = self._calc_pulses(error_y, self.learning_rate_y)
        pulses_y = self._apply_reverse(pulses_y, axis_y)
        pulses_y = self._clamp_pulses(error_y, pulses_y)

        if pulses_x == 0 and pulses_y == 0:
            print(f"ADC Step {iteration}: X error={error_x:.4f}, Y error={error_y:.4f}, no correction needed")
        else:
            # ── X 軸補正 ──────────────────────────────────────────────────────
            if pulses_x != 0:
                print(f"ADC Step {iteration}: X error={error_x:.4f}, sending {pulses_x:+d} pulses to ch{axis_x}")
                finished = self._move_axis(axis_x, pulses_x)
                if finished:
                    self.master.ADC_total_pulses_x += pulses_x
                else:
                    print(f"ADC Step {iteration}: X move failed/timeout, skipping Y correction")
                    self.master.after(0, self.master.update_ADC_display)
                    return
            else:
                print(f"ADC Step {iteration}: X error={error_x:.4f}, no X correction needed")

            # ── Y 軸補正（X と同じステップで計算済みの誤差を使用）────────────
            if pulses_y != 0:
                print(f"ADC Step {iteration}: Y error={error_y:.4f}, sending {pulses_y:+d} pulses to ch{axis_y}")
                finished = self._move_axis(axis_y, pulses_y)
                if finished:
                    self.master.ADC_total_pulses_y += pulses_y
                else:
                    print(f"ADC Step {iteration}: Y move failed/timeout")
                    self.master.after(0, self.master.update_ADC_display)
                    return
            else:
                print(f"ADC Step {iteration}: Y error={error_y:.4f}, no Y correction needed")

        self.prev_error_x = error_x
        self.prev_error_y = error_y
        self.prev_pulses_x = pulses_x
        self.prev_pulses_y = pulses_y

        self.master.after(0, self.master.update_ADC_display)

    def _move_axis(self, channel: int, pulses: int) -> bool:
        """PAMC の指定チャンネルを相対移動させ、完了を待つ。

        Returns:
            bool: 移動完了（FIN 受信）なら True、失敗・タイムアウトなら False
        """
        pamc = self.master.pamc
        if not pamc.is_connected:
            print(f"[ADC] PAMC not connected, skip move ch{channel} {pulses:+d} pulses")
            return False

        print(f"[ADC] move_relative: channel={channel}, pulses={pulses:+d}")
        ok = pamc.move_relative(channel, pulses)
        if not ok:
            print(f"[ADC] move_relative failed: ch{channel} {pulses:+d} pulses")
            return False

        # 動作完了待ち
        finished = pamc.wait_for_stop(channel)
        if not finished:
            print(f"[ADC] wait_for_stop timeout: ch{channel} — skipping further corrections")
        return finished

    def stop(self) -> None:
        self.running = False
