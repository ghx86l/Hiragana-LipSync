import json
import math
import os
import struct
import tempfile
import wave
from pathlib import Path

import numpy as np
from scipy.signal import resample_poly


FPS = 30
RATE = 16000
VMD_MODEL_NAME = "hiragana-lipsync"
MORPHS = ("\u3042", "\u3044", "\u3046", "\u3048", "\u304a", "\u3093")
VOWELS = {
    "a": "\u3042",
    "A": "\u3042",
    "i": "\u3044",
    "I": "\u3044",
    "u": "\u3046",
    "U": "\u3046",
    "e": "\u3048",
    "E": "\u3048",
    "o": "\u304a",
    "O": "\u304a",
    "N": "\u3093",
}
CLOSERS = {"p", "py", "b", "by", "m", "my", "pau"}
DOMINANT_RATIO = 0.40
MAX_ACTIVE_MORPHS = 2
RELEASE_DECAY = 0.45
LEAD_FRAMES = 5
SUPPORTED_AUDIO = {".wav", ".mp3"}


def output_path(name):
    value = name.strip()
    if not value or Path(value).name != value or value in {".", ".."}:
        raise ValueError("出力VMD名を入力してください。")
    if Path(value).suffix.lower() != ".vmd":
        value += ".vmd"
    return Path.home() / "Downloads" / value


def fixed_string(value, size):
    encoded = value.encode("cp932", errors="replace")[:size]
    return encoded + b"\0" * (size - len(encoded))


