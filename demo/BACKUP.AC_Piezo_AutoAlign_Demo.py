import serial
import serial.tools.list_ports
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import time
import sys
import threading
from datetime import datetime
import numpy as np

""" Class for collecting data from autocollimator without blocking tk mainloop"""
class AcThread(threading.Thread):
    def __init__(self, master, sample_period=0.1):
        super().__init__()
        self.daemon = True  # Allow program to exit even if thread is running
        self.master = master
        self.sample_period = float(sample_period)
        self.running = False
        self.paused = False
        # Smoothing buffers
        self.x_buffer = []
        self.y_buffer = []

    def run(self):
        self.running = True
        while self.running:
            if not self.paused:
                self.read_ac_data()
            time.sleep(self.sample_period)

    def read_ac_data(self):
        try:
            if self.master.AC.is_open:
                self.master.AC.write("G\r\n".encode())
                output = str(self.master.AC.readline().decode("ascii")).split(",")
                try:
                    raw_x = float(output[2].strip())
                    self.master.alnx = raw_x
                    
                    # Apply smoothing if enabled
                    if self.master.smoothing_enabled:
                        self.x_buffer.append(raw_x)
                        window = self.master.smoothing_window
                        if len(self.x_buffer) > window:
                            self.x_buffer.pop(0)  # Keep only last 'window' measurements
                        self.master.alnx_smooth = sum(self.x_buffer) / len(self.x_buffer)
                    else:
                        self.master.alnx_smooth = raw_x
                        self.x_buffer = []  # Clear buffer when smoothing disabled
                except:
                    pass
                try:
                    raw_y = float(output[3].strip())
                    self.master.alny = raw_y
                    
                    # Apply smoothing if enabled
                    if self.master.smoothing_enabled:
                        self.y_buffer.append(raw_y)
                        window = self.master.smoothing_window
                        if len(self.y_buffer) > window:
                            self.y_buffer.pop(0)  # Keep only last 'window' measurements
                        self.master.alny_smooth = sum(self.y_buffer) / len(self.y_buffer)
                    else:
                        self.master.alny_smooth = raw_y
                        self.y_buffer = []  # Clear buffer when smoothing disabled
                except:
                    pass
                self.master.update_display()
                
                # Log data if test is running (only at specified sampling frequency)
                if self.master.test_running:
                    current_time = datetime.now()
                    # Check if enough time has passed since last log
                    if (self.master.last_log_time is None or 
                        (current_time - self.master.last_log_time).total_seconds() >= self.master.logging_sample_period):
                        # Calculate elapsed time in seconds from test start
                        elapsed_time = (current_time - self.master.test_start_time).total_seconds()
                        # Log smoothed values if smoothing is enabled, otherwise raw values
                        log_x = self.master.alnx_smooth if self.master.smoothing_enabled else self.master.alnx
                        log_y = self.master.alny_smooth if self.master.smoothing_enabled else self.master.alny
                        self.master.logged_data.append({
                            'elapsed_time': elapsed_time,
                            'alnx': log_x,
                            'alny': log_y
                        })
                        self.master.last_log_time = current_time
        except Exception as e:
            print(f"Error reading AC data: {e}")

    def stop(self):
        self.running = False


