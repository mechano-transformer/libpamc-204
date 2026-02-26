# ユニットテスト実行方法

## 概要

`tests/test_api_unit.py` は以下をテストします：

- `send_command` / `send_commands_batch` のモックテスト（デバイス不要）
- query系 API のレスポンスパースロジック
- コマンド文字列の生成ロジック（`E011PR500` 等のフォーマット検証）
- ビルド済みライブラリを使った型チェック（ライブラリが存在する場合のみ）

---

## ローカル実行

```bash
# pytest をインストール
pip install pytest

# テスト実行
python -m pytest tests/test_api_unit.py -v
```

---

## Docker で実行（デバイス・ビルド環境不要）

モックテストのみ実行する場合は Docker を使うと環境構築不要です。

```bash
# ワンライナー（プロジェクトルートで実行）
docker run --rm \
  -v "$(pwd):/work" \
  -w /work \
  python:3.12-slim \
  sh -c "pip install pytest -q && python -m pytest tests/test_api_unit.py -v"
```

### Windows PowerShell の場合

```powershell
docker run --rm `
  -v "${PWD}:/work" `
  -w /work `
  python:3.12-slim `
  sh -c "pip install pytest -q && python -m pytest tests/test_api_unit.py -v"
```

---

## ビルド済みライブラリを使ったテスト

`build/libpamc204.so`（Linux）または `build/Release/pamc204.dll`（Windows）が存在する場合、
ライブラリの型チェックテストも自動的に実行されます。

```bash
# Linux: ビルド後にテスト実行
mkdir -p build && cd build && cmake .. && cmake --build . && cd ..
python -m pytest tests/test_api_unit.py -v
```

デバイスが接続されていない場合、実機テストは「失敗」ではなく「デバイス未接続」として扱われます。

---

## テスト構成

| テストクラス | 内容 | デバイス必要 |
|-------------|------|-------------|
| `TestSendCommandMock` | send_command / send_commands_batch のモックテスト | 不要 |
| `TestQueryApiParsing` | query系 API のレスポンスパースロジック | 不要 |
| `TestCommandStringGeneration` | コマンド文字列フォーマット検証 | 不要 |
| `TestWithLibrary` | ビルド済みライブラリの型チェック | 不要（ライブラリのみ必要） |
