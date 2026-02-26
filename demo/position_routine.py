"""
ポジションルーティンスレッド
事前定義された位置を順番に移動し、各位置で ADC 収束を待つ。
"""
import threading
import time

import tkinter as tk

from .adc_thread import ADCControlThread


class PositionRoutineThread(threading.Thread):
    """事前定義された位置を順番に移動するスレッド。"""

    # 定義位置: (alnx, alny, hold_time[s])
    POSITIONS = [
        (7.0,  -7.0, 2.0),
        (-7.0, -7.0, 2.0),
        (-7.0,  7.0, 2.0),
        (7.0,   7.0, 2.0),
        (0.0,   0.0, 0.0),  # 原点復帰（ホールドなし）
    ]

    def __init__(self, master):
        super().__init__()
        self.daemon = True
        self.master = master
        self.running = False

    def run(self) -> None:
        self.running = True
        self.master.position_routine_running = True

        try:
            for i, (target_x, target_y, hold_time) in enumerate(self.POSITIONS, 1):
                if not self.running:
                    break

                print(f"Position Routine: Moving to position {i} - ({target_x}, {target_y})")

                try:
                    convergence_threshold = float(self.master.ADC_convergence_threshold_var.get())
                except Exception:
                    convergence_threshold = 0.01

                # ADC ターゲットを更新
                self.master.ADC_target_x = target_x
                self.master.ADC_target_y = target_y
                self.master.after(0, self.master.update_target_reticle)

                # ADC が未起動なら起動する
                if not self.master.ADC_active:
                    if not self._start_adc(convergence_threshold):
                        break

                # 収束待ち
                converged = self._wait_for_convergence(target_x, target_y, convergence_threshold)
                if not converged:
                    self._log_convergence_failure(target_x, target_y)

                # ホールド
                if hold_time > 0:
                    print(f"Position Routine: Maintaining position ({target_x}, {target_y}) for {hold_time}s")
                    self._hold(hold_time)
                else:
                    print("Position Routine: Moving to final position (0, 0)")
                    time.sleep(1.0)

            print("Position Routine: Complete. Stopping ADC.")
            if self.master.ADC_active:
                self.master.after(0, self.master.stop_ADC)

        except Exception as e:
            print(f"Error in position routine: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.master.position_routine_running = False
            self.running = False
            print("Position Routine thread finished")

    def _start_adc(self, convergence_threshold: float) -> bool:
        """ADC を起動する。失敗時は False を返す。"""
        try:
            sample_period      = float(self.master.ADC_period_var.get())
            learning_rate      = float(self.master.ADC_lr_var.get())
            min_step           = int(self.master.ADC_min_step_var.get())
            max_step           = int(self.master.ADC_max_step_var.get())
            pulses_per_unit    = float(self.master.ADC_pulses_per_unit_var.get())
            convergence_threshold = float(self.master.ADC_convergence_threshold_var.get())
            if pulses_per_unit <= 0:
                raise ValueError("Piezo calibration factor must be positive")
            if convergence_threshold < 0:
                raise ValueError("Convergence threshold must be non-negative")
        except ValueError as e:
            print(f"Error: Invalid ADC parameters: {e}")
            return False

        if not hasattr(self.master, "ADC_worker") or not self.master.ADC_worker or not self.master.ADC_worker.running:
            worker = ADCControlThread(self.master, sample_period=sample_period)
            worker.learning_rate_x       = learning_rate
            worker.learning_rate_y       = learning_rate
            worker.min_step_pulses       = min_step
            worker.max_step_pulses       = max_step
            worker.pulses_per_unit       = pulses_per_unit
            worker.convergence_threshold = convergence_threshold
            self.master.ADC_worker = worker
            self.master.ADC_active = True
            worker.start()

            self.master.after(0, lambda: self.master.ADC_start_btn.config(state=tk.DISABLED))
            self.master.after(0, lambda: self.master.ADC_stop_btn.config(state=tk.NORMAL))
            self.master.after(0, lambda: self.master.ADC_status_label.config(text="ADC: Active", fg="green"))
            print("ADC control started for position routine")
        return True

    def _wait_for_convergence(self, target_x: float, target_y: float, threshold: float) -> bool:
        """ADC が収束するまで最大 30 秒待つ。"""
        print(f"Position Routine: Waiting for convergence to ({target_x}, {target_y})")
        max_wait = 30.0
        start = time.time()

        while (time.time() - start) < max_wait:
            if not self.running:
                return False
            cx = self.master.alnx_smooth if self.master.smoothing_enabled else self.master.alnx
            cy = self.master.alny_smooth if self.master.smoothing_enabled else self.master.alny
            if abs(cx - target_x) <= threshold and abs(cy - target_y) <= threshold:
                print(f"Position Routine: Converged to ({target_x}, {target_y})")
                return True
            time.sleep(0.1)
        return False

    def _log_convergence_failure(self, target_x: float, target_y: float) -> None:
        cx = self.master.alnx_smooth if self.master.smoothing_enabled else self.master.alnx
        cy = self.master.alny_smooth if self.master.smoothing_enabled else self.master.alny
        print(f"Position Routine: Warning - Did not fully converge to ({target_x}, {target_y})")
        print(f"  Current: ({cx:.4f}, {cy:.4f}), Errors: X={abs(cx - target_x):.4f}, Y={abs(cy - target_y):.4f}")

    def _hold(self, hold_time: float) -> None:
        """指定時間ホールドする（100ms ごとに停止チェック）。"""
        start = time.time()
        while (time.time() - start) < hold_time:
            if not self.running:
                break
            time.sleep(0.1)

    def stop(self) -> None:
        self.running = False
