from pathlib import Path


MORPHS = ("\u3042", "\u3044", "\u3046", "\u3048", "\u304a", "\u3093")
PRESET_EXPRESSIONS = ("aa", "ih", "ou", "ee", "oh")
SUPPORTED_AUDIO = {".wav", ".mp3"}
DEFAULTS = {"scales": [1.0, 1.0, 1.0, 1.0, 1.0, 0.5], "lead": 5, "shapes": 2, "interval": 30, "eye": False}
DEFAULT_DIRECTORY = Path.home() / "Downloads"


def output_path(directory, name, fallback, suffix=".vmd"):
    value = name.strip()
    if not value or Path(value).name != value or value in {".", ".."}:
        value = fallback
    if Path(value).suffix.lower() != suffix:
        value += suffix
    base = Path(directory) if str(directory).strip() else DEFAULT_DIRECTORY
    return base / value