def read_wav(path):
    with wave.open(str(path), "rb") as source:
        channels = source.getnchannels()
        source_rate = source.getframerate()
        width = source.getsampwidth()
        raw = source.readframes(source.getnframes())

    if width == 1:
        audio = (np.frombuffer(raw, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
    elif width == 2:
        audio = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    elif width == 3:
        values = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3)
        audio = values[:, 0].astype(np.int32)
        audio |= values[:, 1].astype(np.int32) << 8
        audio |= values[:, 2].astype(np.int32) << 16
        audio = np.where(audio & 0x800000, audio - 0x1000000, audio).astype(np.float32)
        audio /= 8388608.0
    elif width == 4:
        audio = np.frombuffer(raw, dtype="<i4").astype(np.float32) / 2147483648.0
    else:
        raise ValueError(f"未対応のWAVビット深度です: {width * 8}")

    if channels > 1:
        audio = audio.reshape(-1, channels).mean(axis=1)
    return resample(audio, source_rate)


def read_mp3(path):
    try:
        import av
    except ImportError as error:
        raise RuntimeError("MP3の読み込みにはPyAVが必要です。") from error

    samples = []
    with av.open(str(path)) as container:
        if not container.streams.audio:
            raise ValueError("音声ストリームが見つかりません。")
        resampler = av.audio.resampler.AudioResampler(format="fltp", layout="mono", rate=RATE)
        for frame in container.decode(container.streams.audio[0]):
            for converted in resampler.resample(frame):
                samples.append(converted.to_ndarray().reshape(-1))
        for converted in resampler.resample(None):
            samples.append(converted.to_ndarray().reshape(-1))
    if not samples:
        raise ValueError("MP3から音声を読み込めませんでした。")
    return np.concatenate(samples).astype(np.float32, copy=False)


def resample(audio, source_rate):
    if source_rate == RATE:
        return audio.astype(np.float32, copy=False)
    divisor = math.gcd(source_rate, RATE)
    return resample_poly(audio, RATE // divisor, source_rate // divisor).astype(np.float32)


def read_audio(path):
    path = Path(path)
    extension = path.suffix.lower()
    if extension == ".wav":
        return read_wav(path)
    if extension == ".mp3":
        return read_mp3(path)
    raise ValueError("WAVまたはMP3を指定してください。")


def rms_frames(audio, frame_count):
    samples_per_frame = RATE / FPS
    values = np.zeros(frame_count, dtype=np.float32)
    for frame in range(frame_count):
        start = int(round(frame * samples_per_frame))
        end = min(len(audio), int(round((frame + 1) * samples_per_frame)))
        if end > start:
            values[frame] = math.sqrt(float(np.mean(audio[start:end] ** 2)))
    return values


def active_energy(audio, frame_count):
    values = rms_frames(audio, frame_count)
    smoothed = np.convolve(values, np.ones(3, dtype=np.float32) / 3.0, mode="same")
    peak = max(float(np.percentile(smoothed, 92)), 1e-8)
    floor = float(np.percentile(smoothed, 12))
    threshold = max(floor * 1.7, peak * 0.018)
    level = np.clip((smoothed - threshold) / max(peak - threshold, 1e-8), 0.0, 1.0)
    return level, threshold


def vocabularies(model_dir):
    tokenizer = model_dir / "phoneme_tokenizer" / "tokenizer.json"
    data = json.loads(tokenizer.read_text(encoding="utf-8"))
    vocab = data["model"]["vocab"]
    return {int(index): token for token, index in vocab.items()}


def infer_probabilities(audio, model_dir, device, progress):
    import torch
    from transformers import AutoFeatureExtractor, AutoModel

    os.environ["HF_MODULES_CACHE"] = str(Path(tempfile.gettempdir()) / "hiragana_lipsync")
    print(f"Loading WavLM model on {device}.")
    extractor = AutoFeatureExtractor.from_pretrained(str(model_dir), local_files_only=True)
    model = AutoModel.from_pretrained(
        str(model_dir), trust_remote_code=True, local_files_only=True
    ).eval().to(device)
    id_to_token = vocabularies(model_dir)
    blank_id = 0
    chunk_samples = 14 * RATE
    overlap_samples = RATE
    step_samples = chunk_samples - overlap_samples
    batches = []
    starts = list(range(0, len(audio), step_samples))

    with torch.inference_mode():
        for number, start in enumerate(starts, start=1):
            end = min(len(audio), start + chunk_samples)
            chunk = audio[start:end]
            if len(chunk) < RATE // 2:
                break
            inputs = extractor(chunk, sampling_rate=RATE, return_tensors="pt")
            values = inputs["input_values"].to(device)
            outputs = model(input_values=values)
            logits = outputs["phoneme_logits"][0]
            phone_ids = [token_id for token_id in sorted(id_to_token) if token_id != blank_id and token_id < logits.shape[-1]]
            if not phone_ids:
                raise RuntimeError("モデル出力に既知の音素IDがありません。")
            reduced = logits[:, phone_ids].transpose(0, 1).unsqueeze(0)
            reduced = torch.nn.functional.avg_pool1d(reduced, kernel_size=5, stride=1, padding=2)
            probabilities = torch.softmax(reduced.squeeze(0).transpose(0, 1), dim=-1).cpu().numpy()
            local_times = np.arange(len(probabilities), dtype=np.float32) * (len(chunk) / RATE / len(probabilities))
            left = 0.0 if start == 0 else overlap_samples / RATE / 2
            right = len(chunk) / RATE if end == len(audio) else len(chunk) / RATE - left
            selected = (local_times >= left) & (local_times < right)
            batches.append((start / RATE + local_times[selected], probabilities[selected]))
            progress(int(number / len(starts) * 65))
            print(f"Analysed {number}/{len(starts)} audio chunks.")
            if end == len(audio):
                break

    if not batches:
        raise ValueError("音声が短すぎます。")
    times = np.concatenate([item[0] for item in batches])
    probabilities = np.concatenate([item[1] for item in batches])
    del model
    if device == "cuda":
        torch.cuda.empty_cache()
    tokens = {index: id_to_token[token_id] for index, token_id in enumerate(phone_ids)}
    return times, probabilities, tokens


def make_weights(audio, times, probabilities, id_to_token):
    frame_count = max(2, int(math.ceil(len(audio) / RATE * FPS)))
    levels, threshold = active_energy(audio, frame_count)
    weights = np.zeros((frame_count, len(MORPHS)), dtype=np.float32)
    index = {name: number for number, name in enumerate(MORPHS)}
    vowel_ids = [(token_id, VOWELS[token]) for token_id, token in id_to_token.items() if token in VOWELS]
    closer_ids = [token_id for token_id, token in id_to_token.items() if token in CLOSERS]

    for frame in range(frame_count):
        start = frame / FPS
        end = (frame + 1) / FPS
        selected = (times >= start) & (times < end)
        if not np.any(selected):
            nearest = int(np.argmin(np.abs(times - (start + end) / 2)))
            selected = np.zeros(len(times), dtype=bool)
            selected[nearest] = True
        current = probabilities[selected].mean(axis=0)
        close_score = float(current[closer_ids].sum()) if closer_ids else 0.0
        if levels[frame] < 0.055 or close_score >= 0.50:
            continue
        scores = np.zeros(len(MORPHS), dtype=np.float32)
        for token_id, morph in vowel_ids:
            scores[index[morph]] += current[token_id]
        total = float(scores.sum())
        if total < 0.055:
            continue
        scores /= total
        cutoff = float(scores.max()) * DOMINANT_RATIO
        scores[scores < cutoff] = 0.0
        order = np.argsort(scores)[::-1]
        scores[order[MAX_ACTIVE_MORPHS:]] = 0.0
        total = float(scores.sum())
        if total <= 0.0:
            continue
        scores /= total
        weights[frame] = scores * (0.16 + 0.84 * levels[frame])
        weights[frame, index["\u3093"]] = min(weights[frame, index["\u3093"]], 0.5)

    result = np.zeros_like(weights)
    for frame in range(frame_count):
        previous = result[frame - 1] if frame else np.zeros(len(MORPHS), dtype=np.float32)
        if np.any(weights[frame]):
            if np.any(previous):
                result[frame] = previous * 0.30 + weights[frame] * 0.70
            else:
                result[frame] = weights[frame]
        else:
            result[frame] = previous * RELEASE_DECAY
            result[frame][result[frame] < 0.02] = 0.0
    if LEAD_FRAMES > 0:
        result[:-LEAD_FRAMES] = result[LEAD_FRAMES:]
        result[-LEAD_FRAMES:] = 0.0
    result[0] = 0.0
    result[-1] = 0.0
    return result, threshold


KEY_TOLERANCE = 0.01


def reduce_morph_keys(values):
    points = [(frame, float(value)) for frame, value in enumerate(values)]
    if len(points) <= 2:
        return points
    keep = [False] * len(points)
    keep[0] = True
    keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        low, high = stack.pop()
        if high <= low + 1:
            continue
        low_frame, low_value = points[low]
        high_frame, high_value = points[high]
        span = high_frame - low_frame
        worst = KEY_TOLERANCE
        chosen = -1
        for frame in range(low + 1, high):
            current_frame, current_value = points[frame]
            if span == 0:
                predicted = low_value
            else:
                predicted = low_value + (high_value - low_value) * (current_frame - low_frame) / span
            deviation = abs(current_value - predicted)
            if deviation > worst:
                worst = deviation
                chosen = frame
        if chosen != -1:
            keep[chosen] = True
            stack.append((low, chosen))
            stack.append((chosen, high))
    return [points[frame] for frame in range(len(points)) if keep[frame]]

def write_vmd(path, weights):
    with Path(path).open("wb") as output:
        output.write(b"Vocaloid Motion Data 0002\0\0\0\0\0")
        output.write(fixed_string(VMD_MODEL_NAME, 20))
        output.write(struct.pack("<I", 0))
        morph_keys = [
            (morph, reduce_morph_keys(weights[:, index]))
            for index, morph in enumerate(MORPHS)
        ]
        output.write(struct.pack("<I", sum(len(keys) for _, keys in morph_keys)))
        for morph, keys in morph_keys:
            for frame, value in keys:
                output.write(fixed_string(morph, 15))
                output.write(struct.pack("<If", frame, value))
        output.write(struct.pack("<IIII", 0, 0, 0, 0))


def generate(audio_path, output, model_dir, use_gpu, progress):
    audio = read_audio(audio_path)
    progress(5)
    print(f"Loaded {len(audio) / RATE:.2f} seconds of audio at 16 kHz.")
    device = "cuda" if use_gpu else "cpu"
    if use_gpu:
        import torch

        if not torch.cuda.is_available():
            raise RuntimeError("Use GPU (beta) が有効ですが、CUDA GPUを利用できません。")
    times, probabilities, vocabulary = infer_probabilities(audio, Path(model_dir), device, progress)
    progress(75)
    weights, threshold = make_weights(audio, times, probabilities, vocabulary)
    progress(90)
    write_vmd(output, weights)
    progress(100)
    result = {
        "duration": len(audio) / RATE,
        "frames": len(weights),
        "closed": int(np.count_nonzero(np.max(weights, axis=1) == 0.0)),
        "threshold": threshold,
    }
    print(f"Finished: {result}")
    return result