""" ADC Control Thread for drift correction using gradient dADCent """
class ADCControlThread(threading.Thread):
    def __init__(self, master, sample_period=0.5):
        super().__init__()
        self.daemon = True  # Allow program to exit even if thread is running
        self.master = master
        self.sample_period = float(sample_period)
        self.running = False
        self.paused = False
        
        # ADC Parameters
        # Calibration: 1000 pulses = 2.74 units of angle
        self.pulses_per_unit = round(1000 / 2.74, 2)  # ~365 pulses per unit
        
        # Autodrift parameters
        self.learning_rate_x = 0.3  # Adaptive step size for X axis
        self.learning_rate_y = 0.3  # Adaptive step size for Y axis
        self.min_step_pulses = 1  # Minimum step size in pulses
        self.max_step_pulses = 500  # Maximum step size in pulses
        self.convergence_threshold = 0.01  # Error threshold to consider converged
        
        # History for gradient estimation
        self.prev_error_x = 0.0
        self.prev_error_y = 0.0
        self.prev_pulses_x = 0
        self.prev_pulses_y = 0
        
        # ADC perturbation parameters
        self.perturb_amplitude = 2  # Small perturbation in pulses
        self.perturb_frequency = 0.5  # Hz
        self.perturb_phase_x = 0.0
        self.perturb_phase_y = np.pi / 2  # 90 deg phase shift for Y
        
    def run(self):
        self.running = True
        iteration = 0
        print("ADC control thread started")
        
        while self.running:
            if not self.paused and self.master.ADC_active:
                try:
                    self.ADC_control_step(iteration)
                    iteration += 1
                except Exception as e:
                    print(f"ADC control error: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                if iteration % 10 == 0:  # Print status every 10 skipped iterations
                    status = "paused" if self.paused else "inactive"
                    print(f"ADC thread running but {status} (ADC_active={self.master.ADC_active})")
            time.sleep(self.sample_period)
        
        print("ADC control thread stopped")
    
    def ADC_control_step(self, iteration):
        """Execute one step of ADC control for both axes using gradient dADCent"""
        if not self.master.AC.is_open:
            print("ADC: AC not connected")
            return
        if not self.master.ser or not self.master.ser.is_open:
            print("ADC: Piezo motor not connected")
            return
        
        # Get current angle measurements and calculate error from target position
        # Use smoothed values if smoothing is enabled, otherwise use raw values
        current_x = self.master.alnx_smooth if self.master.smoothing_enabled else self.master.alnx
        current_y = self.master.alny_smooth if self.master.smoothing_enabled else self.master.alny
        error_x = current_x - self.master.ADC_target_x
        error_y = current_y - self.master.ADC_target_y
        
        # Update master with current errors
        self.master.ADC_error_x = error_x
        self.master.ADC_error_y = error_y
        
        # Adaptive step size based on error magnitude
        # Larger errors -> larger steps, smaller errors -> smaller steps
        # This ensures discrete steps get smaller as error approaches zero
        adaptive_lr_x = self.learning_rate_x * min(1.0, max(0.1, abs(error_x) / 0.1))
        adaptive_lr_y = self.learning_rate_y * min(1.0, max(0.1, abs(error_y) / 0.1))
        
        # Simple gradient dADCent: move opposite to error direction
        # Convert angle error directly to pulses
        # Negative error means we need positive pulses (and vice versa)
        pulses_correction_x = -int(round(adaptive_lr_x * error_x * self.pulses_per_unit))
        pulses_correction_y = -int(round(adaptive_lr_y * error_y * self.pulses_per_unit))
        
        # Apply direction reversal based on axis assignment
        # Determine axis assignment based on swap_axes setting
        # Default: X uses axis 2, Y uses axis 1
        # Swapped: X uses axis 1, Y uses axis 2
        if self.master.swap_axes:
            axis_x = 1
            axis_y = 2
        else:
            axis_x = 2
            axis_y = 1
        
        # Apply reversal based on which axis is being used
        if axis_x == 1 and self.master.reverse_axis1:
            pulses_correction_x = -pulses_correction_x
        elif axis_x == 2 and self.master.reverse_axis2:
            pulses_correction_x = -pulses_correction_x
        
        if axis_y == 1 and self.master.reverse_axis1:
            pulses_correction_y = -pulses_correction_y
        elif axis_y == 2 and self.master.reverse_axis2:
            pulses_correction_y = -pulses_correction_y
        
        # Clamp to min/max step sizes
        pulses_correction_x = np.clip(pulses_correction_x, -self.max_step_pulses, self.max_step_pulses)
        pulses_correction_y = np.clip(pulses_correction_y, -self.max_step_pulses, self.max_step_pulses)
        
        # Ensure minimum step if error is significant (but allow zero if error is very small)
        if abs(error_x) > self.convergence_threshold:
            if abs(pulses_correction_x) < self.min_step_pulses:
                pulses_correction_x = self.min_step_pulses if pulses_correction_x >= 0 else -self.min_step_pulses
        else:
            pulses_correction_x = 0  # No correction if error is below threshold
        
        if abs(error_y) > self.convergence_threshold:
            if abs(pulses_correction_y) < self.min_step_pulses:
                pulses_correction_y = self.min_step_pulses if pulses_correction_y >= 0 else -self.min_step_pulses
        else:
            pulses_correction_y = 0  # No correction if error is below threshold
        
        # Send commands every sample period (combine X and Y if both need correction)
        # Note: axis assignment was already determined above for reversal logic
        
        if pulses_correction_x != 0 or pulses_correction_y != 0:
            # Combine both commands into one if both need correction
            if pulses_correction_x != 0 and pulses_correction_y != 0:
                print(f"ADC Step {iteration}: X error={error_x:.4f} ({pulses_correction_x} pulses), Y error={error_y:.4f} ({pulses_correction_y} pulses)")
                self.move_piezo_combined(axis_y, pulses_correction_y, axis_x, pulses_correction_x)
                self.master.ADC_total_pulses_x += pulses_correction_x
                self.master.ADC_total_pulses_y += pulses_correction_y
            elif pulses_correction_x != 0:
                print(f"ADC Step {iteration}: X error={error_x:.4f}, sending {pulses_correction_x} pulses")
                self.move_piezo_axis(axis_x, pulses_correction_x)
                self.master.ADC_total_pulses_x += pulses_correction_x
            elif pulses_correction_y != 0:
                print(f"ADC Step {iteration}: Y error={error_y:.4f}, sending {pulses_correction_y} pulses")
                self.move_piezo_axis(axis_y, pulses_correction_y)
                self.master.ADC_total_pulses_y += pulses_correction_y
        else:
            print(f"ADC Step {iteration}: X error={error_x:.4f}, Y error={error_y:.4f}, no correction needed")
        
        # Update history
        self.prev_error_x = error_x
        self.prev_error_y = error_y
        self.prev_pulses_x = pulses_correction_x
        self.prev_pulses_y = pulses_correction_y
        
        # Update display
        self.master.update_ADC_display()
    
    def move_piezo_combined(self, axis1, pulses1, axis2, pulses2):
        """Move both piezo motor axes simultaneously - format: M:W+direction1Ppulses1+direction2Ppulses2"""
        try:
            if self.master.ser is None or not self.master.ser.is_open:
                print("Piezo motor not connected")
                return
            
            # Format: M:W+direction1Ppulses1+direction2Ppulses2
            direction1 = '+' if pulses1 >= 0 else '-'
            direction2 = '+' if pulses2 >= 0 else '-'
            pulses1_abs = abs(pulses1)
            pulses2_abs = abs(pulses2)
            
            wdata = 'M:W' + direction1 + 'P' + str(pulses1_abs) + direction2 + 'P' + str(pulses2_abs) + '\r\n'
            print(f"ADC Move Combined: {wdata.strip()}")
            
            self.master.ser.write(wdata.encode())
            rdata = self.master.ser.readline()
            print(f"Response: {rdata}")

            wdata = 'G:\r\n'
            self.master.ser.write(wdata.encode())
            rtn = self.master.ser.readline()
            print(rtn)
            
            # Wait for motor to complete movement
            while True:
                wdata = '!:\r\n'
                self.master.ser.write(wdata.encode())
                status = self.master.ser.readline().decode().strip()
                if status == 'R':  # Ready
                    break
                elif status == 'B':  # Busy
                    time.sleep(0.1)  # Shorter delay for ADC
                else:
                    print(f"Unexpected status: {status}")
                    break
                    
        except Exception as e:
            print(f"Error moving piezo axes combined: {e}")
            import traceback
            traceback.print_exc()
    
    def move_piezo_axis(self, axis, pulses):
        """Move piezo motor axis by relative pulses - matches click_MoveRel format"""
        try:
            if self.master.ser is None or not self.master.ser.is_open:
                print("Piezo motor not connected")
                return
            
            # Format exactly like click_MoveRel: 'M:axis+directionPpulses\r\n'
            direction = '+' if pulses >= 0 else '-'
            pulses_abs = abs(pulses)
            axis_str = str(axis)
            wdata = 'M:' + axis_str + direction + 'P' + str(pulses_abs) + '\r\n'
            print(f"ADC Move: {wdata.strip()}")
            
            self.master.ser.write(wdata.encode())
            rdata = self.master.ser.readline()
            print(f"Response: {rdata}")

            wdata = 'G:\r\n'
            self.master.ser.write(wdata.encode())
            rtn = self.master.ser.readline()
            print(rtn)
            
            # Wait for motor to complete movement (same as click_MoveRel)
            while True:
                wdata = '!:\r\n'
                self.master.ser.write(wdata.encode())
                status = self.master.ser.readline().decode().strip()
                if status == 'R':  # Ready
                    break
                elif status == 'B':  # Busy
                    time.sleep(0.1)  # Shorter delay for ADC
                else:
                    print(f"Unexpected status: {status}")
                    break
                    
        except Exception as e:
            print(f"Error moving piezo axis {axis}: {e}")
            import traceback
            traceback.print_exc()
    
    def stop(self):
        self.running = False


""" Position Routine Thread for moving through predefined positions """
class PositionRoutineThread(threading.Thread):
    def __init__(self, master):
        super().__init__()
        self.daemon = True  # Allow program to exit even if thread is running
        self.master = master
        self.running = False
        
    def run(self):
        self.running = True
        self.master.position_routine_running = True
        
        try:
            # Define positions: (alnx, alny, hold_time)
            positions = [
                (7.0, -7.0, 2.0),   # Position 3: (5, -5) - hold for 2 seconds
                (-7.0, -7.0, 2.0),
                (-7.0, 7.0, 2.0),
                (7.0, 7.0, 2.0),
                (0.0, 0.0, 0.0)     # Position 5: (0, 0) - return home, no hold
            ]
            
            for i, (target_x, target_y, hold_time) in enumerate(positions, 1):
                if not self.running:
                    break
                    
                print(f"Position Routine: Moving to position {i} - ({target_x}, {target_y})")
                
                # Get ADC parameters (needed for convergence threshold)
                try:
                    convergence_threshold = float(self.master.ADC_convergence_threshold_var.get())
                except:
                    convergence_threshold = 0.01  # Default if not available
                
                # Set target position for ADC
                self.master.ADC_target_x = target_x
                self.master.ADC_target_y = target_y
                
                # Update green reticle to show target position
                self.master.after(0, self.master.update_target_reticle)
                
                # If ADC is not already running, start it
                if not self.master.ADC_active:
                    # Get ADC parameters from GUI
                    try:
                        sample_period = float(self.master.ADC_period_var.get())
                        learning_rate = float(self.master.ADC_lr_var.get())
                        min_step = int(self.master.ADC_min_step_var.get())
                        max_step = int(self.master.ADC_max_step_var.get())
                        pulses_per_unit = float(self.master.ADC_pulses_per_unit_var.get())
                        convergence_threshold = float(self.master.ADC_convergence_threshold_var.get())
                        
                        # Validate parameters
                        if pulses_per_unit <= 0:
                            raise ValueError("Piezo calibration factor must be positive")
                        if convergence_threshold < 0:
                            raise ValueError("Convergence threshold must be non-negative")
                    except ValueError as e:
                        print(f"Error: Invalid ADC parameters: {e}")
                        break
                    
                    # Create and start ADC worker
                    if not hasattr(self.master, "ADC_worker") or not self.master.ADC_worker or not self.master.ADC_worker.running:
                        self.master.ADC_worker = ADCControlThread(self.master, sample_period=sample_period)
                        self.master.ADC_worker.learning_rate_x = learning_rate
                        self.master.ADC_worker.learning_rate_y = learning_rate
                        self.master.ADC_worker.min_step_pulses = min_step
                        self.master.ADC_worker.max_step_pulses = max_step
                        self.master.ADC_worker.pulses_per_unit = pulses_per_unit
                        self.master.ADC_worker.convergence_threshold = convergence_threshold
                        self.master.ADC_active = True
                        self.master.ADC_worker.start()
                        
                        # Update GUI from main thread
                        self.master.after(0, lambda: self.master.ADC_start_btn.config(state=tk.DISABLED))
                        self.master.after(0, lambda: self.master.ADC_stop_btn.config(state=tk.NORMAL))
                        self.master.after(0, lambda: self.master.ADC_status_label.config(text="ADC: Active", fg="green"))
                        print("ADC control started for position routine")
                
                # Wait for ADC to converge to target position
                print(f"Position Routine: Waiting for convergence to ({target_x}, {target_y})")
                max_convergence_wait = 30.0  # Maximum 30 seconds to converge
                convergence_start = time.time()
                converged = False
                
                while (time.time() - convergence_start) < max_convergence_wait:
                    if not self.running:
                        break
                    
                    # Calculate current error (use smoothed values if smoothing enabled)
                    current_x = self.master.alnx_smooth if self.master.smoothing_enabled else self.master.alnx
                    current_y = self.master.alny_smooth if self.master.smoothing_enabled else self.master.alny
                    error_x = abs(current_x - target_x)
                    error_y = abs(current_y - target_y)
                    
                    # Check if converged (both axes within threshold)
                    if error_x <= convergence_threshold and error_y <= convergence_threshold:
                        converged = True
                        print(f"Position Routine: Converged to ({target_x}, {target_y}) - X error: {error_x:.4f}, Y error: {error_y:.4f}")
                        break
                    
                    time.sleep(0.1)  # Check every 100ms
                
                if not converged:
                    current_x = self.master.alnx_smooth if self.master.smoothing_enabled else self.master.alnx
                    current_y = self.master.alny_smooth if self.master.smoothing_enabled else self.master.alny
                    print(f"Position Routine: Warning - Did not fully converge to ({target_x}, {target_y}) within {max_convergence_wait}s")
                    print(f"  Current position: ({current_x:.4f}, {current_y:.4f})")
                    print(f"  Target position: ({target_x}, {target_y})")
                    print(f"  Errors: X={abs(current_x - target_x):.4f}, Y={abs(current_y - target_y):.4f}")
                
                # Now maintain position for the specified hold time
                if hold_time > 0:
                    print(f"Position Routine: Maintaining position ({target_x}, {target_y}) for {hold_time} seconds")
                    hold_start = time.time()
                    while (time.time() - hold_start) < hold_time:
                        if not self.running:
                            break
                        time.sleep(0.1)  # Check every 100ms
                else:
                    # For final position (0,0), just wait a moment for ADC to settle
                    print(f"Position Routine: Moving to final position (0, 0)")
                    time.sleep(1.0)  # Brief pause to allow movement
            
            # Stop ADC at the end
            print("Position Routine: Complete. Stopping ADC.")
            if self.master.ADC_active:
                # Stop ADC from main thread
                self.master.after(0, self.master.stop_ADC)
                
        except Exception as e:
            print(f"Error in position routine: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.master.position_routine_running = False
            self.running = False
            print("Position Routine thread finished")
    
    def stop(self):
        self.running = False


class ADCGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        
        # Autocollimator setup
        self.AC = serial.Serial(baudrate=38400, timeout=0.1, write_timeout=0.1)
        self.alnx = 0.0  # Raw X measurement
        self.alny = 0.0  # Raw Y measurement
        self.alnx_smooth = 0.0  # Smoothed X measurement
        self.alny_smooth = 0.0  # Smoothed Y measurement
        self.smoothing_enabled = False
        self.smoothing_window = 5  # Default number of measurements to average
        self.worker = None
        self.test_running = False
        self.logged_data = []
        
        self.units = {
            "0": "min",
            "1": "deg",
            "2": "mdeg",
            "3": "urad",
            "min": "0",
            "deg": "1",
            "mdeg": "2",
            "urad": "3"
        }
        self.unitvalues = ["min", "deg", "mdeg", "urad"]
        self.current_unit = "mdeg"
        
        # Piezo motor setup
        self.ser = None
        
        # ADC control setup
        self.ADC_worker = None
        self.ADC_active = False
        self.ADC_error_x = 0.0
        self.ADC_error_y = 0.0
        self.ADC_total_pulses_x = 0
        self.ADC_total_pulses_y = 0
        self.ADC_target_x = 0.0  # Target position for ADC (default: 0,0)
        self.ADC_target_y = 0.0
        self.position_routine_running = False
        
        # Test timing
        self.test_start_time = None
        self.last_log_time = None
        self.logging_sample_period = 0.1  # Default sampling period in seconds
        
        # ADC configuration options
        self.reverse_axis1 = False  # Reverse sign of pulse commands for Axis 1
        self.reverse_axis2 = False  # Reverse sign of pulse commands for Axis 2
        self.swap_axes = False  # Swap X/Y axis assignment
        
        self.title("Autocollimator & Piezo Motor Alignment Demo")
        self.geometry("1400x800")
        
        # Create main container frame
        main_container = tk.Frame(self)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left side - Autocollimator frame
        self.ac_frame = tk.LabelFrame(main_container, text="Autocollimator", padx=10, pady=10)
        self.ac_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        self.setup_autocollimator_tab()
        
        # Middle - Piezo Motor frame
        self.piezo_frame = tk.LabelFrame(main_container, text="Piezo Motor Control", padx=10, pady=10)
        self.piezo_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        self.setup_piezo_tab()
        
        # Right side - ADC Control frame
        self.ADC_frame = tk.LabelFrame(main_container, text="Automated Drift Correction (ADC)", padx=10, pady=10)
        self.ADC_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        self.setup_ADC_tab()
        
        # Data Logging section at the bottom
        logging_container = tk.Frame(self)
        logging_container.pack(fill=tk.X, padx=10, pady=5)
        self.setup_logging_tab(logging_container)
        
        self.protocol("WM_DELETE_WINDOW", self.safe_destroy)
    
    def setup_autocollimator_tab(self):
        # Port selection frame
        select_frame = tk.Frame(self.ac_frame, padx=20, pady=10)
        ac_port_label = tk.Label(select_frame, text="Select Autocollimator COM Port:")
        
        # Create a row frame for port selection and button
        port_row = tk.Frame(select_frame)
        self.port_select = ttk.Combobox(port_row, width=30)
        self.port_select.bind("<<ComboboxSelected>>", self.setACPort)
        position_routine_btn = tk.Button(port_row, text="Position Routine", 
                                        command=self.start_position_routine, width=15)
        
        refresh_btn = tk.Button(select_frame, text="Refresh Ports", command=self.refreshPorts)
        
        # Units selection
        units_frame = tk.Frame(self.ac_frame, padx=20, pady=10)
        units_label = tk.Label(units_frame, text="Units:")
        self.units_box = ttk.Combobox(units_frame, values=self.unitvalues, width=15)
        self.units_box.set(self.current_unit)
        self.units_box.bind("<<ComboboxSelected>>", self.setUnits)
        
        # Control buttons
        control_frame = tk.Frame(self.ac_frame, padx=20, pady=10)
        start_btn = tk.Button(control_frame, text="Start Reading", command=self.startReading, width=15)
        stop_btn = tk.Button(control_frame, text="Stop Reading", command=self.stopReading, width=15)
        
        # Smoothing control frame
        smoothing_frame = tk.LabelFrame(self.ac_frame, text="Data Smoothing", padx=20, pady=10)
        self.smoothing_enabled_var = tk.BooleanVar(value=False)
        smoothing_check = tk.Checkbutton(smoothing_frame, text="Enable Smoothing", 
                                         variable=self.smoothing_enabled_var,
                                         command=self.update_smoothing_enabled)
        smoothing_check.pack(anchor="w", pady=5)
        
        smoothing_input_frame = tk.Frame(smoothing_frame)
        smoothing_input_frame.pack(fill=tk.X, pady=5)
        tk.Label(smoothing_input_frame, text="Averaging Window:").pack(side=tk.LEFT, padx=5)
        self.smoothing_window_var = tk.StringVar(value="5")
        smoothing_window_entry = tk.Entry(smoothing_input_frame, textvariable=self.smoothing_window_var, width=10)
        smoothing_window_entry.pack(side=tk.LEFT, padx=5)
        smoothing_window_entry.bind("<KeyRelease>", self.update_smoothing_window)
        
        # Display canvas
        display_frame = tk.Frame(self.ac_frame, padx=20, pady=10)
        self.aln_canvas = tk.Canvas(display_frame, width=460, height=460, bg="black")
        self.drawCross()
        self.xvar = self.aln_canvas.create_text(60, 330, anchor="w", text="X-Tilt: " + str(self.alnx), fill="white", font=("Arial", 12))
        self.yvar = self.aln_canvas.create_text(60, 360, anchor="w", text="Y-Tilt: " + str(self.alny), fill="white", font=("Arial", 12))
        self.xline = self.aln_canvas.create_line(210, 230, 250, 230, fill="red", width=3)
        self.yline = self.aln_canvas.create_line(230, 210, 230, 250, fill="red", width=3)
        # Green reticle for target position (initially hidden at center)
        self.target_xline = self.aln_canvas.create_line(210, 230, 250, 230, fill="green", width=3)
        self.target_yline = self.aln_canvas.create_line(230, 210, 230, 250, fill="green", width=3)
        
        # Pack widgets
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
        
        self.refreshPorts()
    
    def setup_piezo_tab(self):
        # Port selection frame (similar to autocollimator)
        select_frame = tk.Frame(self.piezo_frame, padx=10, pady=10)
        select_frame.pack(pady=10, fill=tk.X)
        piezo_port_label = tk.Label(select_frame, text="Select Piezo Motor COM Port:")
        self.piezo_port_select = ttk.Combobox(select_frame, width=30)
        self.piezo_port_select.bind("<<ComboboxSelected>>", self.setPiezoPort)
        refresh_piezo_btn = tk.Button(select_frame, text="Refresh Ports", command=self.refreshPiezoPorts)
        
        piezo_port_label.pack(anchor="w")
        self.piezo_port_select.pack(anchor="w", pady=5)
        refresh_piezo_btn.pack(anchor="w", pady=5)
        
        self.refreshPiezoPorts()
        
        # Radio buttons for axis selection
        axis_frame = tk.Frame(self.piezo_frame)
        axis_frame.pack(pady=10)
        self.var = tk.IntVar()
        rdo1 = tk.Radiobutton(axis_frame, value=1, variable=self.var, text='Axis1')
        rdo2 = tk.Radiobutton(axis_frame, value=2, variable=self.var, text='Axis2')
        rdo3 = tk.Radiobutton(axis_frame, value=0, variable=self.var, text='All')
        rdo1.pack(side=tk.LEFT, padx=10)
        rdo2.pack(side=tk.LEFT, padx=10)
        rdo3.pack(side=tk.LEFT, padx=10)
        self.var.set(1)
        
        # Control buttons frame
        control_frame = tk.Frame(self.piezo_frame)
        control_frame.pack(pady=10)
        
        button2 = tk.Button(control_frame, text='Origin', command=self.click_Origin, width=12)
        button3 = tk.Button(control_frame, text='Move(Rel)', command=self.click_MoveRel, width=12)
        button4 = tk.Button(control_frame, text='Move(Abs)', command=self.click_MoveAbs, width=12)
        button7 = tk.Button(control_frame, text='Stop', command=self.click_Stop, width=12)
        button8 = tk.Button(control_frame, text='Position', command=self.click_Status, width=12)
        
        button2.pack(pady=5)
        button3.pack(pady=5)
        button4.pack(pady=5)
        button7.pack(pady=5)
        button8.pack(pady=5)
        
        # Text entry boxes frame
        entry_frame = tk.Frame(self.piezo_frame)
        entry_frame.pack(pady=10)
        tk.Label(entry_frame, text="Rel:").pack(side=tk.LEFT, padx=5)
        self.txt1 = tk.Entry(entry_frame, width=10)
        self.txt1.pack(side=tk.LEFT, padx=5)
        self.txt1.insert(tk.END, "100")
        
        tk.Label(entry_frame, text="Abs:").pack(side=tk.LEFT, padx=5)
        self.txt2 = tk.Entry(entry_frame, width=10)
        self.txt2.pack(side=tk.LEFT, padx=5)
        self.txt2.insert(tk.END, "0")
        
        # Position Label and Progress Bar
        status_frame = tk.Frame(self.piezo_frame)
        status_frame.pack(pady=10)
        
        self.lbl_position = tk.Label(status_frame, text='Position: 0', font=("Arial", 10))
        self.lbl_position.pack()
        
        self.progress_bar = tk.Scale(status_frame, from_=0, to=100, orient="horizontal", length=200, showvalue=False)
        self.progress_bar.pack(pady=5)
        
        # Status label
        self.lbl_status = tk.Label(status_frame, text='---------', font=("Arial", 9))
        self.lbl_status.pack()
        
        # Configuration options frame
        config_frame = tk.LabelFrame(self.piezo_frame, text="Configuration", padx=10, pady=10)
        config_frame.pack(pady=10, fill=tk.X)
        
        # Reverse direction checkboxes for each axis
        self.reverse_axis1_var = tk.BooleanVar(value=False)
        reverse_axis1_check = tk.Checkbutton(config_frame, text="Reverse Axis 1", 
                                             variable=self.reverse_axis1_var,
                                             command=self.update_reverse_axis1)
        reverse_axis1_check.pack(anchor="w", pady=5)
        
        self.reverse_axis2_var = tk.BooleanVar(value=False)
        reverse_axis2_check = tk.Checkbutton(config_frame, text="Reverse Axis 2", 
                                             variable=self.reverse_axis2_var,
                                             command=self.update_reverse_axis2)
        reverse_axis2_check.pack(anchor="w", pady=5)
        
        # Swap axes radio button
        self.swap_axes_var = tk.BooleanVar(value=False)
        swap_axes_check = tk.Checkbutton(config_frame, text="Swap X/Y Axes", 
                                        variable=self.swap_axes_var,
                                        command=self.update_swap_axes)
        swap_axes_check.pack(anchor="w", pady=5)
    
    def setup_ADC_tab(self):
        """Setup ADC control panel"""
        # ADC Control buttons
        ADC_control_frame = tk.Frame(self.ADC_frame)
        ADC_control_frame.pack(pady=10)
        
        self.ADC_start_btn = tk.Button(ADC_control_frame, text="Start ADC", command=self.start_ADC, 
                                       width=15, height=2, bg="lightgreen")
        self.ADC_stop_btn = tk.Button(ADC_control_frame, text="Stop ADC", command=self.stop_ADC, 
                                      width=15, height=2, bg="lightcoral", state=tk.DISABLED)
        
        self.ADC_start_btn.pack(pady=5)
        self.ADC_stop_btn.pack(pady=5)
        
        # ADC Status display
        status_frame = tk.LabelFrame(self.ADC_frame, text="ADC Status", padx=10, pady=10)
        status_frame.pack(pady=10, fill=tk.X)
        
        self.ADC_status_label = tk.Label(status_frame, text="ADC: Inactive", font=("Arial", 12, "bold"))
        self.ADC_status_label.pack(pady=5)
        
        # Error display
        error_frame = tk.LabelFrame(self.ADC_frame, text="Current Errors", padx=10, pady=10)
        error_frame.pack(pady=10, fill=tk.X)
        
        self.error_x_label = tk.Label(error_frame, text="X Error: 0.0000", font=("Arial", 10))
        self.error_y_label = tk.Label(error_frame, text="Y Error: 0.0000", font=("Arial", 10))
        self.error_x_label.pack(pady=2)
        self.error_y_label.pack(pady=2)
        
        # ADC Parameters frame
        params_frame = tk.LabelFrame(self.ADC_frame, text="ADC Parameters", padx=10, pady=10)
        params_frame.pack(pady=10, fill=tk.X)
        
        tk.Label(params_frame, text="Sample Period (s):").pack(anchor="w")
        self.ADC_period_var = tk.StringVar(value="0.02")
        ADC_period_entry = tk.Entry(params_frame, textvariable=self.ADC_period_var, width=10)
        ADC_period_entry.pack(anchor="w", pady=2)
        
        tk.Label(params_frame, text="Learning Rate:").pack(anchor="w", pady=(5,0))
        self.ADC_lr_var = tk.StringVar(value="0.8")
        ADC_lr_entry = tk.Entry(params_frame, textvariable=self.ADC_lr_var, width=10)
        ADC_lr_entry.pack(anchor="w", pady=2)
        
        tk.Label(params_frame, text="Min Step (pulses):").pack(anchor="w", pady=(5,0))
        self.ADC_min_step_var = tk.StringVar(value="10")
        ADC_min_entry = tk.Entry(params_frame, textvariable=self.ADC_min_step_var, width=10)
        ADC_min_entry.pack(anchor="w", pady=2)
        
        tk.Label(params_frame, text="Max Step (pulses):").pack(anchor="w", pady=(5,0))
        self.ADC_max_step_var = tk.StringVar(value="4000")
        ADC_max_entry = tk.Entry(params_frame, textvariable=self.ADC_max_step_var, width=10)
        ADC_max_entry.pack(anchor="w", pady=2)
        
        tk.Label(params_frame, text="Piezo Calibration Factor (pulses/angle):").pack(anchor="w", pady=(5,0))
        self.ADC_pulses_per_unit_var = tk.StringVar(value=str(int(round(1000 / 2.74, 0))))
        ADC_pulses_per_unit_entry = tk.Entry(params_frame, textvariable=self.ADC_pulses_per_unit_var, width=10)
        ADC_pulses_per_unit_entry.pack(anchor="w", pady=2)
        
        tk.Label(params_frame, text="Convergence Threshold:").pack(anchor="w", pady=(5,0))
        self.ADC_convergence_threshold_var = tk.StringVar(value="0.01")
        ADC_convergence_threshold_entry = tk.Entry(params_frame, textvariable=self.ADC_convergence_threshold_var, width=10)
        ADC_convergence_threshold_entry.pack(anchor="w", pady=2)
    
    def setup_logging_tab(self, parent):
        # Create a labeled frame for data logging
        logging_frame = tk.LabelFrame(parent, text="Data Logging", padx=10, pady=10)
        logging_frame.pack(fill=tk.X)
        
        # Test control frame
        test_frame = tk.Frame(logging_frame)
        test_frame.pack(side=tk.LEFT, padx=20, pady=10)
        
        self.start_test_btn = tk.Button(test_frame, text="Start Test", command=self.start_test, width=15, height=2)
        self.stop_test_btn = tk.Button(test_frame, text="Stop Test", command=self.stop_test, width=15, height=2, state=tk.DISABLED)
        self.save_data_btn = tk.Button(test_frame, text="Save Data to File", command=self.save_data, width=15, height=2)
        
        self.start_test_btn.pack(pady=5)
        self.stop_test_btn.pack(pady=5)
        self.save_data_btn.pack(pady=5)
        
        # Status and info frame
        info_frame = tk.Frame(logging_frame)
        info_frame.pack(side=tk.LEFT, padx=20, pady=10)
        
        self.test_status_label = tk.Label(info_frame, text="Test Status: Not Running", font=("Arial", 12))
        self.data_count_label = tk.Label(info_frame, text="Data Points: 0", font=("Arial", 10))
        
        self.test_status_label.pack(pady=10)
        self.data_count_label.pack(pady=5)
        
        # Sampling frequency control frame
        sample_frame = tk.Frame(logging_frame)
        sample_frame.pack(side=tk.LEFT, padx=20, pady=10)
        
        tk.Label(sample_frame, text="Sampling Frequency", font=("Arial", 10, "bold")).pack(pady=5)
        tk.Label(sample_frame, text="Sample Period (s):").pack(anchor="w", pady=(5,0))
        self.logging_sample_period_var = tk.StringVar(value="0.1")
        sample_period_entry = tk.Entry(sample_frame, textvariable=self.logging_sample_period_var, width=10)
        sample_period_entry.pack(anchor="w", pady=2)
        
        # Update data count periodically
        self.update_data_count()
    
    def drawCross(self):
        self.aln_canvas.create_line(230, 0, 230, 460, fill="white", width=1)
        self.aln_canvas.create_line(0, 230, 460, 230, fill="white", width=1)
        self.aln_canvas.create_oval(0, 0, 460, 460, outline="white", width=1)
        self.aln_canvas.create_oval(115, 115, 345, 345, outline="white", width=1)
    
    def refreshPorts(self):
        portList = [str(port) for port in serial.tools.list_ports.comports()]
        self.port_select["values"] = portList
    
    def refreshPiezoPorts(self):
        portList = [str(port) for port in serial.tools.list_ports.comports()]
        self.piezo_port_select["values"] = portList
    
    def openPort(self, device, com):
        device.close()
        print("Trying to open port " + com)
        try:
            device.port = com
            device.open()
            print("Port opened successfully")
            return True
        except Exception as e:
            print(f"Port Error: {e}")
            return False
    
    def setACPort(self, event=None):
        if self.port_select.get():
            port_name = self.port_select.get().split()[0]
            if self.openPort(self.AC, port_name):
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
    
    def setPiezoPort(self, event=None):
        if self.piezo_port_select.get():
            port_name = self.piezo_port_select.get().split()[0]
            # Create serial connection for piezo motor
            try:
                if self.ser and self.ser.is_open:
                    self.ser.close()
                self.ser = serial.Serial(port_name)
                self.ser.baudrate = 38400
                self.ser.bytesize = serial.EIGHTBITS
                self.ser.parity = serial.PARITY_NONE
                self.ser.stopbits = serial.STOPBITS_ONE
                self.ser.timeout = 5
                self.ser.rtscts = True
                print(f"Piezo motor connected to {port_name}")
            except Exception as e:
                print(f"Error connecting to piezo motor: {e}")
                messagebox.showerror("Error", f"Failed to connect to piezo motor: {e}")
    
    def setUnits(self, event=None):
        if self.units_box.get():
            if hasattr(self, "worker") and self.worker and self.worker.running:
                self.stopReading()
            try:
                if self.AC.is_open:
                    unit_code = self.units[self.units_box.get()]
                    self.AC.write(("SETUNIT," + unit_code + "\r\n").encode())
                    response = self.AC.readline().decode("ascii")
                    print(f"Units set: {response}")
                    self.current_unit = self.units_box.get()
            except Exception as e:
                print(f"Error setting units: {e}")
    
    def update_display(self):
        # Use smoothed values if smoothing is enabled, otherwise use raw values
        display_x = self.alnx_smooth if self.smoothing_enabled else self.alnx
        display_y = self.alny_smooth if self.smoothing_enabled else self.alny
        
        self.aln_canvas.itemconfig(self.xvar, text=f"X-Tilt: {display_x:.4f} {self.current_unit}")
        self.aln_canvas.itemconfig(self.yvar, text=f"Y-Tilt: {display_y:.4f} {self.current_unit}")
        scale = 9
        x_offset = display_x * scale
        y_offset = display_y * scale
        self.aln_canvas.coords(self.xline, 
                            230 + x_offset - 20, 230 - y_offset,
                            230 + x_offset + 20, 230 - y_offset)
        self.aln_canvas.coords(self.yline,
                            230 + x_offset, 230 - y_offset - 20,
                            230 + x_offset, 230 - y_offset + 20)
    
    def update_target_reticle(self):
        """Update the green reticle to show the target position"""
        scale = 9
        x_offset = self.ADC_target_x * scale
        y_offset = self.ADC_target_y * scale
        self.aln_canvas.coords(self.target_xline, 
                            230 + x_offset - 20, 230 - y_offset,
                            230 + x_offset + 20, 230 - y_offset)
        self.aln_canvas.coords(self.target_yline,
                            230 + x_offset, 230 - y_offset - 20,
                            230 + x_offset, 230 - y_offset + 20)
    
    def update_ADC_display(self):
        """Update ADC status display"""
        self.error_x_label.config(text=f"X Error: {self.ADC_error_x:.4f} {self.current_unit}")
        self.error_y_label.config(text=f"Y Error: {self.ADC_error_y:.4f} {self.current_unit}")
    
    def update_reverse_axis1(self):
        """Update reverse direction setting for Axis 1"""
        self.reverse_axis1 = self.reverse_axis1_var.get()
        print(f"Reverse Axis 1: {'Enabled' if self.reverse_axis1 else 'Disabled'}")
    
    def update_reverse_axis2(self):
        """Update reverse direction setting for Axis 2"""
        self.reverse_axis2 = self.reverse_axis2_var.get()
        print(f"Reverse Axis 2: {'Enabled' if self.reverse_axis2 else 'Disabled'}")
    
    def update_swap_axes(self):
        """Update swap axes setting"""
        self.swap_axes = self.swap_axes_var.get()
        print(f"Swap axes: {'Enabled' if self.swap_axes else 'Disabled'}")
    
    def update_smoothing_enabled(self):
        """Update smoothing enabled setting"""
        self.smoothing_enabled = self.smoothing_enabled_var.get()
        # Clear buffers when toggling
        if hasattr(self, "worker") and self.worker:
            if hasattr(self.worker, "x_buffer"):
                self.worker.x_buffer = []
                self.worker.y_buffer = []
        print(f"Smoothing: {'Enabled' if self.smoothing_enabled else 'Disabled'}")
    
    def update_smoothing_window(self, event=None):
        """Update smoothing window size"""
        try:
            window = int(self.smoothing_window_var.get())
            if window < 1:
                window = 1
            elif window > 100:
                window = 100
            self.smoothing_window = window
            self.smoothing_window_var.set(str(window))
            # Clear buffers when window size changes
            if hasattr(self, "worker") and self.worker:
                if hasattr(self.worker, "x_buffer"):
                    self.worker.x_buffer = []
                    self.worker.y_buffer = []
            print(f"Smoothing window updated to {window} measurements")
        except ValueError:
            # Invalid input, revert to current value
            self.smoothing_window_var.set(str(self.smoothing_window))
    
    def startReading(self):
        if not self.AC.is_open:
            messagebox.showerror("Error", "Please select and connect to an autocollimator port first.")
            return
        
        if not hasattr(self, "worker") or not self.worker or not self.worker.running:
            self.worker = AcThread(self, sample_period=0.1)
            self.worker.start()
            print("Started reading from autocollimator")
    
    def stopReading(self):
        if hasattr(self, "worker") and self.worker and self.worker.running:
            self.worker.stop()
            self.worker.join(timeout=1)
            print("Stopped reading from autocollimator")
    
    def start_ADC(self):
        """Start ADC control loop"""
        if not self.AC.is_open:
            messagebox.showerror("Error", "Please connect to autocollimator first.")
            return
        
        if not self.ser or not self.ser.is_open:
            messagebox.showerror("Error", "Please connect to piezo motor first.")
            return
        
        if not hasattr(self, "worker") or not self.worker or not self.worker.running:
            messagebox.showerror("Error", "Please start reading from autocollimator first.")
            return
        
        # Get ADC parameters from GUI
        try:
            sample_period = float(self.ADC_period_var.get())
            learning_rate = float(self.ADC_lr_var.get())
            min_step = int(self.ADC_min_step_var.get())
            max_step = int(self.ADC_max_step_var.get())
            pulses_per_unit = float(self.ADC_pulses_per_unit_var.get())
            convergence_threshold = float(self.ADC_convergence_threshold_var.get())
            
            # Validate parameters
            if pulses_per_unit <= 0:
                raise ValueError("Piezo calibration factor must be positive")
            if convergence_threshold < 0:
                raise ValueError("Convergence threshold must be non-negative")
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid ADC parameters: {e}")
            return
        
        # Reset counters
        self.ADC_total_pulses_x = 0
        self.ADC_total_pulses_y = 0
        
        # Create and start ADC worker
        if not hasattr(self, "ADC_worker") or not self.ADC_worker or not self.ADC_worker.running:
            self.ADC_worker = ADCControlThread(self, sample_period=sample_period)
            self.ADC_worker.learning_rate_x = learning_rate
            self.ADC_worker.learning_rate_y = learning_rate
            self.ADC_worker.min_step_pulses = min_step
            self.ADC_worker.max_step_pulses = max_step
            self.ADC_worker.pulses_per_unit = pulses_per_unit
            self.ADC_worker.convergence_threshold = convergence_threshold
            self.ADC_active = True
            self.ADC_worker.start()
            
            self.ADC_start_btn.config(state=tk.DISABLED)
            self.ADC_stop_btn.config(state=tk.NORMAL)
            self.ADC_status_label.config(text="ADC: Active", fg="green")
            print("ADC control started")
    
    def stop_ADC(self):
        """Stop ADC control loop"""
        self.ADC_active = False
        if hasattr(self, "ADC_worker") and self.ADC_worker and self.ADC_worker.running:
            self.ADC_worker.stop()
            self.ADC_worker.join(timeout=2)
        
        self.ADC_start_btn.config(state=tk.NORMAL)
        self.ADC_stop_btn.config(state=tk.DISABLED)
        self.ADC_status_label.config(text="ADC: Inactive", fg="red")
        print("ADC control stopped")
    
    def start_position_routine(self):
        """Start the position routine that moves through predefined positions"""
        # Check prerequisites
        if not self.AC.is_open:
            messagebox.showerror("Error", "Please connect to autocollimator first.")
            return
        
        if not self.ser or not self.ser.is_open:
            messagebox.showerror("Error", "Please connect to piezo motor first.")
            return
        
        if not hasattr(self, "worker") or not self.worker or not self.worker.running:
            messagebox.showerror("Error", "Please start reading from autocollimator first.")
            return
        
        if self.position_routine_running:
            messagebox.showwarning("Warning", "Position routine is already running.")
            return
        
        # Start the position routine in a separate thread
        self.position_routine_thread = PositionRoutineThread(self)
        self.position_routine_thread.start()
        print("Position routine started")
    
    def start_test(self):
        if not self.AC.is_open:
            messagebox.showerror("Error", "Please connect to autocollimator first.")
            return
        
        if not hasattr(self, "worker") or not self.worker or not self.worker.running:
            messagebox.showerror("Error", "Please start reading from autocollimator first.")
            return
        
        # Get sampling period from GUI
        try:
            self.logging_sample_period = float(self.logging_sample_period_var.get())
            if self.logging_sample_period <= 0:
                raise ValueError("Sampling period must be positive")
        except ValueError:
            messagebox.showerror("Error", "Invalid sampling period. Please enter a positive number.")
            return
        
        self.test_running = True
        self.logged_data = []  # Clear previous data
        self.test_start_time = datetime.now()  # Record test start time
        self.last_log_time = None  # Reset last log time
        self.start_test_btn.config(state=tk.DISABLED)
        self.stop_test_btn.config(state=tk.NORMAL)
        self.test_status_label.config(text="Test Status: Running", fg="green")
        print(f"Test started - logging data at {self.logging_sample_period} second intervals")
    
    def stop_test(self):
        self.test_running = False
        self.last_log_time = None  # Reset last log time
        self.start_test_btn.config(state=tk.NORMAL)
        self.stop_test_btn.config(state=tk.DISABLED)
        self.test_status_label.config(text="Test Status: Stopped", fg="red")
        print(f"Test stopped - {len(self.logged_data)} data points logged")
    
    def update_data_count(self):
        count = len(self.logged_data)
        self.data_count_label.config(text=f"Data Points: {count}")
        self.after(1000, self.update_data_count)  # Update every second
    
    def save_data(self):
        if not self.logged_data:
            messagebox.showwarning("Warning", "No data to save. Please run a test first.")
            return
        
        # Ask user for file location
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="Save Data File"
        )
        
        if filename:
            try:
                with open(filename, 'w') as f:
                    # Write header
                    f.write("Time(s)\talnx\talny\n")
                    # Write data with elapsed time in seconds
                    for entry in self.logged_data:
                        f.write(f"{entry['elapsed_time']:.6f}\t{entry['alnx']:.6f}\t{entry['alny']:.6f}\n")
                messagebox.showinfo("Success", f"Data saved to {filename}")
                print(f"Data saved to {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save file: {e}")
                print(f"Error saving file: {e}")
    
    
    def update_position_display(self, position):
        self.lbl_position.config(text=f"Position: {position}")
        self.progress_bar.set(position / 100)
    
    def click_Origin(self):
        if self.ser == None:
            messagebox.showerror("Error", "Please connect to piezo motor first.")
            return
        rtn = self.var.get()
        if rtn == 0:
            axis = 'W'
        else:
            axis = str(rtn)
        wdata = 'N:' + axis + '\r\n'
        print(wdata)
        self.ser.write(wdata.encode())
        rdata = self.ser.readline()
        print(rdata)
    
    def click_MoveRel(self):
        if self.ser == None:
            messagebox.showerror("Error", "Please connect to piezo motor first.")
            return
        sss = self.txt1.get()
        value = int(sss)
        original_value = value
        sss = abs(value)
        print(value)
        if value > 0:
            direction = '+'
        else:
            direction = '-'
        rtn = self.var.get()
        
        # Apply swap_axes if enabled (swap axis selection)
        if self.swap_axes and rtn != 0:
            if rtn == 1:
                rtn = 2
            elif rtn == 2:
                rtn = 1
        
        # Apply reverse axis settings
        if rtn == 1 and self.reverse_axis1:
            value = -value
            direction = '+' if value > 0 else '-'
            sss = abs(value)
        elif rtn == 2 and self.reverse_axis2:
            value = -value
            direction = '+' if value > 0 else '-'
            sss = abs(value)
        elif rtn == 0:  # Both axes (W)
            # For both axes moving together, reverse doesn't apply
            # (both axes move the same amount, so reversing both doesn't change relative movement)
            pass
        
        if rtn == 0:
            axis = 'W'
            wdata = 'M:' + axis + direction + 'P' + str(sss) + direction + 'P' + str(sss) + '\r\n'
        else:
            axis = str(rtn)
            wdata = 'M:' + axis + direction + 'P' + str(sss) + '\r\n'
        
        if original_value != value:
            print(f"Direction reversed: {original_value} -> {value}")
        print(wdata)
        self.ser.write(wdata.encode())
        rdata = self.ser.readline()
        print(rdata)
        
        # Wait for motor to complete movement
        while True:
            wdata = '!:\r\n'
            self.ser.write(wdata.encode())
            print(wdata)
            status = self.ser.readline().decode().strip()
            print(status)
            if status == 'R':
                break
            elif status == 'B':
                time.sleep(0.5)
            else:
                print(f"Unexpected status: {status}")
                break
        
        # Now get the position
        wdata = 'G:\r\n'
        print(wdata)
        self.ser.write(wdata.encode())
        rtn = self.ser.readline()
        print(rtn)
        
        time.sleep(0.5)
        self.click_Status()
    
    def click_MoveAbs(self):
        if self.ser == None:
            messagebox.showerror("Error", "Please connect to piezo motor first.")
            return
        sss = self.txt2.get()
        if sss.isdigit() == False:
            return
        value = int(sss)
        original_value = value
        if value > 0:
            direction = '+'
        else:
            direction = '-'
        rtn = self.var.get()
        
        # Apply swap_axes if enabled (swap axis selection)
        if self.swap_axes and rtn != 0:
            if rtn == 1:
                rtn = 2
            elif rtn == 2:
                rtn = 1
        
        # Apply reverse axis settings
        if rtn == 1 and self.reverse_axis1:
            value = -value
            direction = '+' if value > 0 else '-'
            sss = str(abs(value))
        elif rtn == 2 and self.reverse_axis2:
            value = -value
            direction = '+' if value > 0 else '-'
            sss = str(abs(value))
        elif rtn == 0:  # Both axes (W)
            # For both axes moving together, reverse doesn't apply
            # (both axes move the same amount, so reversing both doesn't change relative movement)
            pass
        
        if rtn == 0:
            axis = 'W'
            wdata = 'A:' + axis + direction + 'P' + sss + direction + 'P' + sss + '\r\n'
        else:
            axis = str(rtn)
            wdata = 'A:' + axis + direction + 'P' + sss + '\r\n'
        
        if original_value != value:
            print(f"Direction reversed: {original_value} -> {value}")
        print(wdata)
        self.ser.write(wdata.encode())
        rdata = self.ser.readline()
        print(rdata)
        
        # Wait for motor to complete movement
        while True:
            wdata = '!:\r\n'
            self.ser.write(wdata.encode())
            status = self.ser.readline().decode().strip()
            print(status)
            if status == 'R':
                break
            elif status == 'B':
                time.sleep(0.5)
            else:
                print(f"Unexpected status: {status}")
                break
        
        # Now get the position
        wdata = 'G:\r\n'
        print(wdata)
        self.ser.write(wdata.encode())
        rtn = self.ser.readline()
        print(rtn)
        
        self.click_Status()
    
    def click_Stop(self):
        if self.ser == None:
            messagebox.showerror("Error", "Please connect to piezo motor first.")
            return
        rtn = self.var.get()
        axis = 'W' if rtn == 0 else str(rtn)
        wdata = f'L:{axis}\r\n'
        print(wdata)
        self.ser.write(wdata.encode())
        rdata = self.ser.readline()
        print(rdata)
    
    def click_Status(self):
        if self.ser == None:
            messagebox.showerror("Error", "Please connect to piezo motor first.")
            return
        wdata = 'Q:\r\n'
        print(wdata)
        self.ser.write(wdata.encode())
        rdata = self.ser.readline()
        print(rdata)
        
        rtn = self.var.get()
        if rtn == 0:
            sss = rdata[0:21]
        elif rtn == 1:
            sss = rdata[0:10]
        else:
            sss = rdata[12:21]
        self.lbl_status['text'] = (sss)
        
        try:
            self.update_position_display(int(sss))
        except:
            pass
    
    def safe_destroy(self):
        """Properly clean up all resources before exiting"""
        print("Shutting down application...")
        
        try:
            # Stop position routine if running
            if hasattr(self, "position_routine_thread") and self.position_routine_thread:
                if hasattr(self.position_routine_thread, "running") and self.position_routine_thread.running:
                    print("Stopping position routine thread...")
                    self.position_routine_thread.stop()
                    self.position_routine_thread.join(timeout=2)
                    if self.position_routine_thread.is_alive():
                        print("Warning: Position routine thread did not stop within timeout")
        except Exception as e:
            print(f"Error stopping position routine: {e}")
        
        try:
            # Stop ADC if running
            if hasattr(self, "ADC_worker") and self.ADC_worker:
                if hasattr(self.ADC_worker, "running") and self.ADC_worker.running:
                    print("Stopping ADC worker thread...")
                    self.ADC_active = False
                    self.ADC_worker.stop()
                    self.ADC_worker.join(timeout=2)
                    if self.ADC_worker.is_alive():
                        print("Warning: ADC worker thread did not stop within timeout")
        except Exception as e:
            print(f"Error stopping ADC worker: {e}")
        
        try:
            # Stop autocollimator reading thread
            if hasattr(self, "worker") and self.worker:
                if hasattr(self.worker, "running") and self.worker.running:
                    print("Stopping autocollimator reading thread...")
                    self.worker.stop()
                    self.worker.join(timeout=1)
                    if self.worker.is_alive():
                        print("Warning: Autocollimator reading thread did not stop within timeout")
        except Exception as e:
            print(f"Error stopping autocollimator worker: {e}")
        
        try:
            # Close serial connections
            if hasattr(self, "AC") and self.AC and self.AC.is_open:
                print("Closing autocollimator connection...")
                self.AC.close()
        except Exception as e:
            print(f"Error closing autocollimator: {e}")
        
        try:
            if hasattr(self, "ser") and self.ser and self.ser.is_open:
                print("Closing piezo motor connection...")
                self.ser.close()
        except Exception as e:
            print(f"Error closing piezo motor: {e}")
        
        # Quit tkinter mainloop before destroying window
        try:
            self.quit()
        except Exception as e:
            print(f"Error quitting mainloop: {e}")
        
        # Destroy the window
        try:
            self.destroy()
        except Exception as e:
            print(f"Error destroying window: {e}")
        
        print("Application shutdown complete")
        sys.exit(0)


if __name__ == "__main__":
    app = ADCGUI()
    app.mainloop()

