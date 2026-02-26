# PAMC-204 API リファレンス

## 概要

`libpamc-204` が提供する全 API の一覧と使用例です。

- **C++ API**: `pamc204::` 名前空間
- **C API**: `pamc204_` プレフィックス（Python ctypes から利用可能）

---

## 低レベル API

| No | API名 | 等価コマンド | 説明 |
|----|-------|-------------|------|
| 1 | `send_command(cmd)` → `string` | 任意 | 汎用コマンド送信。レスポンス文字列を返す。失敗時は空文字列。 |
| 2 | `send_commands_batch(cmds)` → `vector<string>` | 複数 | 複数コマンドを1回のポート開閉で順次送信。失敗時は空 vector。 |

### C API シグネチャ

```c
bool pamc204_send_command(const char *command, char *out_response, int out_size);
```

- `out_response`: レスポンスを格納するバッファ（不要な場合は `NULL`）
- `out_size`: バッファサイズ（`NULL` の場合は `0`）

### 使用例（Python）

```python
# レスポンス不要の場合
lib.pamc204_send_command(b"E01INF", None, 0)

# レスポンスを取得する場合
buf = ctypes.create_string_buffer(256)
ok = lib.pamc204_send_command(b"E01INF", buf, 256)
if ok:
    print(buf.value.decode())
```

---

## 高レベル API（設定系）

設定系 API は `string`（C++）または `bool`（C API）を返します。

| No | API名 | 等価コマンド | 説明 |
|----|-------|-------------|------|
| 1 | `get_firmware_version(addr)` | `ExxINF` | ファームウェアバージョン取得 |
| 2 | `check_device(addr)` | `Exx` | デバイス存在確認 |
| 3 | `set_address(new_addr)` | `SETADDRxx` | デバイスアドレス変更 |
| 4 | `set_voltage(addr, dac)` | `ExxDACnnnn` | 駆動電圧設定（1900=70V〜4095=150V） |
| 5 | `rotate_positive(addr, freq, pulses, ch)` | `ExxNRnnnnyyyyz` | 正回転駆動（freq: 1-1500Hz, pulses: 0=連続） |
| 6 | `rotate_positive_ex(addr, freq, pulses, ch)` | `ExxNRnnnnXyyyyyyz` | 正回転駆動・拡張パルス（1-999999） |
| 7 | `rotate_negative(addr, freq, pulses, ch)` | `ExxRRnnnnyyyyz` | 逆回転駆動 |
| 8 | `rotate_negative_ex(addr, freq, pulses, ch)` | `ExxRRnnnnXyyyyyyz` | 逆回転駆動・拡張パルス |
| 9 | `stop(addr)` | `ExxS` | パルス駆動停止 |
| 10 | `abort_motion(addr)` | `ExxAB` | モーション停止（全CH即停止） |
| 11 | `set_acceleration(addr, ch, acc)` | `ExxmACnnnn` | 加速度設定（1-150000 steps/sec²） |
| 12 | `set_velocity(addr, ch, vel)` | `ExxmVAnnnn` | 速度設定（1-1500 steps/sec） |
| 13 | `set_home_position(addr, ch, pos)` | `ExxmDHnnnn` | ホームポジション設定 |
| 14 | `move_absolute(addr, ch, pos)` | `ExxmPAnnnn` | 絶対位置移動 |
| 15 | `move_relative(addr, ch, pos)` | `ExxmPRnnnn` | 相対位置移動 |
| 16 | `move_infinite(addr, ch, dir)` | `ExxmMVn` | 無限移動（dir: '+' または '-'） |
| 17 | `stop_motion(addr, ch)` | `ExxmST` | 動作停止 |

### 使用例（Python）

```python
lib.pamc204_get_firmware_version(1)
lib.pamc204_check_device(1)
lib.pamc204_set_voltage(1, 4095)           # 150V
lib.pamc204_set_acceleration(1, 1, 10000)  # ch1, 10000 steps/sec²
lib.pamc204_set_velocity(1, 1, 1500)       # ch1, 1500 steps/sec
lib.pamc204_set_home_position(1, 1, 0)     # ch1, ホーム=0
lib.pamc204_move_relative(1, 1, 500)       # ch1, +500パルス
lib.pamc204_move_absolute(1, 1, 1000)      # ch1, 絶対位置1000
lib.pamc204_move_infinite(1, 1, b"+")      # ch1, +方向に無限移動
lib.pamc204_stop_motion(1, 1)              # ch1, 停止
lib.pamc204_abort_motion(1)                # 全CH即停止
lib.pamc204_rotate_positive(1, 1500, 100, b"A")  # 正回転, 1500Hz, 100パルス, CH-A
```

