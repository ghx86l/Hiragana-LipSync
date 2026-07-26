# Hiragana LipSync

[English](README.md) | [日本語](README_ja.md) | [中文](README_zh.md)

Hiragana LipSyncは、日本語音声を解析し、MMD／VRM向けのリップシンクアニメーションを生成するWindowsデスクトップアプリです。WAVまたはMP3から日本語音素をONNXモデルで検出し、口形キーフレームへ変換します。

## 主な機能

- MMD Vocaloid Motion Data（`.vmd`）とVRM Animation（`.vrma`）を出力
- 「あ・い・う・え・お・ん」の6口形を生成
- WAV／MP3をドラッグ＆ドロップまたはファイル選択で入力
- 口形ごとの開き具合を調整
- -30～+30フレームのタイミング補正
- 1フレームあたりの最大口形数を1～6から指定
- 出力FPSを10／15／30から選択
- 自動目アニメーションを追加可能
- 日本語・英語・中国語の画面表示
- ONNX RuntimeによるCPU推論

## 動作要件

- Windows
- 同梱のPython 3.11ランタイム、または別途用意したPython 3.11環境
- `model/phoneme.onnx`
- `model/phoneme_tokenizer/tokenizer.json`

配布フォルダにはランタイムとモデルが含まれています。フォルダ構成を保ったまま使用してください。

## 起動方法

配布フォルダ内の`START.bat`をダブルクリックします。

コマンドから起動する場合：

```powershell
.\python\python.exe .\hiragana_lipsync_main.py
```

アプリには2つのタブがあります。

- **変換** — 音声選択、アニメーション設定、モーション出力を行います。
- **依存関係** — 同梱ランタイムで使用する処理パッケージの状態確認、インストール、アンインストールを行います。

## 依存関係のインストール

「依存関係」タブは次の固定バージョンを管理します。

| パッケージ | バージョン | 用途 |
| --- | ---: | --- |
| NumPy | 2.2.6 | 音声・キーフレーム配列 |
| SciPy | 1.16.3 | 音声リサンプリング |
| PyAV | 16.0.1 | MP3デコード |
| ONNX Runtime | 1.24.4 | 音素モデル推論 |

### 同梱ランタイム用の代替コマンド

「依存関係」タブのボタンを使わずに導入する場合：

```powershell
.\python\python.exe -m pip install --no-warn-script-location numpy==2.2.6 scipy==1.16.3 av==16.0.1 onnxruntime==1.24.4
```

同じ依存関係をアンインストールする場合：

```powershell
.\python\python.exe -m pip uninstall -y numpy scipy av onnxruntime
```

### 別Python環境を使う代替手順

GUIにはPySide6 Essentialsも必要です。同梱ランタイムを使わない場合：

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install PySide6-Essentials==6.11.1 numpy==2.2.6 scipy==1.16.3 av==16.0.1 onnxruntime==1.24.4
.\.venv\Scripts\python.exe -c "from src.window import main; main()"
```

この直接モジュール起動コマンドは、ランチャーが同梱`python`へ自動的に切り替える動作を回避します。

その環境からアプリ用依存関係をすべてアンインストールする場合：

```powershell
.\.venv\Scripts\python.exe -m pip uninstall -y PySide6-Essentials shiboken6 numpy scipy av onnxruntime
```

各コマンドが変更するのは、指定したPython環境だけです。アプリ本体、モデル、生成済みモーションは削除されません。

## 使い方

1. アプリを起動します。
2. **依存関係**タブを開き、不足している処理パッケージをインストールします。
3. **変換**タブへ戻ります。
4. `.wav`または`.mp3`を1ファイル、音声エリアへドロップするか、エリアをクリックして選択します。
5. 必要に応じて設定を調整します。
6. **Audio to .vmd**または**Audio to .vrma**をクリックします。
7. 「変換完了」と表示されるまで待ちます。

生成ファイルは、現在のユーザーの`Downloads`フォルダへ自動保存されます。

```text
<入力ファイル名>_lipsync.vmd
<入力ファイル名>_lipsync.vrma
```

同名ファイルがある場合は上書きされます。

## 設定

| 設定 | 範囲／選択肢 | 初期値 |
| --- | --- | --- |
| 口の開き具合 | A・I・U・E・O・Nごとに0.0～1.0 | 母音1.0、Nのみ0.5 |
| タイミング補正 | -30～+30先行フレーム | +5 |
| 各フレームの最大口形種類数 | 1～6 | 2 |
| 出力FPS | 10、15、30 | 30 |
| 目のアニメーション | オフ／オン | オフ |

リセットボタンで初期値へ戻せます。選択した画面言語は`src/config.json`へ保存されます。

## 出力仕様

- VMDの口形名は「あ」「い」「う」「え」「お」「ん」です。
- VRMAは標準表情プリセット`aa`、`ih`、`ou`、`ee`、`oh`を使用します。
- 目のアニメーションを有効にすると、VMDには目モーフ／ボーン、VRMAには`blink`表情トラックが追加されます。
- 音声は推論前にモノラル・16 kHzへ内部変換されます。

## トラブルシューティング

### 依存関係が「未導入」と表示される

「依存関係」タブ、または上記の同梱ランタイム用インストールコマンドを使用してください。固定バージョンと異なるパッケージも「未導入」と判定されます。

### MP3を開けない

`av==16.0.1`が導入されていることを確認してください。WAV入力ではPyAVを使用しません。

### 「モデルがありません」と表示される

`model/phoneme.onnx`と`model/phoneme_tokenizer/tokenizer.json`がアプリフォルダ内の所定位置にあることを確認してください。

### 入力音声と同じ場所に出力が見つからない

出力先は入力音声の隣ではなく、常に現在のユーザーの`Downloads`フォルダです。

## フォルダ構成

```text
Hiragana-LipSync/
├─ hiragana_lipsync_main.py
├─ START.bat
├─ icon/
├─ img/
├─ model/
│  ├─ phoneme.onnx
│  └─ phoneme_tokenizer/tokenizer.json
├─ python/
└─ src/
```

## クレジット

- 音素モデル：[TylorShine/wavlm-base-plus-hiragana-ctc-v2](https://huggingface.co/TylorShine/wavlm-base-plus-hiragana-ctc-v2) — CC BY-SA 3.0
- 目アニメーション参考：[「何もしない」まばたき＆呼吸モーション](https://booth.pm/ja/items/6123352) かんな@MMD

