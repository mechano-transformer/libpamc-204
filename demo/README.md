# Autocollimator & PAMC-204 Alignment Demo

オートコリメータ（自動準直器）と PAMC-204 ピエゾモーターコントローラーを組み合わせた、
**自動ドリフト補正（ADC: Automated Drift Correction）** デモアプリケーションです。

---

## 何をするプログラムか

| 機能 | 説明 |
| --- | --- |
| **オートコリメータ読み取り** | シリアル通信でオートコリメータから X/Y 傾き角度を連続取得し、リアルタイム表示する |
| **PAMC-204 手動制御** | PAMC-204 DLL 経由でピエゾモーターを手動で相対/絶対移動・停止・ホーム設定できる |
| **自動ドリフト補正（ADC）** | オートコリメータの誤差をゼロに近づけるよう、PAMC-204 を自動制御する（勾配降下法） |
| **ポジションルーティン** | 事前定義された複数の目標位置を順番に移動し、各位置で ADC 収束を待つ自動シーケンス |
| **データロギング** | 測定データ（時刻・X/Y 角度）を CSV 形式でファイル保存する |

### ADC（自動ドリフト補正）の動作原理

```text
オートコリメータ → 角度誤差を計算 → PAMC-204 ch1/ch2 を順次駆動 → 誤差を縮小
```

- PAMC-204 は **同時2軸駆動非対応** のため、X軸 → Y軸 の順に **順次駆動**
- **モーター速度: 1500 Hz 固定**（接続時に全チャンネルへ自動設定）
- キャリブレーション: 1000パルス ≈ 2.74 単位角度（≈ 365 pulses/unit）

---

## ファイル構成

```text
demo/
├── __init__.py          # パッケージ初期化
├── main.py              # エントリーポイント ← ここから起動
├── gui.py               # メイン GUI クラス（ADCGUI）
├── pamc204_wrapper.py   # PAMC-204 DLL ラッパー（PAMC204 クラス）
├── ac_thread.py         # オートコリメータ読み取りスレッド（AcThread）
├── adc_thread.py        # ADC 制御スレッド（ADCControlThread）
└── position_routine.py  # ポジションルーティンスレッド（PositionRoutineThread）
```

---

## 必要環境

- **OS**: Windows（PAMC-204 DLL は Windows 専用）
- **Python**: 3.10 以上
- **依存ライブラリ**:

```bash
pip install pyserial numpy
```

- **PAMC-204 DLL**: 配布済みの `pamc204.dll` を `demo/` フォルダに配置すること

---

## 実行方法

```bash
# 1. pamc204.dll を demo/ フォルダに配置する

# 2. demo/ フォルダに移動
cd demo

# 3. 起動
python main.py --dll ./pamc204.dll
```

---

## 操作手順

### 1. オートコリメータ接続

1. **Autocollimator** パネルの「Refresh Ports」をクリック
2. COM ポートを選択（選択と同時に接続・単位取得）
3. 「Start Reading」をクリックして連続読み取り開始

### 2. PAMC-204 接続

1. **PAMC-204 Piezo Motor Control** パネルの「Address」に PAMC-204 のアドレスを入力（デフォルト: 1）
2. 「Connect PAMC-204」をクリック
   - 接続成功: ステータスが緑色に変わる
   - **全チャンネルのモーター速度が 1500 Hz に自動設定される**
3. 切断するときは「Disconnect」をクリック

### 3. 手動操作

| ボタン | 動作 |
| --- | --- |
| Set Home | 現在位置をホームポジション（0）に設定 |
| Move (Rel) | 入力パルス数だけ相対移動 |
| Move (Abs) | 指定絶対位置へ移動 |
| Stop | 動作停止 |
| Position? | 現在位置を問い合わせて表示 |

- **Axis 1 / Axis 2** ラジオボタンで操作対象軸を選択

### 4. ADC（自動ドリフト補正）

1. オートコリメータ読み取りと PAMC-204 接続が完了していることを確認
2. **ADC Parameters** を必要に応じて調整
3. 「Start ADC」をクリック → 自動補正開始
4. 「Stop ADC」で停止

### 5. ポジションルーティン

1. 上記 1〜2 の接続と「Start Reading」が完了していることを確認
2. **Autocollimator** パネルの「Position Routine」をクリック
3. 以下の順序で自動移動・収束待ち・ホールドを繰り返す:
   - `(+7.0, -7.0)` → 2秒ホールド
   - `(-7.0, -7.0)` → 2秒ホールド
   - `(-7.0, +7.0)` → 2秒ホールド
   - `(+7.0, +7.0)` → 2秒ホールド
   - `(0.0,  0.0)` → 原点復帰

### 6. データロギング

1. 「Start Test」でロギング開始
2. 「Stop Test」で停止
3. 「Save Data to File」で `.txt` ファイルに保存（タブ区切り: `Time(s) / alnx / alny`）

---

## ADC パラメータ説明

| パラメータ | デフォルト | 説明 |
| --- | --- | --- |
| Sample Period (s) | 0.5 | ADC 制御ループの周期（秒） |
| Learning Rate | 0.3 | 補正ステップの大きさ（0〜1） |
| Min Step (pulses) | 1 | 最小補正パルス数 |
| Max Step (pulses) | 500 | 最大補正パルス数 |
| Piezo Calibration | 365 | 1単位角度あたりのパルス数 |
| Convergence Threshold | 0.01 | 収束判定の誤差閾値 |

---

## 軸設定

| 設定 | 説明 |
| --- | --- |
| Reverse Axis 1 | 軸1のパルス方向を反転 |
| Reverse Axis 2 | 軸2のパルス方向を反転 |
| Swap X/Y Axes | X/Y 軸の割り当てを入れ替え（デフォルト: X→ch2, Y→ch1） |
