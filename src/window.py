import sys
from pathlib import Path

from PySide6.QtCore import QEvent, QThread, Qt
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QProgressBar,
    QStackedLayout,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .core import SUPPORTED_AUDIO, output_path
from .design import APP_STYLE
from .lang import LANG
from .worker import Worker


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hiragana LipSync")
        self.setMinimumSize(600, 400)
        self.setAcceptDrops(True)
        self.audio_path = None
        self.thread = None
        self.worker = None
        self.language_code = "ja"
        self.root_dir = Path(__file__).resolve().parent.parent
        self.model_dir = self.root_dir / "model"

        self.root = QWidget()
        self.root.setObjectName("root")
        self.root.setAcceptDrops(True)
        self.setCentralWidget(self.root)
        stack = QStackedLayout(self.root)
        stack.setStackingMode(QStackedLayout.StackingMode.StackAll)

        self.drop_overlay = QFrame()
        self.drop_overlay.setObjectName("dropOverlay")
        self.drop_overlay.setProperty("dragActive", False)
        self.drop_overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        stack.addWidget(self.drop_overlay)

        content = QWidget()
        content.setObjectName("content")
        stack.addWidget(content)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(30, 24, 30, 24)
        layout.setSpacing(12)

        language_row = QHBoxLayout()
        language_row.setSpacing(0)
        self.language_group = QButtonGroup(self)
        self.language_group.setExclusive(True)
        self.language_buttons = {}
        for code, values in LANG.items():
            button = QPushButton(values["name"])
            button.setObjectName("languageButton")
            button.setCheckable(True)
            button.setChecked(code == self.language_code)
            button.clicked.connect(lambda checked, value=code: self.change_language(value))
            self.language_group.addButton(button)
            self.language_buttons[code] = button
            language_row.addWidget(button)
        language_row.addStretch()
        layout.addLayout(language_row)

        self.drop_area = QFrame()
        self.drop_area.setObjectName("dropArea")
        drop_layout = QVBoxLayout(self.drop_area)
        drop_layout.setContentsMargins(24, 26, 24, 26)
        drop_layout.setSpacing(8)
        self.drop_title = QLabel()
        self.drop_title.setObjectName("dropTitle")
        self.drop_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drop_path = QLabel("")
        self.drop_path.setObjectName("dropPath")
        self.drop_path.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drop_path.setWordWrap(True)
        drop_layout.addWidget(self.drop_title)
        drop_layout.addWidget(self.drop_path)
        layout.addWidget(self.drop_area)

        self.options_button = QToolButton()
        self.options_button.setObjectName("options")
        self.options_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.options_button.setArrowType(Qt.ArrowType.RightArrow)
        self.options_button.setCheckable(True)
        self.options_button.toggled.connect(self.toggle_options)
        layout.addWidget(self.options_button)

        self.option_panel = QFrame()
        self.option_panel.setObjectName("optionPanel")
        self.option_panel.setVisible(False)
        options = QVBoxLayout(self.option_panel)
        options.setContentsMargins(14, 14, 14, 14)
        self.use_gpu = QCheckBox()
        self.use_gpu.setChecked(True)
        options.addWidget(self.use_gpu)
        layout.addWidget(self.option_panel)

        layout.addStretch()
        self.run_button = QPushButton()
        self.run_button.setObjectName("run")
        self.run_button.setEnabled(False)
        self.run_button.clicked.connect(self.start)
        layout.addWidget(self.run_button)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setTextVisible(False)
        layout.addWidget(self.progress)
        self.setStyleSheet(APP_STYLE)
        self.install_drop_filter()
        self.apply_language()
        self.resize(600, 400)

    def install_drop_filter(self):
        for widget in self.findChildren(QWidget):
            widget.setAcceptDrops(True)
            widget.installEventFilter(self)

    def text(self, key):
        return LANG[self.language_code][key]

    def change_language(self, code):
        self.language_code = code
        self.language_buttons[code].setChecked(True)
        self.apply_language()

    def apply_language(self):
        self.options_button.setText(self.text("settings"))
        self.use_gpu.setText(self.text("use_gpu"))
        self.run_button.setText(self.text("generate"))
        self.drop_title.setText(self.audio_path.name if self.audio_path else self.text("drop_audio"))

    def toggle_options(self, visible):
        self.option_panel.setVisible(visible)
        self.options_button.setArrowType(
            Qt.ArrowType.DownArrow if visible else Qt.ArrowType.RightArrow
        )

    def eventFilter(self, watched, event):
        if event.type() in (QEvent.Type.DragEnter, QEvent.Type.DragMove):
            if self.accept_audio(event):
                return True
        elif event.type() == QEvent.Type.DragLeave:
            self.set_drop_active(False)
        elif event.type() == QEvent.Type.Drop:
            if self.drop_audio(event):
                return True
        return super().eventFilter(watched, event)

    def dragEnterEvent(self, event):
        self.accept_audio(event)

    def dragMoveEvent(self, event):
        self.accept_audio(event)

    def dragLeaveEvent(self, event):
        self.set_drop_active(False)
        event.accept()

    def dropEvent(self, event):
        self.drop_audio(event)

    def accept_audio(self, event):
        urls = event.mimeData().urls()
        if len(urls) == 1 and urls[0].isLocalFile():
            path = Path(urls[0].toLocalFile())
            if path.suffix.lower() in SUPPORTED_AUDIO:
                event.acceptProposedAction()
                self.set_drop_active(True)
                return True
        event.ignore()
        return False

    def drop_audio(self, event):
        if not self.accept_audio(event):
            return False
        self.set_drop_active(False)
        self.set_audio(Path(event.mimeData().urls()[0].toLocalFile()))
        event.acceptProposedAction()
        return True

    def set_drop_active(self, active):
        self.drop_overlay.setProperty("dragActive", active)
        self.drop_overlay.style().unpolish(self.drop_overlay)
        self.drop_overlay.style().polish(self.drop_overlay)

    def set_audio(self, path):
        self.audio_path = path
        self.drop_title.setText(path.name)
        self.drop_path.setText(str(path))
        self.run_button.setEnabled(True)
        print(f"Selected audio: {path}")

    def start(self):
        if not self.audio_path or not self.audio_path.is_file():
            print(self.text("audio_required"))
            return
        if not (self.model_dir / "model.safetensors").is_file():
            print(self.text("model_missing"))
            return
        output = output_path(f"{self.audio_path.stem}_lipsync")
        self.progress.setValue(0)
        self.run_button.setEnabled(False)
        self.thread = QThread(self)
        self.worker = Worker(
            str(self.audio_path),
            str(output),
            str(self.model_dir),
            self.use_gpu.isChecked(),
        )
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.progress.setValue)
        self.worker.complete.connect(self.finish)
        self.worker.failed.connect(self.fail)
        self.worker.complete.connect(self.thread.quit)
        self.worker.failed.connect(self.thread.quit)
        self.thread.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def finish(self, result):
        print(f"VMD written: {result}")
        self.progress.setValue(0)
        self.run_button.setEnabled(True)

    def fail(self, detail):
        print(detail)
        self.progress.setValue(0)
        self.run_button.setEnabled(True)


def main():
    application = QApplication(sys.argv)
    window = Window()
    window.show()
    raise SystemExit(application.exec())