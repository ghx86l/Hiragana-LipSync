import os
import sys
from pathlib import Path


def runtime_python(root):
    candidates = (root / "env" / "Scripts" / "python.exe", root / "env" / "bin" / "python")
    return next((candidate for candidate in candidates if candidate.is_file()), None)


def main():
    script = Path(__file__).resolve()
    runtime = runtime_python(script.parent)
    if runtime and Path(sys.executable).resolve() != runtime.resolve():
        os.execv(str(runtime), [str(runtime), str(script), *sys.argv[1:]])
    from src.window import main as launch

    launch()


if __name__ == "__main__":
    main()