# libpamc-204

クロスプラットフォーム対応のPAMC204制御用ライブラリです。  
Windows では DLL、Linux/WSL2 では SO としてビルドできます。  
共通 API `pamc204::send_command(portName, command)` を提供し、OS ごとに内部実装を切り替えています。

## 📦 必要環境

- **Linux / WSL2**
  - g++ (C++17以上)
  - cmake (3.10以上推奨)
- **Windows**
  - Visual Studio 2022 または VSCode + CMake Tools
  - CMake (3.10以上)

## 📂 プロジェクト構成

```
libpamc-204/
├── CMakeLists.txt              # ビルド設定（Windows/Linux両対応）
├── README.md
├── include/                    # 公開ヘッダ
│   ├── serial.h                # メインAPI
│   └── serial_common.h         # 共通ユーティリティ
├── src/
│   ├── core/                   # プラットフォーム非依存コード
│   │   ├── api.cpp             # 高レベルAPI実装
│   │   └── utils.cpp           # 共通ユーティリティ
│   └── platform/               # プラットフォーム固有実装
│       ├── windows/
│       │   └── serial.cpp      # Windows実装（Win32 API）
│       └── linux/
│           └── serial.cpp      # Linux実装（termios）
└── demo/                       # サンプルコード
    └── main.cpp
```

## 🔧 ビルド方法

### Linux / WSL2

```bash
cd libpamc-204
mkdir build -p && cd build
cmake ..
make
```

生成物:

- `./build/libpamc204.so` (共有ライブラリ)
- `./build/test_serial` (テスト用実行ファイル)

### Windows (VSCode + CMake Tools または CMake/Ninja)

```powershell
cd libpamc-204
mkdir build
cd build
cmake ..
cmake --build .
```

生成物:

- Debugビルド時
  - build\Debug\pamc204.dll   # DLL本体
  - build\Debug\pamc204.lib   # インポートライブラリ
  - build\Debug\pamc204.exp   # エクスポート情報
  - build\Debug\test_serial.exe # 動作確認用実行ファイル

- Releaseビルド時
  - build\Release\pamc204.dll
  - build\Release\pamc204.lib
  - build\Release\test_serial.exe

## ▶️ 使い方

### 🎯 高レベルAPI（推奨）

個別コマンド専用関数を使用する方法（PDFのCmdLibスタイル）：

```cpp
#include "serial.h"

// C++ API（名前空間で保護）
pamc204::get_firmware_version("COM3", 1);           // E01INF
pamc204::check_device("COM3", 1);                   // E01
pamc204::set_voltage("COM3", 1, 4095);              // E01DAC4095 (150V)
pamc204::rotate_positive("COM3", 1, 1500, 1000, 'A'); // E01NR15001000A
pamc204::stop("COM3", 1);                           // E01S

// C API（pamc204_プレフィックスで保護）
pamc204_get_firmware_version("COM3", 1);
pamc204_rotate_positive("COM3", 1, 1500, 1000, 'A');
pamc204_stop("COM3", 1);
```

### 🔧 低レベルAPI

汎用コマンド送信（柔軟性が高い）：

```cpp
#include "serial.h"

// C++ API
pamc204::send_command("COM3", "E01INF");
pamc204::send_command("COM3", "E01NR15001000A");

// C API
pamc204_send_command("COM3", "E01INF");
```

- `portName`: OSごとのポート指定
  - Windows: `"COM3"` や `"\\\\.\\COM3"`
  - Linux: `"/dev/ttyUSB0"`
- `command`: 送信する文字列（CRLF が自動付加されます）

戻り値:

- `true`: 成功
- `false`: エラー（Windowsでは `GetLastError()`、Linuxでは標準出力にエラー行）

### 📋 (参考)コマンド表

PAMC-204で使用可能なコマンド一覧：

| No | コマンド | 詳細 |
|----|---------|------|
| 1 | `ExxINF` | ファームウェアバージョンの確認 |
| 2 | `Exx` | アドレスを持つドライバーがネットワーク内に存在するかどうかを確認 |
| 3 | `SETADDRxx` | ドライバのアドレスを変更 |
| 4 | `ExxDACnnnn` | 駆動電圧の調整 |
| 5 | `ExxNRnnnnyyyyz`<br>`ExxNRnnnnXyyyyyyz` | 正回転駆動コマンド |
| 6 | `ExxRRnnnnyyyyz`<br>`ExxRRnnnnXyyyyyyz` | 逆回転駆動コマンド |
| 7 | `ExxS` | 停止コマンド |