---

## 高レベル API（問い合わせ系）

問い合わせ系 API は値を **直接返します**（C++ / C API 共通）。

| No | API名 | 等価コマンド | 説明 | 失敗時の戻り値 |
|----|-------|-------------|------|---------------|
| 1 | `query_acceleration(addr, ch)` → `int` | `ExxmAC?` | 加速度問い合わせ | `-1` |
| 2 | `query_velocity(addr, ch)` → `int` | `ExxmVA?` | 速度問い合わせ | `-1` |
| 3 | `query_home_position(addr, ch)` → `int` | `ExxmDH?` | ホームポジション問い合わせ | `INT_MIN` |
| 4 | `query_absolute_position(addr, ch)` → `int` | `ExxmPA?` | 絶対位置問い合わせ | `INT_MIN` |
| 5 | `query_relative_position(addr, ch)` → `int` | `ExxmPR?` | 相対位置問い合わせ | `INT_MIN` |
| 6 | `query_actual_position(addr, ch)` → `int` | `ExxmTP?` | 実位置問い合わせ | `INT_MIN` |
| 7 | `query_motion_status(addr, ch)` → `int` | `ExxmMD?` | 動作状態確認（0=動作中, 1=停止） | `-1` |
| 8 | `query_move_direction(addr, ch)` → `char` | `ExxmMV?` | 移動方向問い合わせ（'+' または '-'） | `'\0'` |

### 使用例（Python）

```python
INT_MIN = -2147483648

acc = lib.pamc204_query_acceleration(1, 1)
if acc != -1:
    print(f"加速度: {acc} steps/sec²")

vel = lib.pamc204_query_velocity(1, 1)
if vel != -1:
    print(f"速度: {vel} steps/sec")

pos = lib.pamc204_query_actual_position(1, 1)
if pos != INT_MIN:
    print(f"実位置: {pos}")

status = lib.pamc204_query_motion_status(1, 1)
if status == 1:
    print("停止中")
elif status == 0:
    print("動作中")
else:
    print("取得失敗")
```

---

## 4チャンネル同時操作 API

`send_commands_batch()` を使用して1回のポート開閉で全軸コマンドを送信します。

C API の `query_*_all_channels` は C 言語の制約上、配列出力引数を使用します。
C++ API は `std::vector<int>` を返します。

| No | API名 | 説明 |
|----|-------|------|
| 1 | `move_relative_all_channels(addr, pos)` → `vector<string>` | 全CH同時相対移動 |
| 2 | `query_actual_position_all_channels(addr)` → `vector<int>` | 全CH実位置問い合わせ |
| 3 | `query_motion_status_all_channels(addr)` → `vector<int>` | 全CH動作状態確認 |
| 4 | `move_infinite_all_channels(addr, dir)` → `vector<string>` | 全CH無限移動 |
| 5 | `stop_motion_all_channels(addr)` → `vector<string>` | 全CH動作停止 |

### 使用例（Python）

```python
from ctypes import c_int

# 全CH同時相対移動
lib.pamc204_move_relative_all_channels(1, 500)

# 全CH実位置取得（配列出力引数）
positions = (c_int * 4)()
ok = lib.pamc204_query_actual_position_all_channels(1, positions)
if ok:
    for i, pos in enumerate(positions):
        print(f"CH{i+1}: {pos}")

# 全CH動作状態取得（配列出力引数）
statuses = (c_int * 4)()
ok = lib.pamc204_query_motion_status_all_channels(1, statuses)
if ok:
    for i, st in enumerate(statuses):
        label = {0: "動作中", 1: "停止", -1: "エラー"}.get(st, "不明")
        print(f"CH{i+1}: {label}")

# 全CH無限移動・停止
lib.pamc204_move_infinite_all_channels(1, b"+")
lib.pamc204_stop_motion_all_channels(1)
```

---

## パラメータ説明

