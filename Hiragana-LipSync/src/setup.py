import importlib
import os
import re
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

from PySide6.QtCore import QObject, QRect, QThread, QTimer, Signal, Slot
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .lang import LANG


REQUIREMENT_PATTERN = re.compile(r"^([A-Za-z0-9._-]+)\s*==\s*(\S+)$")
CREATION_FLAGS = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
PACKAGES = (
    ("numpy", "2.2.6"),
    ("scipy", "1.16.3"),
    ("av", "16.0.1"),
    ("onnxruntime", "1.24.4"),
)
RUNTIME_NAME = "python"
PYTHON_URL = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip"
GET_PIP_URL = "https://bootstrap.pypa.io/get-pip.py"
PTH_LINES = ("python311.zip", ".", "Lib\\site-packages", "", "import site")


def runtime_python(root):
    return Path(root) / RUNTIME_NAME / "python.exe"


def normalize(name):
    return name.lower().replace("_", "-")


def installed_versions(python_path):
    if not Path(python_path).is_file():
        return {}
    completed = subprocess.run(
        [str(python_path), "-m", "pip", "freeze"],
        capture_output=True,
        text=True,
        creationflags=CREATION_FLAGS,
    )
    if completed.returncode != 0:
        return {}
    versions = {}
    for line in completed.stdout.splitlines():
        matched = REQUIREMENT_PATTERN.match(line.strip())
        if matched:
            versions[normalize(matched.group(1))] = matched.group(2)
    return versions


class EnvWorker(QObject):
    line = Signal(str)
    complete = Signal(bool)

    def __init__(self, root, packages):
        super().__init__()
        self.root = Path(root)
        self.packages = packages

    def stream(self, command):
        self.line.emit("> " + " ".join(str(item) for item in command))
        environment = dict(os.environ)
        environment["PYTHONUTF8"] = "1"
        environment["PYTHONIOENCODING"] = "utf-8"
        environment["PIP_NO_COLOR"] = "1"
        process = subprocess.Popen(
            [str(item) for item in command],
            cwd=str(self.root),
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8-sig",
            errors="replace",
            creationflags=CREATION_FLAGS,
        )
        for output in process.stdout:
            self.line.emit(output.rstrip())
        process.stdout.close()
        return process.wait() == 0

    def download(self, url, path):
        self.line.emit(f"Downloading {url}")
        with urllib.request.urlopen(url) as source, path.open("wb") as target:
            target.write(source.read())
        self.line.emit(f"Saved {path.name}")

    def bootstrap(self):
        if runtime_python(self.root).is_file():
            return True
        target = self.root / RUNTIME_NAME
        archive = self.root / "py.zip"
        script = self.root / "gp.py"
        try:
            self.download(PYTHON_URL, archive)
            self.line.emit(f"Extracting to {target}")
            with zipfile.ZipFile(archive) as source:
                source.extractall(target)
            (target / "python311._pth").write_text("\n".join(PTH_LINES) + "\n", encoding="ascii")
            self.download(GET_PIP_URL, script)
            return self.stream([runtime_python(self.root), script, "--no-warn-script-location"])
        finally:
            archive.unlink(missing_ok=True)
            script.unlink(missing_ok=True)

    def install(self):
        if not self.bootstrap():
            return False
        target = runtime_python(self.root)
        command = [target, "-m", "pip", "install", "--no-warn-script-location"]
        command += [f"{package}=={version}" for package, version in self.packages]
        return self.stream(command)

    @Slot()
    def run(self):
        try:
            result = self.install()
        except Exception as error:
            self.line.emit(str(error))
            result = False
        self.complete.emit(result)