### 📋 API使用例

PAMC-204のコマンド仕様に基づく使用例：

| 機能 | コマンド例 | 説明 |
|------|-----------|------|
| **ファームウェアバージョン確認** | `send_command(port, "E01INF")` | アドレスE01のドライバのファームウェアバージョンを取得 |
| **デバイス存在確認** | `send_command(port, "E01")` | アドレスE01のドライバが接続されているか確認 |
| **アドレス変更** | `send_command(port, "SETADDR02")` | 接続中のドライバのアドレスをE02に変更 |
| **出力電圧調整** | `send_command(port, "E01DAC4095")` | アドレスE01の出力電圧を150Vに設定 |
| | `send_command(port, "E01DAC3000")` | アドレスE01の出力電圧を110Vに設定 |
| | `send_command(port, "E01DAC1900")` | アドレスE01の出力電圧を70Vに設定 |
| **正回転駆動（パルス指定）** | `send_command(port, "E01NR15001500A")` | E01のCH1を1500Hzで1500パルス正回転 |
| | `send_command(port, "E01NR1500X100000A")` | E01のCH1を1500Hzで100000パルス正回転 |
| **正回転駆動（連続）** | `send_command(port, "E01NR15000000A")` | E01のCH1を1500Hzで連続正回転 |
| **逆回転駆動（パルス指定）** | `send_command(port, "E01RR15001500B")` | E01のCH2を1500Hzで1500パルス逆回転 |
| | `send_command(port, "E01RR1500X100000B")` | E01のCH2を1500Hzで100000パルス逆回転 |
| **逆回転駆動（連続）** | `send_command(port, "E01RR15000000C")` | E01のCH3を1500Hzで連続逆回転 |
| **停止** | `send_command(port, "E01S")` | E01の連続駆動を停止 |

#### コマンドフォーマット詳細

- **アドレス**: `xx` = 01～32（例: E01, E02, ...）
- **周波数**: `nnnn` = 0001～1500 Hz
- **パルス数**:
  - 4桁: `yyyy` = 0000～9999（0000=連続駆動）
  - 6桁: `Xyyyyyy` = X000001～X999999（Xプレフィックス付き）
- **チャンネル**: `z` = A（CH1）, B（CH2）, C（CH3）, D（CH4）
- **出力電圧**: 70V～150V

#### エラーメッセージ

- ライブラリによるエラーメッセージ表示例

```
ERROR: ERROR1 - コマンドが認識できません
ERROR: ERROR4 - 6桁パルス数が範囲外です（X000001～X999999）
ERROR: BUSY - ドライバが駆動中です。停止後に再送信してください
```

- エラー仕様
| エラー | 説明 |
|--------|------|
| `Error Value Range` | 出力電圧の値が範囲外（70V～150V） |
| `ERROR` | 回転方向、周波数、チャンネル指定が不正、またはコマンド認識不可 |
| `ERROR1` | コマンド認識不可 |
| `ERROR4` | 6桁パルス数が範囲外（X000001～X999999） |
| `ERROR5` | 4桁パルス数が範囲外（0001～9999） |
| `BUSY` | ドライバ駆動中（停止後に再送信） |

## 🧪 テスト実行方法

### Linux / WSL2

```bash
sudo ./test_serial /dev/ttyUSB0 "E01INF"
```

### Windows

```powershell
.\test_serial.exe COM3 "E01INF"
```

### 動的ライブラリの動作確認

`test_linux.py`,`test_windows.py`を用意したのでこれを実行することによりライブラリの動作確認が行えます。

## 🧪 テスト記録

- Windows
![windows test](./imgs/windows-test.png)

## memo

### WSL2からホストWindows11のUSB機器を使用する方法

[参考](https://watako-lab.com/2025/05/18/wsl2_usbserial/)

1. CMDを管理者権限で起動

```powershell
# 【usbipdのインストール】
winget install usbipd

#【接続されているUSBデバイスを表示】
usbipd list
  1-1    0403:6015  USB Serial Converter                                          Attached
　⇒ USBシリアルが1-1というIDであることがわかる。

#【WSL側で使いたいデバイスをバインド】
usbipd bind --busid 1-1

#【WSL側で使いたいデバイスをバインド】
usbipd attach --busid 1-1 --wsl
```
