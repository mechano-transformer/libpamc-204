"""
メイン GUI クラス（PAMC-204 / PAMC-104/204 対応）
オートコリメータ読み取り・ピエゾモーター制御・ADC を統合した tkinter アプリ。

元の AC_Piezo_AutoAlign_Demo.py から分割・移植。
ピエゾモーター制御は mode 引数で切り替え:
  "pamc204"     : PAMC-204 DLL（pamc204_wrapper.py）を使用（デフォルト）
  "pamc104_204" : PAMC-104/204 send_command ベース（pamc104_204_wrapper.py）を使用
"""
import sys
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime
from enum import Enum

import serial
import serial.tools.list_ports

from .pamc204_wrapper import PAMC204
from .pamc104_wrapper import PAMC104
from .ac_thread import AcThread
from .adc_thread import ADCControlThread
from .position_routine import PositionRoutineThread


class PiezoMode(str, Enum):
    """ピエゾモーター制御モード。

    str を継承しているため argparse / 文字列比較と透過的に使用できる。
    """
    PAMC204 = "pamc204"  # PAMC-204 DLL 経由（デフォルト）
    PAMC104 = "pamc104"  # PAMC-104 RS232C 直接通信

    @classmethod
    def from_str(cls, value: str) -> "PiezoMode":
        """文字列から PiezoMode を返す。一致しない場合は ValueError。"""
        try:
            return cls(value.lower())
        except ValueError:
            valid = ", ".join(f'"{m.value}"' for m in cls)
            raise ValueError(f"Invalid mode: {value!r}. Choose from {valid}") from None

    @property
    def label(self) -> str:
        """GUI 表示用ラベル文字列。"""
        return "PAMC-104" if self is PiezoMode.PAMC104 else "PAMC-204"