class Spinner(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedHeight(6)
        self.offset = 0
        self.running = False
        self.timer = QTimer(self)
        self.timer.setInterval(30)
        self.timer.timeout.connect(self.advance)

    def start(self):
        self.running = True
        self.offset = 0
        self.timer.start()
        self.update()

    def stop(self):
        self.running = False
        self.timer.stop()
        self.update()

    def advance(self):
        span = max(1, self.width() + self.width() // 3)
        self.offset = (self.offset + 6) % span
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#3A3A3C"))
        if self.running:
            width = max(24, self.width() // 3)
            painter.fillRect(
                QRect(self.offset - width, 0, width, self.height()), QColor("#0A84FF")
            )
        painter.end()


class EnvSection(QFrame):
    requested = Signal()

    def __init__(self, root_dir, packages):
        super().__init__()
        self.setObjectName("settingsPanel")
        self.root_dir = Path(root_dir)
        self.packages = packages
        self.language_code = "ja"
        self.rows = []

        panel = QVBoxLayout(self)
        panel.setContentsMargins(5, 5, 5, 5)
        panel.setSpacing(5)

        self.table = QGridLayout()
        self.table.setHorizontalSpacing(5)
        self.table.setVerticalSpacing(5)
        for column, stretch in enumerate((2, 1, 1)):
            self.table.setColumnStretch(column, stretch)
        self.heads = []
        for column in range(3):
            label = QLabel()
            label.setObjectName("envHead")
            self.table.addWidget(label, 0, column)
            self.heads.append(label)
        panel.addLayout(self.table)

        buttons = QHBoxLayout()
        buttons.setSpacing(3)
        self.install_button = QPushButton()
        self.install_button.setObjectName("envSecondary")
        self.install_button.clicked.connect(self.requested.emit)
        buttons.addWidget(self.install_button)
        buttons.addStretch()
        panel.addLayout(buttons)
        self.build_rows()

    def text(self, key):
        return LANG[self.language_code][key]

    def build_rows(self):
        for widgets in self.rows:
            for widget in widgets:
                self.table.removeWidget(widget)
                widget.deleteLater()
        self.rows = []
        for index, (package, version) in enumerate(self.packages, start=1):
            name = QLabel(package)
            name.setObjectName("envCell")
            required = QLabel(version)
            required.setObjectName("envCell")
            state = QLabel("")
            state.setObjectName("envState")
            self.table.addWidget(name, index, 0)
            self.table.addWidget(required, index, 1)
            self.table.addWidget(state, index, 2)
            self.rows.append((name, required, state))

    def refresh(self, busy):
        versions = installed_versions(runtime_python(self.root_dir))
        ready = all(
            versions.get(normalize(package)) == version for package, version in self.packages
        )
        for name, required, state in self.rows:
            found = versions.get(normalize(name.text()))
            installed = found == required.text()
            key, flag = ("state_installed", "match") if installed else ("state_missing", "missing")
            state.setText(self.text(key))
            state.setProperty("state", flag)
            state.style().unpolish(state)
            state.style().polish(state)
        self.install_button.setEnabled(not busy and not ready)

    def apply_language(self, code):
        self.language_code = code
        for index, key in enumerate(("col_package", "col_version", "col_state")):
            self.heads[index].setText(self.text(key))
        self.install_button.setText(self.text("install"))


class SetupPanel(QWidget):
    def __init__(self, root_dir, language_code):
        super().__init__()
        self.root_dir = Path(root_dir)
        self.language_code = language_code
        self.busy = False
        self.thread = None
        self.worker = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(3)

        self.section = EnvSection(self.root_dir, PACKAGES)
        self.section.requested.connect(self.start)
        layout.addWidget(self.section)

        self.spinner = Spinner()
        layout.addWidget(self.spinner)

        self.log = QPlainTextEdit()
        self.log.setObjectName("envLog")
        self.log.setReadOnly(True)
        self.log.setMinimumHeight(220)
        layout.addWidget(self.log)
        self.apply_language(language_code)

    def text(self, key):
        return LANG[self.language_code][key]

    def refresh(self):
        self.section.refresh(self.busy)

    def start(self):
        if self.busy:
            return
        self.log.clear()
        self.busy = True
        self.spinner.start()
        self.append("Setting up the runtime.")
        self.refresh()
        self.thread = QThread(self)
        self.worker = EnvWorker(self.root_dir, PACKAGES)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.line.connect(self.append)
        self.worker.complete.connect(self.finish)
        self.worker.complete.connect(self.thread.quit)
        self.thread.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self.release)
        self.thread.start()

    def release(self):
        self.thread = None
        self.worker = None

    def append(self, message):
        self.log.appendPlainText(message)

    def finish(self, success):
        self.busy = False
        self.spinner.stop()
        if success:
            importlib.invalidate_caches()
        self.append("Finished." if success else "Failed.")
        self.refresh()

    def apply_language(self, code):
        self.language_code = code
        self.section.apply_language(code)
        self.refresh()
