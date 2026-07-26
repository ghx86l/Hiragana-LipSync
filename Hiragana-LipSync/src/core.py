import json
import math
import os
import struct
import wave
from pathlib import Path

import numpy as np
from scipy.signal import resample_poly

from .const import DEFAULTS, MORPHS, PRESET_EXPRESSIONS, SUPPORTED_AUDIO, output_path


FPS = 30
RATE = 16000
VMD_MODEL_NAME = "hiragana-lipsync"
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
RELEASE_DECAY = 0.45
KEY_TOLERANCE = 0.01
EYE_PERIOD = 220
EYE_MORPHS = (
    (
        "\u307e\u3070\u305f\u304d",
        (
            (0, 0.07), (21, 0.07), (23, 0.15), (25, 0.1), (37, 0.07), (38, 0.66),
            (40, 1.0), (41, 0.65), (43, 0.0), (44, 0.07), (46, 1.0), (47, 0.65),
            (48, 0.13), (75, 0.13), (77, 0.15), (82, 0.15), (96, 0.15), (98, 0.0),
            (100, 0.08), (110, 0.08), (112, 0.13), (114, 0.0), (116, 0.08), (121, 0.08),
            (140, 0.07), (141, 0.66), (143, 1.0), (144, 0.65), (146, 0.0), (147, 0.07),
            (220, 0.07),
        ),
    ),
    (
        "\u4e0b",
        (
            (0, 0.05), (21, 0.05), (23, 0.1), (25, 0.05), (37, 0.05), (39, 0.22),
            (41, 0.31), (43, 0.0), (44, 0.11), (46, 0.25), (48, 0.06), (75, 0.06),
            (82, 0.13), (97, 0.13), (100, 0.06), (110, 0.06), (112, 0.2), (114, 0.2),
            (116, 0.06), (140, 0.05), (142, 0.22), (144, 0.31), (146, 0.0), (147, 0.11),
            (158, 0.06), (160, 0.1), (180, 0.1), (182, 0.07), (220, 0.05),
        ),
    ),
)
EYE_BONE_NAME = "\u4e21\u76ee"
EYE_INTERP = bytes.fromhex(
    "14140000141414146b6b6b6b6b6b6b6b141414141414146b6b6b6b6b6b6b6b0014141414"
    "14146b6b6b6b6b6b6b6b000014141414146b6b6b6b6b6b6b6b000000"
)
EYE_BONE_KEYS = (
    (0, (0.0, 0.0, 0.0), (0.0, -0.042987, 0.0, 0.999076)),
    (4, (0.0, 0.0, 0.0), (0.0, -0.041988, 0.0, 0.999119)),
    (6, (0.0, 0.0, 0.0), (0.0, -0.003, 0.0, 0.999997)),
    (20, (0.0, 0.0, 0.0), (0.0, -0.003, 0.0, 0.999997)),
    (23, (0.0, 0.0, 0.0), (0.0, 0.006, 0.0, 0.999983)),
    (26, (0.0, 0.0, 0.0), (0.0, -0.0095, 0.0, 0.999956)),
    (75, (0.0, 0.0, 0.0), (0.0, -0.0095, 0.0, 0.999956)),
    (77, (0.0, 0.0, 0.0), (0.0044, 0.0, 0.0, 0.99999)),
    (79, (0.0, 0.0, 0.0), (0.0044, 0.0, 0.0, 0.99999)),
    (81, (0.0, 0.0, 0.0), (-0.015499, -0.024994, 9.3e-05, 0.99957)),
    (94, (0.0, 0.0, 0.0), (-0.015499, -0.024994, 9.3e-05, 0.99957)),
    (96, (0.0, 0.0, 0.0), (-0.015498, -0.007499, -0.000178, 0.999854)),
    (98, (0.0, 0.0, 0.0), (0.0, -0.0095, 0.0, 0.999956)),
    (113, (0.0, 0.0, 0.0), (0.0, -0.0095, 0.0, 0.999957)),
    (115, (0.0, 0.0, 0.0), (0.0, 0.0005, 0.0, 1.000002)),
    (117, (0.0, 0.0, 0.0), (0.0, -0.0095, 0.0, 0.999956)),
    (124, (0.0, 0.0, 0.0), (0.0, -0.0095, 0.0, 0.999956)),
    (158, (0.0, 0.0, 0.0), (0.0, -0.0095, 0.0, 0.999956)),
    (160, (0.0, 0.0, 0.0), (-0.010499, -0.009499, -0.0001, 0.999901)),
    (180, (0.0, 0.0, 0.0), (-0.010499, -0.009499, -0.0001, 0.999901)),
    (182, (0.0, 0.0, 0.0), (0.0, -0.042987, 0.0, 0.999076)),
    (220, (0.0, 0.0, 0.0), (0.0, -0.042987, 0.0, 0.999076)),
)


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