class ADCGUI(tk.Tk):
    """オートコリメータ & ピエゾモーター アライメント GUI。

    Args:
        dll_path: pamc204.dll のパスを明示指定する場合に渡す。
                  None の場合は自動検索（build/Release/pamc204.dll など）。
        mode:     ピエゾモーター制御モード（文字列または PiezoMode）。
                  "pamc204" … PAMC-204 DLL 経由（デフォルト）
                  "pamc104" … PAMC-104 RS232C 直接通信
        port:     PAMC-104 のシリアルポート名（例: "COM3", "/dev/ttyUSB0"）。
                  --mode pamc104 のときのみ有効。指定時は GUI の初期値に設定される。
                  None の場合は GUI で選択。
    """

    def __init__(self, dll_path: str | None = None, mode: str | PiezoMode = "pamc204",
                 port: str | None = None):
        super().__init__()
        self._dll_path = dll_path
        self._mode: PiezoMode = PiezoMode.from_str(str(mode)) if not isinstance(mode, PiezoMode) else mode
        self._initial_port: str | None = port  # --port 引数で指定されたポート

        # ── オートコリメータ ──────────────────────────────────────
        self.AC = serial.Serial(baudrate=38400, timeout=0.1, write_timeout=0.1)
        self.alnx: float = 0.0
        self.alny: float = 0.0
        self.alnx_smooth: float = 0.0
        self.alny_smooth: float = 0.0
        self.smoothing_enabled: bool = False
        self.smoothing_window: int = 5
        self.worker = None
        self.test_running: bool = False
        self.logged_data: list = []

        self.units = {
            "0": "min", "1": "deg", "2": "mdeg", "3": "urad",
            "min": "0", "deg": "1", "mdeg": "2", "urad": "3",
        }
        self.unitvalues = ["min", "deg", "mdeg", "urad"]
        self.current_unit = "mdeg"

        # ── ピエゾモーターコントローラー（モードで切り替え）────────
        if self._mode is PiezoMode.PAMC104:
            self.pamc = PAMC104(port=self._initial_port)
        else:
            self.pamc = PAMC204(address=1, dll_path=self._dll_path)

        # ── ADC 制御 ──────────────────────────────────────────────
        self.ADC_worker = None
        self.ADC_active: bool = False
        self.ADC_error_x: float = 0.0
        self.ADC_error_y: float = 0.0
        self.ADC_total_pulses_x: int = 0
        self.ADC_total_pulses_y: int = 0
        self.ADC_target_x: float = 0.0
        self.ADC_target_y: float = 0.0
        self.position_routine_running: bool = False

        # ── テスト・ロギング ──────────────────────────────────────
        self.test_start_time = None
        self.last_log_time = None
        self.logging_sample_period: float = 0.1

        # ── 軸設定 ────────────────────────────────────────────────
        self.reverse_axis1: bool = False
        self.reverse_axis2: bool = False
        self.swap_axes: bool = False

        # ── ウィンドウ設定 ────────────────────────────────────────
        self.title(f"Autocollimator & {self._mode.label} Alignment Demo")
        self.geometry("1400x800")
        # 起動時に最大化
        try:
            self.state("zoomed")   # Windows / macOS
        except tk.TclError:
            self.attributes("-zoomed", True)  # Linux (X11)

        # ── レイアウト ────────────────────────────────────────────
        main_container = tk.Frame(self)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.ac_frame = tk.LabelFrame(main_container, text="Autocollimator", padx=10, pady=10)
        self.ac_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        self._setup_autocollimator_tab()

        self.piezo_frame = tk.LabelFrame(
            main_container, text=f"{self._mode.label} Piezo Motor Control", padx=10, pady=10
        )
        self.piezo_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        self._setup_piezo_tab()

        self.ADC_frame = tk.LabelFrame(main_container, text="Automated Drift Correction (ADC)", padx=10, pady=10)
        self.ADC_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        self._setup_ADC_tab()

        logging_container = tk.Frame(self)
        logging_container.pack(fill=tk.X, padx=10, pady=5)
        self._setup_logging_tab(logging_container)

        self.protocol("WM_DELETE_WINDOW", self.safe_destroy)

        # --port 指定時は GUI 表示後に自動接続
        if self._initial_port and self._mode is PiezoMode.PAMC104:
            self.after(200, self._auto_connect_pamc104)

    # ================================================================
    # セットアップ
    # ================================================================

    def _setup_autocollimator_tab(self):
        select_frame = tk.Frame(self.ac_frame, padx=20, pady=10)
        ac_port_label = tk.Label(select_frame, text="Select Autocollimator COM Port:")

        port_row = tk.Frame(select_frame)
        self.port_select = ttk.Combobox(port_row, width=30)
        self.port_select.bind("<<ComboboxSelected>>", self._set_ac_port)
        position_routine_btn = tk.Button(
            port_row, text="Position Routine",
            command=self.start_position_routine, width=15,
        )

        refresh_btn = tk.Button(select_frame, text="Refresh Ports", command=self._refresh_ac_ports)

        units_frame = tk.Frame(self.ac_frame, padx=20, pady=10)
        units_label = tk.Label(units_frame, text="Units:")
        self.units_box = ttk.Combobox(units_frame, values=self.unitvalues, width=15)
        self.units_box.set(self.current_unit)
        self.units_box.bind("<<ComboboxSelected>>", self._set_units)

        control_frame = tk.Frame(self.ac_frame, padx=20, pady=10)
        start_btn = tk.Button(control_frame, text="Start Reading", command=self.start_reading, width=15)
        stop_btn  = tk.Button(control_frame, text="Stop Reading",  command=self.stop_reading,  width=15)

        smoothing_frame = tk.LabelFrame(self.ac_frame, text="Data Smoothing", padx=20, pady=10)
        self.smoothing_enabled_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            smoothing_frame, text="Enable Smoothing",
            variable=self.smoothing_enabled_var,
            command=self._update_smoothing_enabled,
        ).pack(anchor="w", pady=5)

        smoothing_input_frame = tk.Frame(smoothing_frame)
        smoothing_input_frame.pack(fill=tk.X, pady=5)
        tk.Label(smoothing_input_frame, text="Averaging Window:").pack(side=tk.LEFT, padx=5)
        self.smoothing_window_var = tk.StringVar(value="5")
        smoothing_window_entry = tk.Entry(smoothing_input_frame, textvariable=self.smoothing_window_var, width=10)
        smoothing_window_entry.pack(side=tk.LEFT, padx=5)
        smoothing_window_entry.bind("<KeyRelease>", self._update_smoothing_window)

        display_frame = tk.Frame(self.ac_frame, padx=20, pady=10)
        self.aln_canvas = tk.Canvas(display_frame, width=460, height=460, bg="black")
        self._draw_cross()
        self.xvar = self.aln_canvas.create_text(60, 330, anchor="w", text="X-Tilt: 0.0", fill="white", font=("Arial", 12))
        self.yvar = self.aln_canvas.create_text(60, 360, anchor="w", text="Y-Tilt: 0.0", fill="white", font=("Arial", 12))
        self.xline = self.aln_canvas.create_line(210, 230, 250, 230, fill="red",   width=3)
        self.yline = self.aln_canvas.create_line(230, 210, 230, 250, fill="red",   width=3)
        self.target_xline = self.aln_canvas.create_line(210, 230, 250, 230, fill="green", width=3)
        self.target_yline = self.aln_canvas.create_line(230, 210, 230, 250, fill="green", width=3)

        # pack
        select_frame.pack(fill=tk.X)
        ac_port_label.pack(anchor="w")
        port_row.pack(fill=tk.X, pady=5)
        self.port_select.pack(side=tk.LEFT, anchor="w")
        position_routine_btn.pack(side=tk.LEFT, padx=10)
        refresh_btn.pack(anchor="w", pady=5)

        units_frame.pack(fill=tk.X)
        units_label.pack(side=tk.LEFT, padx=5)
        self.units_box.pack(side=tk.LEFT, padx=5)

        control_frame.pack(fill=tk.X)
        start_btn.pack(side=tk.LEFT, padx=5)
        stop_btn.pack(side=tk.LEFT, padx=5)

        smoothing_frame.pack(fill=tk.X)

        display_frame.pack()
        self.aln_canvas.pack()

        self._refresh_ac_ports()

    def _setup_piezo_tab(self):
        """ピエゾモーター接続・手動操作パネル（モードで表示を切り替え）。"""
        lbl = self._mode.label

        # ── 接続 ──
        connect_frame = tk.LabelFrame(self.piezo_frame, text=f"{lbl} Connection", padx=10, pady=10)
        connect_frame.pack(pady=10, fill=tk.X)

        if self._mode is PiezoMode.PAMC104:
            # PAMC-104: シリアルポート選択（RS232C 直接通信）
            tk.Label(connect_frame, text="Serial Port:").pack(anchor="w", padx=5)
            port_row = tk.Frame(connect_frame)
            port_row.pack(fill=tk.X, pady=2)
            self.pamc104_port_select = ttk.Combobox(port_row, width=22)
            self.pamc104_port_select.pack(side=tk.LEFT, padx=5)
            tk.Button(port_row, text="Refresh", command=self._refresh_pamc104_ports, width=8).pack(side=tk.LEFT, padx=2)
            self._refresh_pamc104_ports()
        else:
            # PAMC-204: アドレス入力（DLL 経由）
            addr_row = tk.Frame(connect_frame)
            addr_row.pack(fill=tk.X, pady=2)
            tk.Label(addr_row, text="Address:").pack(side=tk.LEFT, padx=5)
            self.pamc_address_var = tk.StringVar(value="1")
            tk.Entry(addr_row, textvariable=self.pamc_address_var, width=5).pack(side=tk.LEFT, padx=5)

        btn_row = tk.Frame(connect_frame)
        btn_row.pack(fill=tk.X, pady=5)
        tk.Button(btn_row, text=f"Connect {lbl}", command=self._connect_pamc, width=20).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_row, text="Disconnect",      command=self._disconnect_pamc, width=12).pack(side=tk.LEFT, padx=5)

        self.pamc_status_label = tk.Label(connect_frame, text="Status: Not connected", fg="red")
        self.pamc_status_label.pack(anchor="w", pady=2)

        # ── 軸選択 ──
        axis_frame = tk.Frame(self.piezo_frame)
        axis_frame.pack(pady=10)
        self.axis_var = tk.IntVar(value=1)
        tk.Radiobutton(axis_frame, value=1, variable=self.axis_var, text="Axis 1").pack(side=tk.LEFT, padx=10)
        tk.Radiobutton(axis_frame, value=2, variable=self.axis_var, text="Axis 2").pack(side=tk.LEFT, padx=10)

        # ── 操作ボタン ──
        control_frame = tk.Frame(self.piezo_frame)
        control_frame.pack(pady=10)
        tk.Button(control_frame, text="Set Home",   command=self._click_set_home,  width=14).pack(pady=5)
        tk.Button(control_frame, text="Move (Rel)", command=self._click_move_rel,  width=14).pack(pady=5)
        tk.Button(control_frame, text="Move (Abs)", command=self._click_move_abs,  width=14).pack(pady=5)
        tk.Button(control_frame, text="Stop",       command=self._click_stop,      width=14).pack(pady=5)
        tk.Button(control_frame, text="Position?",  command=self._click_position,  width=14).pack(pady=5)

        # ── 入力値 ──
        entry_frame = tk.Frame(self.piezo_frame)
        entry_frame.pack(pady=10)
        tk.Label(entry_frame, text="Rel pulses:").pack(side=tk.LEFT, padx=5)
        self.txt_rel = tk.Entry(entry_frame, width=10)
        self.txt_rel.pack(side=tk.LEFT, padx=5)
        self.txt_rel.insert(tk.END, "100")

        tk.Label(entry_frame, text="Abs position:").pack(side=tk.LEFT, padx=5)
        self.txt_abs = tk.Entry(entry_frame, width=10)
        self.txt_abs.pack(side=tk.LEFT, padx=5)
        self.txt_abs.insert(tk.END, "0")

        # ── ステータス ──
        status_frame = tk.Frame(self.piezo_frame)
        status_frame.pack(pady=10)
        self.lbl_position = tk.Label(status_frame, text="Position: --", font=("Arial", 10))
        self.lbl_position.pack()
        self.lbl_status = tk.Label(status_frame, text="---------", font=("Arial", 9))
        self.lbl_status.pack()

        # ── 設定 ──
        config_frame = tk.LabelFrame(self.piezo_frame, text="Configuration", padx=10, pady=10)
        config_frame.pack(pady=10, fill=tk.X)

        self.reverse_axis1_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            config_frame, text="Reverse Axis 1",
            variable=self.reverse_axis1_var,
            command=self._update_reverse_axis1,
        ).pack(anchor="w", pady=5)

        self.reverse_axis2_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            config_frame, text="Reverse Axis 2",
            variable=self.reverse_axis2_var,
            command=self._update_reverse_axis2,
        ).pack(anchor="w", pady=5)

        self.swap_axes_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            config_frame, text="Swap X/Y Axes",
            variable=self.swap_axes_var,
            command=self._update_swap_axes,
        ).pack(anchor="w", pady=5)

    def _setup_ADC_tab(self):
        """ADC 制御パネル。"""
        ADC_control_frame = tk.Frame(self.ADC_frame)
        ADC_control_frame.pack(pady=10)

        self.ADC_start_btn = tk.Button(
            ADC_control_frame, text="Start ADC", command=self.start_ADC,
            width=15, height=2, bg="lightgreen",
        )
        self.ADC_stop_btn = tk.Button(
            ADC_control_frame, text="Stop ADC", command=self.stop_ADC,
            width=15, height=2, bg="lightcoral", state=tk.DISABLED,
        )
        self.ADC_start_btn.pack(pady=5)
        self.ADC_stop_btn.pack(pady=5)

        status_frame = tk.LabelFrame(self.ADC_frame, text="ADC Status", padx=10, pady=10)
        status_frame.pack(pady=10, fill=tk.X)
        self.ADC_status_label = tk.Label(status_frame, text="ADC: Inactive", font=("Arial", 12, "bold"))
        self.ADC_status_label.pack(pady=5)

        error_frame = tk.LabelFrame(self.ADC_frame, text="Current Errors", padx=10, pady=10)
        error_frame.pack(pady=10, fill=tk.X)
        self.error_x_label = tk.Label(error_frame, text="X Error: 0.0000", font=("Arial", 10))
        self.error_y_label = tk.Label(error_frame, text="Y Error: 0.0000", font=("Arial", 10))
        self.error_x_label.pack(pady=2)
        self.error_y_label.pack(pady=2)

        params_frame = tk.LabelFrame(self.ADC_frame, text="ADC Parameters", padx=10, pady=10)
        params_frame.pack(pady=10, fill=tk.X)

        def _row(label_text, default):
            tk.Label(params_frame, text=label_text).pack(anchor="w")
            v = tk.StringVar(value=default)
            tk.Entry(params_frame, textvariable=v, width=10).pack(anchor="w", pady=2)
            return v

        self.ADC_period_var                = _row("Sample Period (s):",               "0.5")
        self.ADC_lr_var                    = _row("Learning Rate:",                    "0.3")
        self.ADC_min_step_var              = _row("Min Step (pulses):",                "1")
        self.ADC_max_step_var              = _row("Max Step (pulses):",                "500")
        self.ADC_pulses_per_unit_var       = _row("Piezo Calibration (pulses/angle):", str(int(round(1000 / 2.74, 0))))
        self.ADC_convergence_threshold_var = _row("Convergence Threshold:",            "0.01")
        self.ADC_settle_time_var           = _row("Settle Time (s):",                  "0.2")

    def _setup_logging_tab(self, parent):
        logging_frame = tk.LabelFrame(parent, text="Data Logging", padx=10, pady=10)
        logging_frame.pack(fill=tk.X)

        test_frame = tk.Frame(logging_frame)
        test_frame.pack(side=tk.LEFT, padx=20, pady=10)
        self.start_test_btn = tk.Button(test_frame, text="Start Test",        command=self.start_test, width=15, height=2)
        self.stop_test_btn  = tk.Button(test_frame, text="Stop Test",         command=self.stop_test,  width=15, height=2, state=tk.DISABLED)
        self.save_data_btn  = tk.Button(test_frame, text="Save Data to File", command=self.save_data,  width=15, height=2)
        self.start_test_btn.pack(pady=5)
        self.stop_test_btn.pack(pady=5)
        self.save_data_btn.pack(pady=5)

        info_frame = tk.Frame(logging_frame)
        info_frame.pack(side=tk.LEFT, padx=20, pady=10)
        self.test_status_label = tk.Label(info_frame, text="Test Status: Not Running", font=("Arial", 12))
        self.data_count_label  = tk.Label(info_frame, text="Data Points: 0",           font=("Arial", 10))
        self.test_status_label.pack(pady=10)
        self.data_count_label.pack(pady=5)

        sample_frame = tk.Frame(logging_frame)
        sample_frame.pack(side=tk.LEFT, padx=20, pady=10)
        tk.Label(sample_frame, text="Sampling Frequency", font=("Arial", 10, "bold")).pack(pady=5)
        tk.Label(sample_frame, text="Sample Period (s):").pack(anchor="w", pady=(5, 0))
        self.logging_sample_period_var = tk.StringVar(value="0.1")
        tk.Entry(sample_frame, textvariable=self.logging_sample_period_var, width=10).pack(anchor="w", pady=2)

        self._update_data_count()

    # ================================================================
    # 描画ヘルパー
    # ================================================================

    def _draw_cross(self):
        self.aln_canvas.create_line(230,   0, 230, 460, fill="white", width=1)
        self.aln_canvas.create_line(  0, 230, 460, 230, fill="white", width=1)
        self.aln_canvas.create_oval(  0,   0, 460, 460, outline="white", width=1)
        self.aln_canvas.create_oval(115, 115, 345, 345, outline="white", width=1)

    # ================================================================
    # ポート操作
    # ================================================================

    def _refresh_ac_ports(self):
        ports = [str(p) for p in serial.tools.list_ports.comports()]
        self.port_select["values"] = ports

    def _refresh_pamc104_ports(self):
        """PAMC-104 用シリアルポート一覧を更新する。

        --port 引数で指定されたポートがあればそれを優先して初期値に設定する。
        """
        ports = [p.device for p in serial.tools.list_ports.comports()]
        if hasattr(self, "pamc104_port_select"):
            self.pamc104_port_select["values"] = ports
            current = self.pamc104_port_select.get()
            if not current:
                # --port 引数で指定されたポートを優先、なければ先頭ポート
                if self._initial_port:
                    self.pamc104_port_select.set(self._initial_port)
                elif ports:
                    self.pamc104_port_select.set(ports[0])

    def _open_port(self, device, com: str) -> bool:
        device.close()
        print(f"Trying to open port {com}")
        try:
            device.port = com
            device.open()
            print("Port opened successfully")
            return True
        except Exception as e:
            print(f"Port Error: {e}")
            return False

    def _set_ac_port(self, event=None):
        if not self.port_select.get():
            return
        port_name = self.port_select.get().split()[0]
        if self._open_port(self.AC, port_name):
            try:
                self.AC.write("GETUNIT\r\n".encode())
                output = self.AC.readline().decode("ascii").split(",")
                print(output)
                if len(output) > 1:
                    unit_code = output[1].strip()
                    if unit_code in self.units:
                        self.current_unit = self.units[unit_code]
                        self.units_box.set(self.current_unit)
            except Exception as e:
                print(f"Error reading units: {e}")

    def _set_units(self, event=None):
        if not self.units_box.get():
            return
        if self.worker and self.worker.running:
            self.stop_reading()
        try:
            if self.AC.is_open:
                unit_code = self.units[self.units_box.get()]
                self.AC.write(f"SETUNIT,{unit_code}\r\n".encode())
                response = self.AC.readline().decode("ascii")
                print(f"Units set: {response}")
                self.current_unit = self.units_box.get()
        except Exception as e:
            print(f"Error setting units: {e}")

    # ================================================================
    # PAMC 接続
    # ================================================================

    def _auto_connect_pamc104(self):
        """--port 引数で指定されたポートに自動接続する（GUI 表示後に呼ばれる）。

        PAMC-204 の connect() と同様に、self.pamc.connect() を呼ぶだけで接続する。
        self.pamc は __init__() で既に PAMC104(port=self._initial_port) として生成済み。
        """
        if not self._initial_port:
            return
        print(f"[PAMC104] Auto-connecting to {self._initial_port} ...")
        ok = self.pamc.connect()
        if ok:
            self.pamc_status_label.config(
                text=f"Status: Connected ({self._initial_port})", fg="green"
            )
            if hasattr(self, "pamc104_port_select"):
                self.pamc104_port_select.set(self._initial_port)
            print(f"[PAMC104] Auto-connected to {self._initial_port}")
        else:
            self.pamc_status_label.config(text="Status: Connection failed", fg="red")
            print(f"[PAMC104] Auto-connect failed on {self._initial_port}")

    def _connect_pamc(self):
        lbl = self._mode.label
        if self._mode is PiezoMode.PAMC104:
            # PAMC-104: GUI で選択されたポートを set_port() で設定してから connect()
            # PAMC-204 と同様に self.pamc.connect() を呼ぶだけ
            port = self.pamc104_port_select.get().strip() if hasattr(self, "pamc104_port_select") else ""
            if not port:
                messagebox.showerror("Error", "Please select a serial port for PAMC-104.")
                return
            self.pamc.set_port(port)
            ok = self.pamc.connect()
            if ok:
                self.pamc_status_label.config(text=f"Status: Connected ({port})", fg="green")
            else:
                self.pamc_status_label.config(text="Status: Connection failed", fg="red")
                messagebox.showerror("Error", f"PAMC-104 not found on {port}.")
        else:
            # PAMC-204: アドレス指定で DLL 経由接続
            try:
                address = int(self.pamc_address_var.get())
            except ValueError:
                messagebox.showerror("Error", f"Invalid {lbl} address.")
                return
            self.pamc = PAMC204(address=address, dll_path=self._dll_path)
            ok = self.pamc.connect()
            if ok:
                self.pamc_status_label.config(text=f"Status: Connected (addr={address})", fg="green")
            else:
                self.pamc_status_label.config(text="Status: Connection failed", fg="red")
                messagebox.showerror("Error", f"{lbl} not found at address {address}.")

    def _disconnect_pamc(self):
        self.pamc.disconnect()
        self.pamc_status_label.config(text="Status: Disconnected", fg="red")
        print(f"[{self._mode.label}] Disconnected")

    # ================================================================
    # ピエゾ手動操作
    # ================================================================

    def _click_set_home(self):
        if not self.pamc.is_connected:
            messagebox.showerror("Error", "Please connect to PAMC-204 first.")
            return
        ch = self.axis_var.get()
        ok = self.pamc.set_home_position(ch, 0)
        print(f"[PAMC204] set_home_position ch{ch}: {'OK' if ok else 'FAIL'}")

    def _click_move_rel(self):
        if not self.pamc.is_connected:
            messagebox.showerror("Error", "Please connect to PAMC-204 first.")
            return
        try:
            pulses = int(self.txt_rel.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid pulse count.")
            return
        ch = self.axis_var.get()
        # swap_axes が有効な場合は軸番号を入れ替える
        if self.swap_axes:
            ch = 2 if ch == 1 else 1
        if ch == 1 and self.reverse_axis1:
            pulses = -pulses
        elif ch == 2 and self.reverse_axis2:
            pulses = -pulses
        ok = self.pamc.move_relative(ch, pulses)
        print(f"[PAMC204] move_relative ch{ch} {pulses:+d}: {'OK' if ok else 'FAIL'}")
        if ok:
            # wait_for_stop を別スレッドで実行し GUI スレッドをブロックしない
            import threading
            def _wait_and_update():
                self.pamc.wait_for_stop(ch)
                self.after(0, self._click_position)
            threading.Thread(target=_wait_and_update, daemon=True).start()

    def _click_move_abs(self):
        if not self.pamc.is_connected:
            messagebox.showerror("Error", "Please connect to PAMC-204 first.")
            return
        try:
            pos = int(self.txt_abs.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid position value.")
            return
        ch = self.axis_var.get()
        # swap_axes が有効な場合は軸番号を入れ替える
        if self.swap_axes:
            ch = 2 if ch == 1 else 1
        ok = self.pamc.move_absolute(ch, pos)
        print(f"[PAMC204] move_absolute ch{ch} pos={pos}: {'OK' if ok else 'FAIL'}")
        if ok:
            # wait_for_stop を別スレッドで実行し GUI スレッドをブロックしない
            import threading
            def _wait_and_update():
                self.pamc.wait_for_stop(ch)
                self.after(0, self._click_position)
            threading.Thread(target=_wait_and_update, daemon=True).start()

    def _click_stop(self):
        if not self.pamc.is_connected:
            messagebox.showerror("Error", "Please connect to PAMC-204 first.")
            return
        ch = self.axis_var.get()
        ok = self.pamc.stop_motion(ch)
        print(f"[PAMC204] stop_motion ch{ch}: {'OK' if ok else 'FAIL'}")

    def _click_position(self):
        if not self.pamc.is_connected:
            messagebox.showerror("Error", "Please connect to PAMC-204 first.")
            return
        ch = self.axis_var.get()
        pos = self.pamc.query_actual_position(ch)
        if pos is not None:
            self.lbl_position.config(text=f"Position ch{ch}: {pos}")
            self.lbl_status.config(text=f"ch{ch} = {pos}")
            print(f"[PAMC204] query_actual_position ch{ch}: {pos}")
        else:
            self.lbl_position.config(text=f"Position ch{ch}: FAIL")
            self.lbl_status.config(text="query failed")
            print(f"[PAMC204] query_actual_position ch{ch} failed")

    # ================================================================
    # 表示更新
    # ================================================================

    def update_display(self):
        display_x = self.alnx_smooth if self.smoothing_enabled else self.alnx
        display_y = self.alny_smooth if self.smoothing_enabled else self.alny

        self.aln_canvas.itemconfig(self.xvar, text=f"X-Tilt: {display_x:.4f} {self.current_unit}")
        self.aln_canvas.itemconfig(self.yvar, text=f"Y-Tilt: {display_y:.4f} {self.current_unit}")

        scale = 9
        xo = display_x * scale
        yo = display_y * scale
        self.aln_canvas.coords(self.xline, 230 + xo - 20, 230 - yo, 230 + xo + 20, 230 - yo)
        self.aln_canvas.coords(self.yline, 230 + xo, 230 - yo - 20, 230 + xo, 230 - yo + 20)

    def update_target_reticle(self):
        scale = 9
        xo = self.ADC_target_x * scale
        yo = self.ADC_target_y * scale
        self.aln_canvas.coords(self.target_xline, 230 + xo - 20, 230 - yo, 230 + xo + 20, 230 - yo)
        self.aln_canvas.coords(self.target_yline, 230 + xo, 230 - yo - 20, 230 + xo, 230 - yo + 20)

    def update_ADC_display(self):
        self.error_x_label.config(text=f"X Error: {self.ADC_error_x:.4f} {self.current_unit}")
        self.error_y_label.config(text=f"Y Error: {self.ADC_error_y:.4f} {self.current_unit}")

    # ================================================================
    # 設定変更コールバック
    # ================================================================

    def _update_reverse_axis1(self):
        self.reverse_axis1 = self.reverse_axis1_var.get()
        print(f"Reverse Axis 1: {'Enabled' if self.reverse_axis1 else 'Disabled'}")

    def _update_reverse_axis2(self):
        self.reverse_axis2 = self.reverse_axis2_var.get()
        print(f"Reverse Axis 2: {'Enabled' if self.reverse_axis2 else 'Disabled'}")

    def _update_swap_axes(self):
        self.swap_axes = self.swap_axes_var.get()
        print(f"Swap axes: {'Enabled' if self.swap_axes else 'Disabled'}")

    def _update_smoothing_enabled(self):
        self.smoothing_enabled = self.smoothing_enabled_var.get()
        if self.worker:
            self.worker.x_buffer = []
            self.worker.y_buffer = []
        print(f"Smoothing: {'Enabled' if self.smoothing_enabled else 'Disabled'}")

    def _update_smoothing_window(self, event=None):
        try:
            window = max(1, min(100, int(self.smoothing_window_var.get())))
            self.smoothing_window = window
            self.smoothing_window_var.set(str(window))
            if self.worker:
                self.worker.x_buffer = []
                self.worker.y_buffer = []
            print(f"Smoothing window updated to {window} measurements")
        except ValueError:
            self.smoothing_window_var.set(str(self.smoothing_window))

    # ================================================================
    # オートコリメータ読み取り
    # ================================================================

    def start_reading(self):
        if not self.AC.is_open:
            messagebox.showerror("Error", "Please select and connect to an autocollimator port first.")
            return
        if not self.worker or not self.worker.running:
            self.worker = AcThread(self, sample_period=0.1)
            self.worker.start()
            print("Started reading from autocollimator")

    def stop_reading(self):
        if self.worker and self.worker.running:
            self.worker.stop()
            self.worker.join(timeout=1)
            print("Stopped reading from autocollimator")

    # ================================================================
    # ADC 制御
    # ================================================================

    def start_ADC(self):
        """ADC 制御ループを開始する。"""
        if not self.AC.is_open:
            messagebox.showerror("Error", "Please connect to autocollimator first.")
            return
        if not self.pamc.is_connected:
            messagebox.showerror("Error", f"Please connect to {self._mode.label} first.")
            return
        if not self.worker or not self.worker.running:
            messagebox.showerror("Error", "Please start reading from autocollimator first.")
            return

        try:
            sample_period         = float(self.ADC_period_var.get())
            learning_rate         = float(self.ADC_lr_var.get())
            min_step              = int(self.ADC_min_step_var.get())
            max_step              = int(self.ADC_max_step_var.get())
            pulses_per_unit       = float(self.ADC_pulses_per_unit_var.get())
            convergence_threshold = float(self.ADC_convergence_threshold_var.get())
            settle_time           = float(self.ADC_settle_time_var.get())
            if pulses_per_unit <= 0:
                raise ValueError("Piezo calibration factor must be positive")
            if convergence_threshold < 0:
                raise ValueError("Convergence threshold must be non-negative")
            if settle_time < 0:
                raise ValueError("Settle time must be non-negative")
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid ADC parameters: {e}")
            return

        # カウンタリセット
        self.ADC_total_pulses_x = 0
        self.ADC_total_pulses_y = 0

        if not self.ADC_worker or not self.ADC_worker.running:
            self.ADC_worker = ADCControlThread(self, sample_period=sample_period)
            self.ADC_worker.learning_rate_x       = learning_rate
            self.ADC_worker.learning_rate_y       = learning_rate
            self.ADC_worker.min_step_pulses       = min_step
            self.ADC_worker.max_step_pulses       = max_step
            self.ADC_worker.pulses_per_unit       = pulses_per_unit
            self.ADC_worker.convergence_threshold = convergence_threshold
            self.ADC_worker.settle_time           = settle_time
            self.ADC_active = True
            self.ADC_worker.start()

            self.ADC_start_btn.config(state=tk.DISABLED)
            self.ADC_stop_btn.config(state=tk.NORMAL)
            self.ADC_status_label.config(text="ADC: Active", fg="green")
            print("ADC control started")

    def stop_ADC(self):
        """ADC 制御ループを停止する。"""
        self.ADC_active = False
        if self.ADC_worker and self.ADC_worker.running:
            self.ADC_worker.stop()
            self.ADC_worker.join(timeout=2)

        self.ADC_start_btn.config(state=tk.NORMAL)
        self.ADC_stop_btn.config(state=tk.DISABLED)
        self.ADC_status_label.config(text="ADC: Inactive", fg="red")
        print("ADC control stopped")

    # ================================================================
    # ポジションルーティン
    # ================================================================

    def start_position_routine(self):
        """事前定義された位置を順番に移動するルーティンを開始する。"""
        if not self.AC.is_open:
            messagebox.showerror("Error", "Please connect to autocollimator first.")
            return
        if not self.pamc.is_connected:
            messagebox.showerror("Error", f"Please connect to {self._mode.label} first.")
            return
        if not self.worker or not self.worker.running:
            messagebox.showerror("Error", "Please start reading from autocollimator first.")
            return
        if self.position_routine_running:
            messagebox.showwarning("Warning", "Position routine is already running.")
            return

        self.position_routine_thread = PositionRoutineThread(self)
        self.position_routine_thread.start()
        print("Position routine started")

    # ================================================================
    # データロギング
    # ================================================================

    def start_test(self):
        if not self.AC.is_open:
            messagebox.showerror("Error", "Please connect to autocollimator first.")
            return
        if not self.worker or not self.worker.running:
            messagebox.showerror("Error", "Please start reading from autocollimator first.")
            return
        try:
            self.logging_sample_period = float(self.logging_sample_period_var.get())
            if self.logging_sample_period <= 0:
                raise ValueError("Sampling period must be positive")
        except ValueError:
            messagebox.showerror("Error", "Invalid sampling period. Please enter a positive number.")
            return

        self.test_running = True
        self.logged_data = []
        self.test_start_time = datetime.now()
        self.last_log_time = None
        self.start_test_btn.config(state=tk.DISABLED)
        self.stop_test_btn.config(state=tk.NORMAL)
        self.test_status_label.config(text="Test Status: Running", fg="green")
        print(f"Test started - logging data at {self.logging_sample_period} second intervals")

    def stop_test(self):
        self.test_running = False
        self.last_log_time = None
        self.start_test_btn.config(state=tk.NORMAL)
        self.stop_test_btn.config(state=tk.DISABLED)
        self.test_status_label.config(text="Test Status: Stopped", fg="red")
        print(f"Test stopped - {len(self.logged_data)} data points logged")

    def _update_data_count(self):
        self.data_count_label.config(text=f"Data Points: {len(self.logged_data)}")
        self.after(1000, self._update_data_count)

    def save_data(self):
        if not self.logged_data:
            messagebox.showwarning("Warning", "No data to save. Please run a test first.")
            return
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="Save Data File",
        )
        if filename:
            try:
                with open(filename, "w") as f:
                    f.write("Time(s)\talnx\talny\n")
                    for entry in self.logged_data:
                        f.write(f"{entry['elapsed_time']:.6f}\t{entry['alnx']:.6f}\t{entry['alny']:.6f}\n")
                messagebox.showinfo("Success", f"Data saved to {filename}")
                print(f"Data saved to {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save file: {e}")
                print(f"Error saving file: {e}")

    # ================================================================
    # 終了処理
    # ================================================================

    def safe_destroy(self):
        """全リソースを解放してアプリを終了する。"""
        print("Shutting down application...")

        for name, obj, stop_fn in [
            ("position routine",          getattr(self, "position_routine_thread", None), "stop"),
            ("ADC worker",                self.ADC_worker,                                "stop"),
            ("autocollimator worker",     self.worker,                                    "stop"),
        ]:
            try:
                if obj and getattr(obj, "running", False):
                    print(f"Stopping {name}...")
                    getattr(obj, stop_fn)()
                    obj.join(timeout=2)
                    if obj.is_alive():
                        print(f"Warning: {name} did not stop within timeout")
            except Exception as e:
                print(f"Error stopping {name}: {e}")

        # ADC フラグをリセット
        self.ADC_active = False

        for name, device in [("autocollimator", self.AC), ("piezo controller", None)]:
            try:
                if name == "autocollimator" and device and device.is_open:
                    print("Closing autocollimator connection...")
                    device.close()
                elif name == "piezo controller":
                    self.pamc.disconnect()
            except Exception as e:
                print(f"Error closing {name}: {e}")

        try:
            self.quit()
        except Exception as e:
            print(f"Error quitting mainloop: {e}")

        try:
            self.destroy()
        except Exception as e:
            print(f"Error destroying window: {e}")

        print("Application shutdown complete")
        sys.exit(0)