# libpamc-204

A cross-platform library for controlling PAMC204.  
It can be built as a DLL on Windows and as an SO on Linux/WSL2.  
Provides a common API `pamc204::send_command(command)` with platform-specific internal implementations.

## 📦 Requirements

- **Linux / WSL2**
  - g++ (C++17 or later)
  - cmake (3.10 or later recommended)
- **Windows**
  - Visual Studio 2022 or VSCode + CMake Tools
  - CMake (3.10 or later)

## 📂 Project Structure

```
libpamc-204/
├── CMakeLists.txt              # Build configuration (Windows/Linux compatible)
├── README.md
├── include/                    # Public headers
│   ├── pamc204.h               # Main API
│   └── pamc204_internal.h      # Internal utilities
├── src/
│   ├── core/                   # Platform-independent code
│   │   ├── api.cpp             # High-level API implementation
│   │   └── utils.cpp           # Common utilities
│   └── platform/               # Platform-specific implementations
│       ├── windows/
│       │   └── serial.cpp      # Windows implementation (Win32 API)
│       └── linux/
│           └── serial.cpp      # Linux implementation (termios)
└── demo/                       # Sample code
    └── main.cpp
```

## 🔧 Build Instructions

### Linux / WSL2

```bash
cd libpamc-204
mkdir build -p && cd build
cmake ..
cmake --build .
```

Output:

- `./build/libpamc204.so` (shared library)
- `./build/test_serial` (test executable)

### Windows (VSCode + CMake Tools or CMake/Ninja)

```powershell
cd libpamc-204
mkdir build
cd build
cmake ..
cmake --build .
```

Output:

- Debug build
  - build\Debug\pamc204.dll   # DLL
  - build\Debug\pamc204.lib   # Import library
  - build\Debug\pamc204.exp   # Export information
  - build\Debug\test_serial.exe # Test executable

- Release build
  - build\Release\pamc204.dll
  - build\Release\pamc204.lib
  - build\Release\test_serial.exe

## ▶️ Usage

### 🎯 High-Level API (Recommended)

Using dedicated functions for individual commands (CmdLib style from PDF):

```cpp
#include "pamc204.h"

// C++ API (protected by namespace)
pamc204::get_firmware_version(1);           // E01INF
pamc204::check_device(1);                   // E01
pamc204::set_voltage(1, 4095);              // E01DAC4095 (150V)
pamc204::rotate_positive(1, 1500, 1000, 'A'); // E01NR15001000A
pamc204::stop(1);                           // E01S
pamc204::set_acceleration(1, 1, 10000);     // E011AC10000 (Set CH1 acceleration to 10000)
pamc204::query_acceleration(1, 1);          // E011AC? (Query CH1 acceleration)
pamc204::set_velocity(1, 1, 1500);          // E011VA1500 (Set CH1 velocity to 1500)
pamc204::move_absolute(1, 1, 10000);        // E011PA10000 (Move CH1 to absolute position 10000)
pamc204::move_relative(1, 1, 5000);         // E011PR5000 (Move CH1 relative +5000)
pamc204::query_actual_position(1, 1);       // E011TP? (Query CH1 actual position)
pamc204::move_infinite(1, 1, '+');          // E011MV+ (Move CH1 infinitely in + direction)
pamc204::stop_motion(1, 1);                 // E011ST (Stop CH1 motion)
pamc204::abort_motion(1);                   // E01AB (Immediate stop all CH)

// C API (protected by pamc204_ prefix)
pamc204_get_firmware_version(1);
pamc204_rotate_positive(1, 1500, 1000, 'A');
pamc204_stop(1);
pamc204_set_acceleration(1, 1, 10000);
pamc204_query_acceleration(1, 1);
pamc204_set_velocity(1, 1, 1500);
pamc204_move_absolute(1, 1, 10000);
pamc204_query_actual_position(1, 1);
```

### 🔧 Low-Level API

Generic command sending (more flexible):

```cpp
#include "pamc204.h"

// C++ API
pamc204::send_command("E01INF");
pamc204::send_command("E01NR15001000A");

// C API
pamc204_send_command("E01INF");
```

- `command`: String to send (CRLF is automatically appended)

Return value:

- `true`: Success
- `false`: Error (Windows: `GetLastError()`, Linux: error output to stdout)

### 📋 (Reference) Command List

Available commands for PAMC-204:

| No | Command | Details |
|----|---------|---------|
| 1 | `ExxINF` | Check firmware version |
| 2 | `Exx` | Check if driver with address exists in network |
| 3 | `SETADDRxx` | Change driver address |
| 4 | `ExxDACnnnn` | Adjust drive voltage |
| 5 | `ExxNRnnnnyyyyz`<br>`ExxNRnnnnXyyyyyyz` | Forward rotation drive command (pulse drive) |
| 6 | `ExxRRnnnnyyyyz`<br>`ExxRRnnnnXyyyyyyz` | Reverse rotation drive command (pulse drive) |
| 7 | `ExxS` | Stop command (pulse drive) |
| 8 | `ExxAB` | Motion stop (immediate stop all CH) |
| 9 | `ExxmACnnnn` | Acceleration setting |
| 10 | `ExxmAC?` | Acceleration query |
| 11 | `ExxmVAnnnn` | Velocity setting |
| 12 | `ExxmVA?` | Velocity query |
| 13 | `ExxmDHnnnn` | Home position setting |
| 14 | `ExxmDH?` | Home position query |
| 15 | `ExxmPAnnnn` | Absolute position move |
| 16 | `ExxmPA?` | Absolute position query |
| 17 | `ExxmPRnnnn` | Relative position move |
| 18 | `ExxmPR?` | Relative position query |
| 19 | `ExxmTP?` | Actual position query |
| 20 | `ExxmMD?` | Motion status check |
| 21 | `ExxmMVn` | Infinite move |
| 22 | `ExxmMV?` | Move direction query |
| 23 | `ExxmST` | Motion stop |

