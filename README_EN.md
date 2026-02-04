# libpamc-204

A cross-platform library for controlling PAMC204.  
It can be built as a DLL on Windows and as an SO on Linux/WSL2.

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
│   └── pamc204.h               # Main API
├── src/
│   ├── core/                   # Platform-independent code
│   │   ├── api.cpp             # High-level API implementation
│   │   ├── utils.cpp           # Common utilities
│   │   └── utils.h             # Internal header
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
mkdir -p build && cd build
cmake ..
cmake --build .
```

Output:

- `./build/libpamc204.so` (shared library)
- `./build/test_serial` (test executable)

### Windows

```powershell
cd libpamc-204
mkdir build
cd build
cmake ..
cmake --build .
```

Output:

- `build\Debug\pamc204.dll` (DLL)
- `build\Debug\pamc204.lib` (Import library)
- `build\Debug\test_serial.exe` (Test executable)

## ▶️ Usage

### 🎯 High-Level API (Recommended)

Using dedicated functions for individual commands:

```cpp
#include "pamc204.h"

// C++ API (protected by namespace)
pamc204::get_firmware_version(1);           // E01INF
pamc204::check_device(1);                   // E01
pamc204::set_voltage(1, 4095);              // E01DAC4095 (150V)
pamc204::rotate_positive(1, 1500, 1000, 'A'); // E01NR15001000A
pamc204::stop(1);                           // E01S
pamc204::set_acceleration(1, 1, 10000);     // E011AC10000
pamc204::query_acceleration(1, 1);          // E011AC?
pamc204::set_velocity(1, 1, 1500);          // E011VA1500
pamc204::move_absolute(1, 1, 10000);        // E011PA10000
pamc204::move_relative(1, 1, 5000);         // E011PR5000
pamc204::query_actual_position(1, 1);       // E011TP?
pamc204::move_infinite(1, 1, '+');          // E011MV+
pamc204::stop_motion(1, 1);                 // E011ST
pamc204::abort_motion(1);                   // E01AB

// 4-axis simultaneous operation (DLL-level extension)
pamc204::move_relative_all_channels(1, 500);  // Move all axes +500
pamc204::move_infinite_all_channels(1, '+');  // Move all axes infinitely in + direction
pamc204::stop_motion_all_channels(1);         // Stop all axes
int actual_positions[4];
pamc204::query_actual_position_all_channels(1, actual_positions);
int statuses[4];
pamc204::query_motion_status_all_channels(1, statuses);

// C API (protected by pamc204_ prefix)
pamc204_get_firmware_version(1);
pamc204_check_device(1);
pamc204_set_voltage(1, 4095);
pamc204_rotate_positive(1, 1500, 1000, 'A');
pamc204_stop(1);
pamc204_set_acceleration(1, 1, 10000);
pamc204_query_acceleration(1, 1);
pamc204_set_velocity(1, 1, 1500);
pamc204_move_absolute(1, 1, 10000);
pamc204_move_relative(1, 1, 5000);
pamc204_query_actual_position(1, 1);
pamc204_move_infinite(1, 1, '+');
pamc204_stop_motion(1, 1);
pamc204_abort_motion(1);

// 4-axis simultaneous operation (DLL-level extension)
pamc204_move_relative_all_channels(1, 500);
pamc204_move_infinite_all_channels(1, '+');
pamc204_stop_motion_all_channels(1);
int actual_positions[4];
pamc204_query_actual_position_all_channels(1, actual_positions);
int statuses[4];
pamc204_query_motion_status_all_channels(1, statuses);
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

Return value:

- `true`: Success
- `false`: Error

### 📋 Command Reference