| パラメータ | 意味 | 範囲 |
|-----------|------|------|
| `addr` / `xx` | デバイスアドレス | 1〜32 |
| `freq` / `nnnn` | 周波数（Hz） | 1〜1500 |
| `pulses` / `yyyy` | パルス数（0=連続） | 0〜9999 |
| `pulses` / `Xyyyyyy` | 拡張パルス数 | 1〜999999 |
| `ch` / `z` | チャンネル（rotate系） | A=CH1, B=CH2, C=CH3, D=CH4 |
| `ch` / `m` | チャンネル（NP系） | 1〜4 |
| `dir` / `n` | 移動方向 | `+` または `-` |
| `dac` | DAC値（電圧） | 1900=70V, 3000=110V, 4095=150V |
| `acc` | 加速度（steps/sec²） | 1〜150000 |
| `vel` | 速度（steps/sec） | 1〜1500 |
| `pos` | 位置（steps） | -2147483648〜+2147483647 |

---

## エラーメッセージ

| エラー | 説明 |
|--------|------|
| `Error Value Range` | 出力電圧の値が範囲外（70V〜150V） |
| `ERROR` | 回転方向、周波数、チャンネル指定が不正 |
| `ERROR1` | コマンド認識不可 |
| `ERROR4` | 6桁パルス数が範囲外（X000001〜X999999） |
| `ERROR5` | 4桁パルス数が範囲外（0001〜9999） |
| `BUSY` | ドライバ駆動中（停止後に再送信） |

---

## Python ctypes 完全セットアップ例

### Linux（libpamc204.so）

```python
from ctypes import CDLL, c_char_p, c_bool, c_int, c_char, create_string_buffer

lib = CDLL("./build/libpamc204.so")

# シグネチャ設定
lib.pamc204_send_command.restype  = c_bool
lib.pamc204_send_command.argtypes = [c_char_p, c_char_p, c_int]

lib.pamc204_move_relative.restype  = c_bool
lib.pamc204_move_relative.argtypes = [c_int, c_int, c_int]

lib.pamc204_query_actual_position.restype  = c_int
lib.pamc204_query_actual_position.argtypes = [c_int, c_int]

lib.pamc204_query_motion_status.restype  = c_int
lib.pamc204_query_motion_status.argtypes = [c_int, c_int]

lib.pamc204_query_actual_position_all_channels.restype  = c_bool
lib.pamc204_query_actual_position_all_channels.argtypes = [c_int, c_int * 4]

lib.pamc204_query_motion_status_all_channels.restype  = c_bool
lib.pamc204_query_motion_status_all_channels.argtypes = [c_int, c_int * 4]

# 使用例
lib.pamc204_move_relative(1, 1, 500)

pos = lib.pamc204_query_actual_position(1, 1)   # int値を直接取得
st  = lib.pamc204_query_motion_status(1, 1)     # 0=動作中, 1=停止, -1=失敗

positions = (c_int * 4)()
lib.pamc204_query_actual_position_all_channels(1, positions)

statuses = (c_int * 4)()
lib.pamc204_query_motion_status_all_channels(1, statuses)
```

### Windows（pamc204.dll）

```python
from ctypes import CDLL, c_char_p, c_int, c_char
from ctypes import wintypes

lib = CDLL("./pamc204.dll")

# シグネチャ設定
lib.pamc204_send_command.restype  = wintypes.BOOL
lib.pamc204_send_command.argtypes = [c_char_p, c_char_p, c_int]

lib.pamc204_move_relative.restype  = wintypes.BOOL
lib.pamc204_move_relative.argtypes = [wintypes.INT, wintypes.INT, wintypes.INT]

lib.pamc204_query_actual_position.restype  = c_int
lib.pamc204_query_actual_position.argtypes = [wintypes.INT, wintypes.INT]

lib.pamc204_query_motion_status.restype  = c_int
lib.pamc204_query_motion_status.argtypes = [wintypes.INT, wintypes.INT]

lib.pamc204_query_actual_position_all_channels.restype  = wintypes.BOOL
lib.pamc204_query_actual_position_all_channels.argtypes = [wintypes.INT, wintypes.INT * 4]

lib.pamc204_query_motion_status_all_channels.restype  = wintypes.BOOL
lib.pamc204_query_motion_status_all_channels.argtypes = [wintypes.INT, wintypes.INT * 4]

# 使用例
lib.pamc204_move_relative(1, 1, 500)

pos = lib.pamc204_query_actual_position(1, 1)   # int値を直接取得
st  = lib.pamc204_query_motion_status(1, 1)     # 0=動作中, 1=停止, -1=失敗

positions = (wintypes.INT * 4)()
lib.pamc204_query_actual_position_all_channels(1, positions)

statuses = (wintypes.INT * 4)()
lib.pamc204_query_motion_status_all_channels(1, statuses)
```