### 📋 API Usage Examples

Usage examples based on PAMC-204 command specifications:

| Function | Command Example | Description |
|----------|----------------|-------------|
| **Firmware Version Check** | `send_command("E01INF")` | Get firmware version of driver at address E01 |
| **Device Existence Check** | `send_command("E01")` | Check if driver at address E01 is connected |
| **Address Change** | `send_command("SETADDR02")` | Change address of connected driver to E02 |
| **Output Voltage Adjustment** | `send_command("E01DAC4095")` | Set output voltage of address E01 to 150V |
| | `send_command("E01DAC3000")` | Set output voltage of address E01 to 110V |
| | `send_command("E01DAC1900")` | Set output voltage of address E01 to 70V |
| **Forward Rotation (Pulse Specified)** | `send_command("E01NR15001500A")` | Rotate E01 CH1 forward at 1500Hz for 1500 pulses |
| | `send_command("E01NR1500X100000A")` | Rotate E01 CH1 forward at 1500Hz for 100000 pulses |
| **Forward Rotation (Continuous)** | `send_command("E01NR15000000A")` | Continuously rotate E01 CH1 forward at 1500Hz |
| **Reverse Rotation (Pulse Specified)** | `send_command("E01RR15001500B")` | Rotate E01 CH2 reverse at 1500Hz for 1500 pulses |
| | `send_command("E01RR1500X100000B")` | Rotate E01 CH2 reverse at 1500Hz for 100000 pulses |
| **Reverse Rotation (Continuous)** | `send_command("E01RR15000000C")` | Continuously rotate E01 CH3 reverse at 1500Hz |
| **Stop** | `send_command("E01S")` | Stop continuous drive of E01 |
| **Acceleration Setting** | `send_command("E011AC10000")` | Set E01 CH1 acceleration to 10000 steps/sec² |
| **Acceleration Query** | `send_command("E011AC?")` | Query E01 CH1 acceleration |
| **Velocity Setting** | `send_command("E011VA1500")` | Set E01 CH1 velocity to 1500 steps/sec |
| **Absolute Position Move** | `send_command("E011PA10000")` | Move E01 CH1 to absolute position 10000 |
| **Relative Position Move** | `send_command("E011PR5000")` | Move E01 CH1 +5000 from current position |
| **Actual Position Query** | `send_command("E011TP?")` | Query E01 CH1 current position |
| **Infinite Move** | `send_command("E011MV+")` | Move E01 CH1 infinitely in + direction |
| **Motion Stop** | `send_command("E011ST")` | Stop E01 CH1 motion |
| **Abort Motion** | `send_command("E01AB")` | Immediate stop all CH of E01 |

#### Command Format Details

**Pulse Drive Commands:**

- **Address**: `xx` = 01～32 (e.g., E01, E02, ...)
- **Frequency**: `nnnn` = 0001～1500 Hz
- **Pulse Count**:
  - 4 digits: `yyyy` = 0000～9999 (0000=continuous drive)
  - 6 digits: `Xyyyyyy` = X000001～X999999 (with X prefix)
- **Channel**: `z` = A (CH1), B (CH2), C (CH3), D (CH4)
- **Output Voltage**: 70V～150V

**Position Control Commands:**

- **Address**: `xx` = 01～32
- **Channel**: `m` = 1～4
- **Acceleration**: `nnnn` = 1～150000 steps/sec²
- **Velocity**: `nnnn` = 1～1500 steps/sec
- **Position**: `nnnn` = -2147483648～+2147483647
- **Direction**: `n` = + (forward) or - (reverse)

#### Error Messages

- Library error message display examples

```
ERROR: ERROR1 - Command not recognized
ERROR: ERROR4 - 6-digit pulse count out of range (X000001～X999999)
ERROR: BUSY - Driver is in operation. Resend after stopping
```

- Error specifications
| Error | Description |
|-------|-------------|
| `Error Value Range` | Output voltage value out of range (70V～150V) |
| `ERROR` | Invalid rotation direction, frequency, or channel specification, or command not recognized |
| `ERROR1` | Command not recognized |
| `ERROR4` | 6-digit pulse count out of range (X000001～X999999) |
| `ERROR5` | 4-digit pulse count out of range (0001～9999) |
| `BUSY` | Driver in operation (resend after stopping) |

## 🧪 Test Execution

### Linux / WSL2

```bash
sudo ./test_serial "E01INF"
```

### Windows

```powershell
.\Debug\test_serial.exe "E01INF"
```

※ When attached to WSL via `usbipd`, detach it from WSL

```powershell
usbipd detach --busid 1-1
```

### Dynamic Library Operation Verification

`test_linux.py` and `test_windows.py` are provided for library operation verification.

```bash
sudo python3 test_linux_all_apis.py 
```

```powershell
python3 test_windows_all_apis.py 
```
