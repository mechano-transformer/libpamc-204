# libpamc-204

クロスプラットフォーム対応のPAMC204制御用ライブラリです。  
Windows では DLL、Linux/WSL2 では SO としてビルドできます。

## 📦 必要環境

- **Linux / WSL2**
  - g++ (C++17以上)
  - cmake (3.10以上推奨)
- **Windows**
  - Visual Studio 2022 または VSCode + CMake Tools
  - CMake (3.10以上)
  ※ ビルドにはVisualStudioのインストールが必須です

## 📂 プロジェクト構成

```text
libpamc-204/
├── CMakeLists.txt              # ビルド設定（Windows/Linux両対応）
├── README.md
├── docs/
│   └── API.md                  # API一覧・使用例
├── include/                    # 公開ヘッダ
│   └── pamc204.h               # メインAPI
├── src/
│   ├── core/                   # プラットフォーム非依存コード
│   │   ├── api.cpp             # 高レベルAPI実装
│   │   ├── utils.cpp           # 共通ユーティリティ
│   │   └── utils.h             # 内部ヘッダー
│   └── platform/               # プラットフォーム固有実装
│       ├── windows/
│       │   └── serial.cpp      # Windows実装（Win32 API）
│       └── linux/
│           └── serial.cpp      # Linux実装（termios）
├── tests/                      # ユニットテスト
│   └── test_api_unit.py        # send_command / send_commands_batch ユニットテスト
└── demo/                       # サンプルコード
    └── main.cpp
```

## 🔧 ビルド方法

### Linux / WSL2

```bash
cd libpamc-204
mkdir -p build && cd build
cmake ..
cmake --build .
```

生成物:

- `./build/libpamc204.so` (共有ライブラリ)
- `./build/test_serial` (テスト用実行ファイル)

### Windows

```powershell
# VisualStudioをインストールしていること
cd libpamc-204
mkdir build
cd build
cmake -DCMAKE_BUILD_TYPE=Release ..
cmake --build . --config Release
```

生成物:

- `build\Release\pamc204.dll` (DLL本体)
- `build\Release\pamc204.lib` (インポートライブラリ)
- `build\Release\test_serial.exe` (動作確認用実行ファイル)

## ▶️ 使い方

### 🎯 高レベルAPI（推奨）

個別コマンド専用関数を使用する方法。詳細は [docs/API.md](docs/API.md) を参照。

```cpp
#include "pamc204.h"

// C++ API（名前空間で保護）
std::string resp = pamc204::get_firmware_version(1);  // E01INF → レスポンス文字列
pamc204::check_device(1);                              // E01
pamc204::set_voltage(1, 4095);                         // E01DAC4095 (150V)
pamc204::rotate_positive(1, 1500, 1000, 'A');          // E01NR15001000A
pamc204::stop(1);                                      // E01S
pamc204::set_acceleration(1, 1, 10000);                // E011AC10000
int acc = pamc204::query_acceleration(1, 1);           // E011AC? → int値（失敗時 -1）
pamc204::set_velocity(1, 1, 1500);                     // E011VA1500
pamc204::move_absolute(1, 1, 10000);                   // E011PA10000
pamc204::move_relative(1, 1, 5000);                    // E011PR5000
int pos = pamc204::query_actual_position(1, 1);        // E011TP? → int値（失敗時 INT_MIN）
int status = pamc204::query_motion_status(1, 1);       // E011MD? → 0=動作中, 1=停止, -1=失敗
pamc204::move_infinite(1, 1, '+');                     // E011MV+
pamc204::stop_motion(1, 1);                            // E011ST
pamc204::abort_motion(1);                              // E01AB

// 4軸同時操作（send_commands_batch を使用して1回のポート開閉で送信）
std::vector<std::string> resps = pamc204::move_relative_all_channels(1, 500);
std::vector<int> positions     = pamc204::query_actual_position_all_channels(1);
std::vector<int> statuses      = pamc204::query_motion_status_all_channels(1);
pamc204::move_infinite_all_channels(1, '+');
pamc204::stop_motion_all_channels(1);

// C API（pamc204_プレフィックス）
pamc204_get_firmware_version(1);
pamc204_set_acceleration(1, 1, 10000);
int acc2 = pamc204_query_acceleration(1, 1);    // int値を直接返す
int pos2 = pamc204_query_actual_position(1, 1); // int値を直接返す
int st2  = pamc204_query_motion_status(1, 1);   // int値を直接返す
```

### 🔩 低レベルAPI

汎用コマンド送信（柔軟性が高い）：

```cpp
#include "pamc204.h"

// C++ API: レスポンス文字列を返す
std::string resp = pamc204::send_command("E01INF");
if (!resp.empty()) { /* 成功 */ }

// 複数コマンドを1回のポート開閉で送信
auto resps = pamc204::send_commands_batch({"E011AC?", "E011VA?", "E011TP?"});
if (!resps.empty()) {
    // resps[0] = 加速度, resps[1] = 速度, resps[2] = 実位置
}

// C API: 成功/失敗を bool で返す（レスポンスはバッファに格納）
char buf[256] = {};
bool ok = pamc204_send_command("E01INF", buf, sizeof(buf));
```

### 📋 コマンドリファレンス

詳細は [docs/API.md](docs/API.md) を参照。

