# libpamc-204

クロスプラットフォーム対応のシリアル通信ライブラリです。  
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
├── CMakeLists.txt          # ビルド設定（Windows/Linux両対応）
├── README.md               
├── .gitignore              
├── include/                # 公開ヘッダ
│   └── serial.h            # 共通インターフェース
├── src/                    
│   ├── serial_common.cpp   # 共通処理（文字列変換・エラートークン検出）
│   ├── serial_win.cpp      # Windows専用実装（Win32 API）
│   ├── serial_linux.cpp    # Linux専用実装（termios）
└── demo/                   # 簡易動作確認用コード
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

### 共通 API
```cpp
#include "serial.h"

bool ok = pamc204::send_command("COM3", "E01INF");       // Windows
bool ok = pamc204::send_command("/dev/ttyUSB0", "E01INF"); // Linux
```

- `portName`: OSごとのポート指定  
  - Windows: `"COM3"` や `"\\\\.\\COM3"`  
  - Linux: `"/dev/ttyUSB0"`  
- `command`: 送信する文字列（CRLF が自動付加されます）

戻り値:
- `true`: 成功
- `false`: エラー（Windowsでは `GetLastError()`、Linuxでは標準出力にエラー行）

---

## 🧪 テスト実行方法

### Linux / WSL2
```bash
sudo ./test_serial /dev/ttyUSB0 "E01INF"
```

### Windows
```powershell
.\test_serial.exe COM3 "E01INF"
```

---

## 📌 補足
- Windows では DLL 内部で `DllMain` を持ち、Win32 API を利用しています。  
- Linux では `termios` を利用して同等の動作を再現しています。  
- エラートークン検出は共通処理 (`serial_common.cpp`) にまとめています。  

## 🧪 テスト記録
- Windows
![windows test](windows-test.png)

## memo
### WSL2からホストWindows11のUSB機器を使用する方法
[参考](https://watako-lab.com/2025/05/18/wsl2_usbserial/)

1. CMDを管理者権限で起動
```powershell
# 【usbipdのインストール】
winget install usbipd

#【接続されているUSBデバイスを表示】
usbipd list
  7-2    xxxx:xxxx  USB-Enhanced-SERIAL CH343 (COM2)                              Not shared
　⇒ USBシリアルが7-2というIDであることがわかる。

#【WSL側で使いたいデバイスをバインド】
usbipd bind --busid 1-1

#【WSL側で使いたいデバイスをバインド】
usbipd attach --busid 1-1 --wsl
```
