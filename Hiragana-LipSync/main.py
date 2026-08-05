import sys
from pathlib import Path


def main():
    script = Path(__file__).resolve()
    compiled = "__compiled__" in globals()
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
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    from src.window import main as launch

    launch()


if __name__ == "__main__":
    main()