| No | コマンドフォーマット | 高レベルAPI（C++） | 説明 |
|----|--------------------|--------------------|------|
| 1 | `ExxINF` | `get_firmware_version(1)` → `string` | ファームウェアバージョン確認 |
| 2 | `Exx` | `check_device(1)` → `string` | デバイス存在確認 |
| 3 | `SETADDRxx` | `set_address(2)` → `string` | アドレス変更 |
| 4 | `ExxDACnnnn` | `set_voltage(1, 4095)` → `string` | 駆動電圧設定（70V〜150V） |
| 5 | `ExxNRnnnnyyyyz` | `rotate_positive(1, 1500, 1000, 'A')` → `string` | 正回転駆動 |
| 6 | `ExxRRnnnnyyyyz` | `rotate_negative(1, 1500, 1000, 'A')` → `string` | 逆回転駆動 |
| 7 | `ExxS` | `stop(1)` → `string` | パルス駆動停止 |
| 8 | `ExxAB` | `abort_motion(1)` → `string` | モーション停止（全CH即停止） |
| 9 | `ExxmACnnnn` | `set_acceleration(1, 1, 10000)` → `string` | 加速度設定 |
| 10 | `ExxmAC?` | `query_acceleration(1, 1)` → `int` | 加速度問い合わせ（失敗時 -1） |
| 11 | `ExxmVAnnnn` | `set_velocity(1, 1, 1500)` → `string` | 速度設定 |
| 12 | `ExxmVA?` | `query_velocity(1, 1)` → `int` | 速度問い合わせ（失敗時 -1） |
| 13 | `ExxmDHnnnn` | `set_home_position(1, 1, 0)` → `string` | ホームポジション設定 |
| 14 | `ExxmDH?` | `query_home_position(1, 1)` → `int` | ホームポジション問い合わせ（失敗時 INT_MIN） |
| 15 | `ExxmPAnnnn` | `move_absolute(1, 1, 10000)` → `string` | 絶対位置移動 |
| 16 | `ExxmPA?` | `query_absolute_position(1, 1)` → `int` | 絶対位置問い合わせ（失敗時 INT_MIN） |
| 17 | `ExxmPRnnnn` | `move_relative(1, 1, 5000)` → `string` | 相対位置移動 |
| 18 | `ExxmPR?` | `query_relative_position(1, 1)` → `int` | 相対位置問い合わせ（失敗時 INT_MIN） |
| 19 | `ExxmTP?` | `query_actual_position(1, 1)` → `int` | 実位置問い合わせ（失敗時 INT_MIN） |
| 20 | `ExxmMD?` | `query_motion_status(1, 1)` → `int` | 動作状態確認（0=動作中, 1=停止, -1=失敗） |
| 21 | `ExxmMVn` | `move_infinite(1, 1, '+')` → `string` | 無限移動 |
| 22 | `ExxmMV?` | `query_move_direction(1, 1)` → `char` | 移動方向問い合わせ（失敗時 '\0'） |
| 23 | `ExxmST` | `stop_motion(1, 1)` → `string` | 動作停止 |

### エラーメッセージ

| エラー | 説明 |
|--------|------|
| `Error Value Range` | 出力電圧の値が範囲外（70V～150V） |
| `ERROR` | 回転方向、周波数、チャンネル指定が不正 |
| `ERROR1` | コマンド認識不可 |
| `ERROR4` | 6桁パルス数が範囲外（X000001～X999999） |
| `ERROR5` | 4桁パルス数が範囲外（0001～9999） |
| `BUSY` | ドライバ駆動中（停止後に再送信） |

## 🧪 テスト実行方法

### Linux / WSL2

```bash
sudo ./test_serial "E01INF"
```

### Windows

```powershell
.\Release\test_serial.exe "E01INF"
```

※ `usbipd`でWSLにattachしてるときはdetatchすること

```powershell
usbipd detach --busid 1-1
```

### 動的ライブラリの動作確認

```bash
# Linux/WSL2
sudo python3 test_linux_all_apis.py 
```

```powershell
# Windows
python3 test_windows_all_apis.py 
```

### ユニットテスト（モック使用・デバイス不要）

```bash
python3 -m pytest tests/test_api_unit.py -v
```

## 🧪 テスト記録

- Windows
![windows test](./imgs/windows-test.png)

## memo

### WSL2からホストWindows11のUSB機器を使用する方法

[参考](https://watako-lab.com/2025/05/18/wsl2_usbserial/)

```powershell
# 【usbipdのインストール】
winget install usbipd

#【接続されているUSBデバイスを表示】
usbipd list

#【WSL側で使いたいデバイスをバインド】
usbipd bind --busid 1-1

#【WSL側で使いたいデバイスをアタッチ】
usbipd attach --busid 1-1 --wsl

#【デバイスをデタッチ】
usbipd detach --busid 1-1
```

### Github Actionsによる自動ビルド && リリース

```bash
# タグをつけてpushすればGithub Actionが回る
git tag v1.0.0
git push origin v1.0.0

# tagのpushをやり直したいとき
git push origin :refs/tags/v1.0.0  # リモートのタグを削除
git tag -d v1.0.0                  # ローカルのタグを削除
git tag v1.0.0                     # 再度タグを作成
git push origin v1.0.0             # タグをpush
```

### C++のオートフォーマット

```bash
# インストール
sudo apt install clang-format

# 実行
cd libpamc-204
clang-format -i src/**/*.cpp
```
