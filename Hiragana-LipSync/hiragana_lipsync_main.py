import os
import sys
from pathlib import Path


def runtime_python(root):
    candidate = root / "python" / "python.exe"
    return candidate if candidate.is_file() else None


def main():
    script = Path(__file__).resolve()
    compiled = "__compiled__" in globals() or getattr(sys, "frozen", False)
    if not compiled:
        runtime = runtime_python(script.parent)
        if runtime and Path(sys.executable).resolve() != runtime.resolve():
            os.execv(str(runtime), [str(runtime), str(script), *sys.argv[1:]])
    root = str(Path(sys.argv[0]).resolve().parent if compiled else script.parent)
    if root not in sys.path:
        sys.path.insert(0, root)
    python_root = Path(root) / "python"
    runtime_paths = (
        python_root / "python311.zip",
        python_root,
        python_root / "Lib" / "site-packages",
    )
    for path in runtime_paths:
        if path.exists() and str(path) not in sys.path:
            sys.path.insert(0, str(path))
    from src.window import main as launch

    launch()


if __name__ == "__main__":
    main()