| No | Command Format | Usage Example | Description |
|----|----------------|---------------|-------------|
| 1 | `ExxINF` | `send_command("E01INF")` | Check firmware version |
| 2 | `Exx` | `send_command("E01")` | Check device existence |
| 3 | `SETADDRxx` | `send_command("SETADDR02")` | Change address (to E02) |
| 4 | `ExxDACnnnn` | `send_command("E01DAC4095")`<br>`send_command("E01DAC1900")` | Adjust drive voltage (150V / 70V)<br>Range: 70V～150V |
| 5 | `ExxNRnnnnyyyyz`<br>`ExxNRnnnnXyyyyyyz` | `send_command("E01NR15001500A")`<br>`send_command("E01NR1500X100000A")`<br>`send_command("E01NR15000000A")` | Forward rotation drive<br>1500Hz/1500 pulses<br>1500Hz/100000 pulses<br>1500Hz/continuous |
| 6 | `ExxRRnnnnyyyyz`<br>`ExxRRnnnnXyyyyyyz` | `send_command("E01RR15001500B")`<br>`send_command("E01RR1500X100000B")` | Reverse rotation drive<br>1500Hz/1500 pulses<br>1500Hz/100000 pulses |
| 7 | `ExxS` | `send_command("E01S")` | Stop pulse drive |
| 8 | `ExxAB` | `send_command("E01AB")` | Abort motion (immediate stop all CH) |
| 9 | `ExxmACnnnn` | `send_command("E011AC10000")` | Set acceleration (10000 steps/sec²)<br>Range: 1～150000 |
| 10 | `ExxmAC?` | `send_command("E011AC?")` | Query acceleration |
| 11 | `ExxmVAnnnn` | `send_command("E011VA1500")` | Set velocity (1500 steps/sec)<br>Range: 1～1500 |
| 12 | `ExxmVA?` | `send_command("E011VA?")` | Query velocity |
| 13 | `ExxmDHnnnn` | `send_command("E011DH0")` | Set home position |
| 14 | `ExxmDH?` | `send_command("E011DH?")` | Query home position |
| 15 | `ExxmPAnnnn` | `send_command("E011PA10000")` | Absolute position move (position 10000)<br>Range: -2147483648～+2147483647 |
| 16 | `ExxmPA?` | `send_command("E011PA?")` | Query absolute position |
| 17 | `ExxmPRnnnn` | `send_command("E011PR5000")` | Relative position move (+5000) |
| 18 | `ExxmPR?` | `send_command("E011PR?")` | Query relative position |
| 19 | `ExxmTP?` | `send_command("E011TP?")` | Query actual position |
| 20 | `ExxmMD?` | `send_command("E011MD?")` | Check motion status |
| 21 | `ExxmMVn` | `send_command("E011MV+")` | Infinite move (+ direction)<br>Direction: + or - |
| 22 | `ExxmMV?` | `send_command("E011MV?")` | Query move direction |
| 23 | `ExxmST` | `send_command("E011ST")` | Stop motion |

**Parameter Descriptions:**

- `xx`: Address (01～32)
- `nnnn`: Frequency (1～1500 Hz), acceleration, velocity, position, etc.
- `yyyy`: Pulse count (0000～9999, 0000=continuous)
- `Xyyyyyy`: Extended pulse count (X000001～X999999)
- `z`: Channel (A=CH1, B=CH2, C=CH3, D=CH4)
- `m`: Channel number (1～4)
- `n`: Direction (+ or -)

### Error Messages

| Error | Description |
|-------|-------------|
| `Error Value Range` | Output voltage value out of range (70V～150V) |
| `ERROR` | Invalid rotation direction, frequency, or channel specification |
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

```bash
# Linux/WSL2
sudo python3 test_linux_all_apis.py 
```

```powershell
# Windows
python3 test_windows_all_apis.py 
```

## 🧪 Test Records

- Windows
![windows test](./imgs/windows-test.png)

## memo

### Using USB Devices from WSL2 on Host Windows 11

[Reference](https://watako-lab.com/2025/05/18/wsl2_usbserial/)

```powershell
# Install usbipd
winget install usbipd

# List connected USB devices
usbipd list

# Bind device for WSL
usbipd bind --busid 1-1

# Attach device to WSL
usbipd attach --busid 1-1 --wsl

# Detach device
usbipd detach --busid 1-1
```

### Github Actions Automated Build && Release

```bash
# Tag and push to trigger Github Action
git tag v1.0.0
git push origin v1.0.0

# To redo tag push
git push origin :refs/tags/v1.0.0  # Delete remote tag
git tag -d v1.0.0                  # Delete local tag
git tag v1.0.0                     # Create tag again
git push origin v1.0.0             # Push tag
```