def softmax(values):
    shifted = values - values.max(axis=-1, keepdims=True)
    exponent = np.exp(shifted)
    return exponent / exponent.sum(axis=-1, keepdims=True)


def smooth(values, width=5):
    kernel = np.ones(width, dtype=np.float32) / float(width)
    padded = np.zeros((values.shape[0] + width - 1, values.shape[1]), dtype=np.float32)
    padded[width // 2:width // 2 + values.shape[0]] = values
    output = np.empty_like(values)
    for column in range(values.shape[1]):
        output[:, column] = np.convolve(padded[:, column], kernel, mode="valid")
    return output


def report(message, status):
    print(message)
    status(message)


def infer_probabilities(audio, model_dir, progress, status):
    import onnxruntime

    graph = model_dir / "phoneme.onnx"
    if not graph.is_file():
        raise FileNotFoundError("model/phoneme.onnx が見つかりません。")
    report("Loading phoneme model on CPU.", status)
    options = onnxruntime.SessionOptions()
    options.graph_optimization_level = onnxruntime.GraphOptimizationLevel.ORT_ENABLE_ALL
    options.intra_op_num_threads = os.cpu_count() or 1
    session = onnxruntime.InferenceSession(
        str(graph), options, providers=["CPUExecutionProvider"]
    )
    id_to_token = vocabularies(model_dir)
    blank_id = 0
    chunk_samples = 14 * RATE
    overlap_samples = RATE
    step_samples = chunk_samples - overlap_samples
    batches = []
    starts = list(range(0, len(audio), step_samples))

    for number, start in enumerate(starts, start=1):
        end = min(len(audio), start + chunk_samples)
        chunk = audio[start:end]
        if len(chunk) < RATE // 2:
            break
        values = np.ascontiguousarray(chunk, dtype=np.float32)[None, :]
        logits = session.run(None, {"input_values": values})[0][0]
        phone_ids = [
            token_id
            for token_id in sorted(id_to_token)
            if token_id != blank_id and token_id < logits.shape[-1]
        ]
        if not phone_ids:
            raise RuntimeError("モデル出力に既知の音素IDがありません。")
        reduced = smooth(logits[:, phone_ids])
        probabilities = softmax(reduced)
        local_times = np.arange(len(probabilities), dtype=np.float32) * (
            len(chunk) / RATE / len(probabilities)
        )
        left = 0.0 if start == 0 else overlap_samples / RATE / 2
        right = len(chunk) / RATE if end == len(audio) else len(chunk) / RATE - left
        selected = (local_times >= left) & (local_times < right)
        batches.append((start / RATE + local_times[selected], probabilities[selected]))
        progress(int(number / len(starts) * 65))
        report(f"Analysed {number}/{len(starts)} audio chunks.", status)
        if end == len(audio):
            break

    if not batches:
        raise ValueError("音声が短すぎます。")
    times = np.concatenate([item[0] for item in batches])
    probabilities = np.concatenate([item[1] for item in batches])
    del session
    tokens = {index: id_to_token[token_id] for index, token_id in enumerate(phone_ids)}
    return times, probabilities, tokens


def make_weights(audio, times, probabilities, id_to_token, settings):
    frame_count = max(2, int(math.ceil(len(audio) / RATE * FPS)))
    levels, threshold = active_energy(audio, frame_count)
    weights = np.zeros((frame_count, len(MORPHS)), dtype=np.float32)
    index = {name: number for number, name in enumerate(MORPHS)}
    vowel_ids = [(token_id, VOWELS[token]) for token_id, token in id_to_token.items() if token in VOWELS]
    closer_ids = [token_id for token_id, token in id_to_token.items() if token in CLOSERS]
    scales = np.asarray(settings["scales"], dtype=np.float32)
    shapes = int(settings["shapes"])

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
        scores[order[shapes:]] = 0.0
        total = float(scores.sum())
        if total <= 0.0:
            continue
        scores /= total
        weights[frame] = scores * (0.16 + 0.84 * levels[frame]) * scales

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
    lead = int(settings["lead"])
    if lead != 0:
        shifted = np.zeros_like(result)
        if lead > 0:
            if lead < frame_count:
                shifted[: frame_count - lead] = result[lead:]
        else:
            delay = -lead
            if delay < frame_count:
                shifted[delay:] = result[: frame_count - delay]
        result = shifted
    result[0] = 0.0
    result[-1] = 0.0
    return result, threshold


def reduce_morph_keys(points):
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


def eye_morph_keys(frame_count):
    entries = []
    for name, keys in EYE_MORPHS:
        for base in range(0, frame_count, EYE_PERIOD):
            for frame, value in keys:
                target = base + frame
                if target < frame_count:
                    entries.append((name, target, value))
    return entries


def eye_bone_keys(frame_count):
    entries = []
    for base in range(0, frame_count, EYE_PERIOD):
        for frame, pos, rot in EYE_BONE_KEYS:
            target = base + frame
            if target < frame_count:
                entries.append((target, pos, rot))
    return entries


def write_vmd(path, weights, settings):
    frame_count = len(weights)
    stride = max(1, int(round(30 / int(settings["interval"]))))
    morph_keys = []
    for index, morph in enumerate(MORPHS):
        points = [(frame, float(weights[frame][index])) for frame in range(0, frame_count, stride)]
        if points[-1][0] != frame_count - 1:
            points.append((frame_count - 1, float(weights[frame_count - 1][index])))
        morph_keys.append((morph, reduce_morph_keys(points)))
    eye_morphs = eye_morph_keys(frame_count) if settings["eye"] else []
    eye_bones = eye_bone_keys(frame_count) if settings["eye"] else []
    with Path(path).open("wb") as output:
        output.write(b"Vocaloid Motion Data 0002\0\0\0\0\0")
        output.write(fixed_string(VMD_MODEL_NAME, 20))
        output.write(struct.pack("<I", len(eye_bones)))
        for frame, pos, rot in eye_bones:
            output.write(fixed_string(EYE_BONE_NAME, 15))
            output.write(struct.pack("<I", frame))
            output.write(struct.pack("<3f", *pos))
            output.write(struct.pack("<4f", *rot))
            output.write(EYE_INTERP)
        output.write(struct.pack("<I", sum(len(keys) for _, keys in morph_keys) + len(eye_morphs)))
        for morph, keys in morph_keys:
            for frame, value in keys:
                output.write(fixed_string(morph, 15))
                output.write(struct.pack("<If", frame, value))
        for name, frame, value in eye_morphs:
            output.write(fixed_string(name, 15))
            output.write(struct.pack("<If", frame, value))
        output.write(struct.pack("<IIII", 0, 0, 0, 0))


def blink_curve(frame_count):
    values = np.zeros(frame_count, dtype=np.float32)
    keys = EYE_MORPHS[0][1]
    for base in range(0, frame_count, EYE_PERIOD):
        for index in range(len(keys) - 1):
            start_frame, start_value = keys[index]
            end_frame, end_value = keys[index + 1]
            for frame in range(start_frame, end_frame + 1):
                target = base + frame
                if target >= frame_count:
                    break
                span = end_frame - start_frame
                ratio = 0.0 if span == 0 else (frame - start_frame) / span
                values[target] = start_value + (end_value - start_value) * ratio
    return values


def pad_chunk(data, filler):
    remainder = len(data) % 4
    return data if remainder == 0 else data + filler * (4 - remainder)


def write_vrma(path, weights, settings):
    frame_count = len(weights)
    stride = max(1, int(round(30 / int(settings["interval"]))))
    frames = list(range(0, frame_count, stride))
    if frames[-1] != frame_count - 1:
        frames.append(frame_count - 1)
    times = np.asarray(frames, dtype=np.float32) / float(FPS)
    tracks = [(name, weights[frames, index]) for index, name in enumerate(PRESET_EXPRESSIONS)]
    if settings["eye"]:
        curve = blink_curve(frame_count)
        tracks.append(("blink", curve[frames]))

    binary = bytearray()
    views = []
    accessors = []

    def add_accessor(values, kind):
        offset = len(binary)
        binary.extend(values.astype(np.float32).tobytes())
        views.append({"buffer": 0, "byteOffset": offset, "byteLength": len(binary) - offset})
        count = len(values) if kind == "SCALAR" else len(values) // 3
        accessor = {
            "bufferView": len(views) - 1,
            "componentType": 5126,
            "count": count,
            "type": kind,
        }
        if kind == "SCALAR":
            accessor["min"] = [float(values.min())]
            accessor["max"] = [float(values.max())]
        accessors.append(accessor)
        return len(accessors) - 1

    input_accessor = add_accessor(times, "SCALAR")
    nodes = []
    samplers = []
    channels = []
    preset = {}
    for name, values in tracks:
        vectors = np.zeros((len(values), 3), dtype=np.float32)
        vectors[:, 0] = values
        output_accessor = add_accessor(vectors.reshape(-1), "VEC3")
        nodes.append({"name": name, "translation": [0.0, 0.0, 0.0]})
        samplers.append(
            {"input": input_accessor, "output": output_accessor, "interpolation": "LINEAR"}
        )
        channels.append(
            {
                "sampler": len(samplers) - 1,
                "target": {"node": len(nodes) - 1, "path": "translation"},
            }
        )
        preset[name] = {"node": len(nodes) - 1}

    expressions = {"preset": preset}
    document = {
        "asset": {"version": "2.0", "generator": VMD_MODEL_NAME},
        "extensionsUsed": ["VRMC_vrm_animation"],
        "scene": 0,
        "scenes": [{"nodes": list(range(len(nodes)))}],
        "nodes": nodes,
        "buffers": [{"byteLength": len(binary)}],
        "bufferViews": views,
        "accessors": accessors,
        "animations": [{"name": VMD_MODEL_NAME, "samplers": samplers, "channels": channels}],
        "extensions": {
            "VRMC_vrm_animation": {"specVersion": "1.0", "expressions": expressions}
        },
    }
    json_chunk = pad_chunk(json.dumps(document, separators=(",", ":")).encode("utf-8"), b" ")
    bin_chunk = pad_chunk(bytes(binary), b"\0")
    total = 12 + 8 + len(json_chunk) + 8 + len(bin_chunk)
    with Path(path).open("wb") as output:
        output.write(struct.pack("<III", 0x46546C67, 2, total))
        output.write(struct.pack("<II", len(json_chunk), 0x4E4F534A))
        output.write(json_chunk)
        output.write(struct.pack("<II", len(bin_chunk), 0x004E4942))
        output.write(bin_chunk)


def generate(audio_path, output, model_dir, settings, progress, status):
    audio = read_audio(audio_path)
    progress(5)
    report(f"Loaded {len(audio) / RATE:.2f} seconds of audio at 16 kHz.", status)
    times, probabilities, vocabulary = infer_probabilities(
        audio, Path(model_dir), progress, status
    )
    progress(75)
    weights, threshold = make_weights(audio, times, probabilities, vocabulary, settings)
    progress(90)
    if str(output).lower().endswith(".vrma"):
        write_vrma(output, weights, settings)
    else:
        write_vmd(output, weights, settings)
    progress(100)
    result = {
        "duration": len(audio) / RATE,
        "frames": len(weights),
        "closed": int(np.count_nonzero(np.max(weights, axis=1) == 0.0)),
        "threshold": threshold,
    }
    print(f"Finished: {result}")
    return result
