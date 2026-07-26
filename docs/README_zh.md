# Hiragana LipSync

[English](README.md) | [日本語](README_ja.md) | [中文](README_zh.md)

Hiragana LipSync 是一款 Windows 桌面应用，可分析日语语音并为 MMD／VRM 工作流程生成口型同步动画。它支持 WAV 和 MP3 音频，通过 ONNX 模型识别日语音素，再将结果转换为口型关键帧。

## 主要功能

- 导出 MMD Vocaloid Motion Data（`.vmd`）和 VRM Animation（`.vrma`）
- 生成 A／I／U／E／O／N 六种口型
- 支持拖放或文件选择方式导入 WAV／MP3
- 可分别调整每种口型的张开程度
- 可设置 -30 至 +30 帧的时机补偿
- 每帧最多可混合1至6种口型
- 输出帧率可选10／15／30 FPS
- 可选自动眼部动画
- 日语、英语、中文界面
- 使用 ONNX Runtime 进行 CPU 推理

## 运行要求

- Windows
- 随附的 Python 3.11 运行环境，或单独准备的 Python 3.11 环境
- `model/phoneme.onnx`
- `model/phoneme_tokenizer/tokenizer.json`

发布文件夹中包含应用运行环境和模型文件。请保持原有文件夹结构。

## 启动应用

双击发布文件夹中的 `START.bat`。

也可以运行：

```powershell
.\python\python.exe .\hiragana_lipsync_main.py
```

应用包含两个选项卡：

- **转换** — 选择音频、调整动画设置并导出动作文件。
- **依赖关系** — 检查、安装或卸载随附运行环境所用的处理软件包。

## 安装依赖关系

“依赖关系”选项卡管理以下固定版本：

| 软件包 | 版本 | 用途 |
| --- | ---: | --- |
| NumPy | 2.2.6 | 音频和关键帧数组 |
| SciPy | 1.16.3 | 音频重采样 |
| PyAV | 16.0.1 | MP3 解码 |
| ONNX Runtime | 1.24.4 | 音素模型推理 |

### 随附运行环境的替代命令

如果不使用“依赖关系”选项卡中的按钮，可执行：

```powershell
.\python\python.exe -m pip install --no-warn-script-location numpy==2.2.6 scipy==1.16.3 av==16.0.1 onnxruntime==1.24.4
```

卸载相同依赖关系：

```powershell
.\python\python.exe -m pip uninstall -y numpy scipy av onnxruntime
```

### 使用独立 Python 环境

图形界面还需要 PySide6 Essentials。不使用随附运行环境时：

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install PySide6-Essentials==6.11.1 numpy==2.2.6 scipy==1.16.3 av==16.0.1 onnxruntime==1.24.4
.\.venv\Scripts\python.exe -c "from src.window import main; main()"
```

该直接模块命令可避开启动器自动切换到随附 `python` 运行环境的行为。

从该环境中卸载全部应用依赖关系：

```powershell
.\.venv\Scripts\python.exe -m pip uninstall -y PySide6-Essentials shiboken6 numpy scipy av onnxruntime
```

这些命令只修改指定的 Python 环境，不会删除应用本体、模型文件或已生成的动作文件。

## 使用方法

1. 启动应用。
2. 打开**依赖关系**选项卡，安装缺少的处理软件包。
3. 返回**转换**选项卡。
4. 将一个 `.wav` 或 `.mp3` 文件拖入音频区域，或点击该区域选择文件。
5. 根据需要调整设置。
6. 点击 **Audio to .vmd** 或 **Audio to .vrma**。
7. 等待状态显示“转换完成”。

生成文件会自动保存到当前用户的 `Downloads` 文件夹：

```text
<源文件名>_lipsync.vmd
<源文件名>_lipsync.vrma
```

如果存在同名文件，程序会将其覆盖。

## 设置

| 设置 | 范围／选项 | 默认值 |
| --- | --- | --- |
| 口的张开程度 | A、I、U、E、O、N分别为0.0–1.0 | 元音1.0，N为0.5 |
| 时机补偿 | -30至+30提前帧 | +5 |
| 每帧最大口形种类数 | 1–6 | 2 |
| 输出FPS | 10、15、30 | 30 |
| 眼部动画 | 关闭／开启 | 关闭 |

重置按钮可恢复默认设置。所选界面语言保存在 `src/config.json` 中。

## 输出兼容性

- VMD 使用“あ”“い”“う”“え”“お”“ん”作为口型名称。
- VRMA 使用标准表情预设 `aa`、`ih`、`ou`、`ee`、`oh`。
- 启用眼部动画后，VMD 会包含眼部变形／骨骼动画，VRMA 会包含 `blink` 表情轨道。
- 推理前，音频会在内部转换为单声道、16 kHz 采样。

## 故障排除

### 依赖关系显示“未安装”

请通过“依赖关系”选项卡安装固定版本，或使用上面的随附运行环境安装命令。版本与固定版本不一致时，也会显示为“未安装”。

### 无法打开 MP3

请确认已安装 `av==16.0.1`。WAV 输入不需要 PyAV。

### 提示没有模型

请确认 `model/phoneme.onnx` 和 `model/phoneme_tokenizer/tokenizer.json` 位于应用文件夹中的指定位置。

### 在音频文件旁找不到输出

输出始终保存到当前用户的 `Downloads` 文件夹，而不是输入音频所在位置。

## 项目结构

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

## 致谢

- 音素模型：[TylorShine/wavlm-base-plus-hiragana-ctc-v2](https://huggingface.co/TylorShine/wavlm-base-plus-hiragana-ctc-v2) — CC BY-SA 3.0
- 眼部动画参考：[「何もしない」まばたき＆呼吸モーション](https://booth.pm/ja/items/6123352)，作者：かんな@MMD

