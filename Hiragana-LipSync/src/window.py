import json
import sys
from pathlib import Path

from PySide6.QtCore import QEvent, QPoint, QSize, QThread, Qt
from PySide6.QtGui import QColor, QIcon, QPainter
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QProgressBar,
    QSizePolicy,
    QSlider,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .const import DEFAULT_DIRECTORY, DEFAULTS, MORPHS, SUPPORTED_AUDIO, output_path
from .design import APP_STYLE
from .lang import LANG
from .setup import SetupPanel
from .worker import Worker


def tinted_icon(path, color, size):
    pixmap = QIcon(str(path)).pixmap(size)
    painter = QPainter(pixmap)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    painter.fillRect(pixmap.rect(), QColor(color))
    painter.end()
    return QIcon(pixmap)


def file_size(path):
    size = float(Path(path).stat().st_size)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024.0 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024.0


CREDIT_HTML = (
    'Model: <a href="https://huggingface.co/TylorShine/wavlm-base-plus-hiragana-ctc-v2" '
    'style="color:#8E8E93; text-decoration:underline">wavlm-base-plus-hiragana-ctc-v2</a> (CC BY-SA 3.0)<br>'
    'Eye animation reference: <a href="https://booth.pm/ja/items/6123352" '
    'style="color:#8E8E93; text-decoration:underline">「何もしない」まばたき＆呼吸モーション</a> かんな@MMD'
)


def config_path(root):
    return Path(root) / "config" / "config.json"


def load_config(root):
    try:
        data = json.loads(config_path(root).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    code = data.get("language")
    directory = data.get("directory")
    name = data.get("name")
    return {
        "language": code if code in LANG else "ja",
        "directory": directory if isinstance(directory, str) and directory.strip() else str(DEFAULT_DIRECTORY),
        "name": name if isinstance(name, str) else "",
    }


def save_config(root, data):
    try:
        path = config_path(root)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except OSError:
        pass


class SquarePopupComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._popup = None

    def showPopup(self):
        if self._popup is not None:
            self.hidePopup()
            return
        host = self.window()
        popup = QFrame(host)
        popup.setObjectName("squarePopup")
        popup_layout = QVBoxLayout(popup)
        popup_layout.setContentsMargins(0, 0, 0, 0)
        popup_layout.setSpacing(0)
        row_height = self.height()
        for index in range(self.count()):
            item = QPushButton(self.itemText(index), popup)
            item.setObjectName("squarePopupItem")
            item.setProperty("selected", index == self.currentIndex())
            item.setProperty("hovered", False)
            item.setFixedHeight(row_height)
            item.clicked.connect(
                lambda checked=False, item_index=index: self._select_item(item_index)
            )
            popup_layout.addWidget(item)
        position = self.mapTo(host, QPoint(0, self.height()))
        popup.setGeometry(
            position.x(),
            position.y(),
            self.width(),
            row_height * self.count() + 2,
        )
        self._popup = popup
        QApplication.instance().installEventFilter(self)
        popup.show()
        popup.raise_()

    def hidePopup(self):
        if self._popup is None:
            return
        QApplication.instance().removeEventFilter(self)
        popup = self._popup
        self._popup = None
        popup.hide()
        popup.deleteLater()

    def _select_item(self, index):
        self.setCurrentIndex(index)
        self.hidePopup()

    def eventFilter(self, watched, event):
        if self._popup is None:
            return super().eventFilter(watched, event)
        if (
            isinstance(watched, QPushButton)
            and watched.parent() is self._popup
            and event.type() in (QEvent.Type.Enter, QEvent.Type.Leave)
        ):
            watched.setProperty("hovered", event.type() == QEvent.Type.Enter)
            watched.style().unpolish(watched)
            watched.style().polish(watched)
            watched.update()
        elif event.type() == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_Escape:
            self.hidePopup()
        elif event.type() == QEvent.Type.MouseButtonPress:
            point = event.globalPosition().toPoint()
            popup_rect = self._popup.rect().translated(
                self._popup.mapToGlobal(QPoint())
            )
            combo_rect = self.rect().translated(self.mapToGlobal(QPoint()))
            if not popup_rect.contains(point) and not combo_rect.contains(point):
                self.hidePopup()
        return super().eventFilter(watched, event)


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hiragana LipSync")
        self.setFixedSize(550, 650)
        self.setAcceptDrops(True)
        self.audio_path = None
        self.thread = None
        self.worker = None
        self.status_key = "idle"
        self.status_text = ""
        if "__compiled__" in globals():
            self.root_dir = Path(sys.argv[0]).resolve().parent
        else:
            self.root_dir = Path(__file__).resolve().parent.parent
        self.model_dir = self.root_dir / "model"
        self.config = load_config(self.root_dir)
        self.language_code = self.config["language"]

        icon_path = self.root_dir / "icon" / "hiragana_lipsync.ico"
        if icon_path.is_file():
            self.setWindowIcon(QIcon(str(icon_path)))

        self.root = QWidget()
        self.root.setObjectName("root")
        self.root.setAcceptDrops(True)
        self.setCentralWidget(self.root)
        shell = QVBoxLayout(self.root)
        shell.setContentsMargins(5, 5, 5, 5)
        shell.setSpacing(3)
        self.tabs = QTabWidget()
        self.tabs.setObjectName("tabs")
        self.convert_page = QWidget()
        self.output_page = QWidget()
        self.setup_page = SetupPanel(self.root_dir, self.language_code)
        self.tabs.addTab(self.convert_page, "")
        self.tabs.addTab(self.output_page, "")
        self.tabs.addTab(self.setup_page, "")
        layout = QVBoxLayout(self.convert_page)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(3)

        corner = QWidget()
        corner.setObjectName("corner")
        language_row = QHBoxLayout(corner)
        language_row.setContentsMargins(5, 5, 5, 5)
        corner.setFixedHeight(40)
        language_row.setSpacing(3)
        self.language_combo = SquarePopupComboBox()
        self.language_combo.setFixedSize(120, 30)
        for code, values in LANG.items():
            self.language_combo.addItem(values["name"], code)
        self.language_combo.setCurrentIndex(
            self.language_combo.findData(self.language_code)
        )
        self.language_combo.currentIndexChanged.connect(self.change_language)
        language_row.addWidget(self.language_combo)
        self.tabs.setCornerWidget(corner, Qt.Corner.TopRightCorner)
        shell.addWidget(self.tabs)

        self.drop_area = QFrame()
        self.drop_area.setObjectName("dropArea")
        self.drop_area.setProperty("dragActive", False)
        self.drop_area.setProperty("hovered", False)
        self.drop_area.setCursor(Qt.CursorShape.PointingHandCursor)
        drop_layout = QVBoxLayout(self.drop_area)
        drop_layout.setContentsMargins(5, 0, 5, 0)
        drop_layout.setSpacing(0)
        self.drop_title = QLabel()
        self.drop_title.setObjectName("dropTitle")
        self.drop_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drop_path = QLabel("")
        self.drop_path.setObjectName("dropPath")
        self.drop_path.setVisible(False)
        self.drop_path.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drop_path.setWordWrap(True)
        self.drop_title.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.drop_path.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        drop_layout.addStretch()
        drop_layout.addWidget(self.drop_title, 0, Qt.AlignmentFlag.AlignHCenter)
        drop_layout.addWidget(self.drop_path, 0, Qt.AlignmentFlag.AlignHCenter)
        drop_layout.addStretch()
        layout.addWidget(self.drop_area)

        self.status = QLabel("")
        self.status.setObjectName("status")
        layout.addWidget(self.status)

        self.run_button = QPushButton("Audio to .vmd")
        self.run_button.setObjectName("run")
        self.run_button.setEnabled(False)
        self.run_button.clicked.connect(lambda: self.start(".vmd"))
        layout.addWidget(self.run_button)

        self.run_vrma_button = QPushButton("Audio to .vrma")
        self.run_vrma_button.setObjectName("run")
        self.run_vrma_button.setEnabled(False)
        self.run_vrma_button.clicked.connect(lambda: self.start(".vrma"))
        layout.addWidget(self.run_vrma_button)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setTextVisible(False)
        layout.addWidget(self.progress)

        self.settings_panel = QFrame()
        self.settings_panel.setObjectName("settingsPanel")
        panel = QVBoxLayout(self.settings_panel)
        panel.setContentsMargins(5, 5, 5, 5)
        panel.setSpacing(10)

        head = QHBoxLayout()
        self.settings_title = QLabel()
        self.settings_title.setObjectName("settingsTitle")
        head.addWidget(self.settings_title)
        head.addStretch()
        self.reset_button = QToolButton()
        self.reset_button.setObjectName("reset")
        self.reset_button.setCursor(Qt.CursorShape.PointingHandCursor)
        reset_icon = self.root_dir / "img" / "reset_settings.svg"
        self.reset_icons = None
        if reset_icon.is_file():
            icon_size = QSize(18, 18)
            self.reset_icons = (
                tinted_icon(reset_icon, "#B3B3B3", icon_size),
                tinted_icon(reset_icon, "#FFFFFF", icon_size),
            )
            self.reset_button.setIcon(self.reset_icons[0])
            self.reset_button.setIconSize(icon_size)
        else:
            self.reset_button.setText("\u21ba")
        self.reset_button.clicked.connect(self.apply_defaults)
        head.addWidget(self.reset_button)
        panel.addLayout(head)

        self.mouth_label = QLabel()
        self.mouth_label.setObjectName("rowLabel")
        panel.addWidget(self.mouth_label)
        mouth_row = QHBoxLayout()
        mouth_row.setSpacing(3)
        self.mouth_sliders = []
        for _ in MORPHS:
            item = QVBoxLayout()
            item.setSpacing(8)
            name = QLabel()
            name.setObjectName("mouthName")
            name.setAlignment(Qt.AlignmentFlag.AlignCenter)
            slider = QSlider(Qt.Orientation.Vertical)
            slider.setRange(0, 10)
            slider.setFixedHeight(96)
            value = QLabel()
            value.setObjectName("mouthValue")
            value.setAlignment(Qt.AlignmentFlag.AlignCenter)
            slider.valueChanged.connect(
                lambda v, label=value: label.setText(f"{v / 10:.1f}")
            )
            item.addWidget(name)
            item.addWidget(slider, alignment=Qt.AlignmentFlag.AlignHCenter)
            item.addWidget(value)
            mouth_row.addLayout(item)
            self.mouth_sliders.append((name, slider, value))
        panel.addLayout(mouth_row)

        self.lead_label, self.lead_slider, self.lead_value = self.build_slider_row(panel, -30, 30)
        self.shapes_label, self.shapes_slider, self.shapes_value = self.build_slider_row(panel, 1, 6)

        interval_row = QHBoxLayout()
        interval_row.setSpacing(3)
        self.interval_label = QLabel()
        self.interval_label.setObjectName("rowLabel")
        self.interval_label.setMinimumWidth(185)
        self.interval_combo = SquarePopupComboBox()
        self.interval_combo.addItems(["10", "15", "30"])
        interval_row.addWidget(self.interval_label)
        interval_row.addWidget(self.interval_combo)
        interval_row.addStretch()
        panel.addLayout(interval_row)

        eye_row = QHBoxLayout()
        eye_row.setSpacing(3)
        self.eye_label = QLabel()
        self.eye_label.setObjectName("rowLabel")
        self.eye_label.setMinimumWidth(185)
        self.eye_check = QCheckBox()
        eye_row.addWidget(self.eye_label)
        eye_row.addWidget(self.eye_check)
        eye_row.addStretch()
        panel.addLayout(eye_row)

        layout.addWidget(self.settings_panel)
        layout.addStretch()

        self.credit = QLabel(CREDIT_HTML)
        self.credit.setObjectName("credit")
        self.credit.setTextFormat(Qt.TextFormat.RichText)
        self.credit.setOpenExternalLinks(True)
        self.credit.setWordWrap(True)
        layout.addWidget(self.credit)

        self.build_output_page()
        self.apply_style()
        self.drop_widgets = (self.drop_area, self.drop_title, self.drop_path)
        self.install_drop_filter()
        self.apply_defaults()
        self.apply_language()

    def build_slider_row(self, panel, minimum, maximum):
        row = QHBoxLayout()
        row.setSpacing(3)
        label = QLabel()
        label.setObjectName("rowLabel")
        label.setMinimumWidth(185)
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(minimum, maximum)
        value = QLabel()
        value.setObjectName("rowValue")
        value.setMinimumWidth(30)
        value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        slider.valueChanged.connect(lambda current: value.setText(str(current)))
        row.addWidget(label)
        row.addWidget(slider, 1)
        row.addWidget(value)
        panel.addLayout(row)
        return label, slider, value

    def build_output_page(self):
        layout = QVBoxLayout(self.output_page)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(3)

        self.output_panel = QFrame()
        self.output_panel.setObjectName("settingsPanel")
        panel = QVBoxLayout(self.output_panel)
        panel.setContentsMargins(5, 5, 5, 5)
        panel.setSpacing(10)

        self.output_title = QLabel()
        self.output_title.setObjectName("settingsTitle")
        panel.addWidget(self.output_title)

        self.directory_label = QLabel()
        self.directory_label.setObjectName("rowLabel")
        panel.addWidget(self.directory_label)
        directory_row = QHBoxLayout()
        directory_row.setSpacing(3)
        self.directory_edit = QLineEdit(self.config["directory"])
        self.directory_edit.setObjectName("path")
        self.directory_edit.setReadOnly(True)
        self.browse_button = QPushButton()
        self.browse_button.setObjectName("browse")
        self.browse_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.browse_button.clicked.connect(self.pick_directory)
        directory_row.addWidget(self.directory_edit, 1)
        directory_row.addWidget(self.browse_button)
        panel.addLayout(directory_row)

        self.name_label = QLabel()
        self.name_label.setObjectName("rowLabel")
        panel.addWidget(self.name_label)
        self.name_edit = QLineEdit(self.config["name"])
        self.name_edit.setObjectName("field")
        self.name_edit.editingFinished.connect(self.store_config)
        panel.addWidget(self.name_edit)
        self.name_hint = QLabel()
        self.name_hint.setObjectName("rowHint")
        panel.addWidget(self.name_hint)

        layout.addWidget(self.output_panel)
        layout.addStretch()

    def store_config(self):
        self.config = {
            "language": self.language_code,
            "directory": self.directory_edit.text().strip(),
            "name": self.name_edit.text().strip(),
        }
        save_config(self.root_dir, self.config)

    def pick_directory(self):
        selected = QFileDialog.getExistingDirectory(self, "", self.directory_edit.text())
        if selected:
            self.directory_edit.setText(str(Path(selected)))
            self.store_config()

    def install_drop_filter(self):
        for widget in self.findChildren(QWidget):
            if isinstance(widget, QLineEdit):
                continue
            widget.setAcceptDrops(True)
            widget.installEventFilter(self)

    def apply_style(self):
        check_icon = self.root_dir / "img" / "check.svg"
        families = LANG[self.language_code]["font"]
        style = APP_STYLE.replace("{check_icon}", check_icon.as_posix())
        style = style.replace("{font_family}", ", ".join(f'"{name}"' for name in families))
        style = style.replace("{mono_family}", f'"{families[0]}"')
        self.setStyleSheet(style)

    def text(self, key):
        return LANG[self.language_code][key]

    def change_language(self, index):
        code = self.language_combo.itemData(index)
        if not code:
            return
        self.language_code = code
        self.store_config()
        self.apply_language()

    def apply_language(self):
        self.apply_style()
        self.drop_title.setText(self.audio_path.name if self.audio_path else self.text("drop_audio"))
        self.settings_title.setText(self.text("advanced"))
        self.mouth_label.setText(self.text("mouth"))
        self.lead_label.setText(self.text("lead"))
        self.shapes_label.setText(self.text("shapes"))
        self.interval_label.setText(self.text("interval"))
        self.eye_label.setText(self.text("eye"))
        self.output_title.setText(self.text("output"))
        self.directory_label.setText(self.text("output_dir"))
        self.name_label.setText(self.text("output_name"))
        self.name_hint.setText(self.text("output_hint"))
        self.browse_button.setText(self.text("browse"))
        names = self.text("vowel_names")
        for index, (name, _, _) in enumerate(self.mouth_sliders):
            name.setText(names[index])
        self.tabs.setTabText(0, self.text("tab_convert"))
        self.tabs.setTabText(1, self.text("tab_output"))
        self.tabs.setTabText(2, self.text("tab_setup"))
        self.setup_page.apply_language(self.language_code)
        if self.status_key:
            self.status.setText(self.text(self.status_key))
        else:
            self.status.setText(self.status_text or self.text("idle"))

    def apply_defaults(self):
        for index, (_, slider, value) in enumerate(self.mouth_sliders):
            scaled = int(round(DEFAULTS["scales"][index] * 10))
            slider.setValue(scaled)
            value.setText(f"{scaled / 10:.1f}")
        self.lead_slider.setValue(DEFAULTS["lead"])
        self.lead_value.setText(str(DEFAULTS["lead"]))
        self.shapes_slider.setValue(DEFAULTS["shapes"])
        self.shapes_value.setText(str(DEFAULTS["shapes"]))
        self.interval_combo.setCurrentText(str(DEFAULTS["interval"]))
        self.eye_check.setChecked(DEFAULTS["eye"])

    def read_settings(self):
        return {
            "scales": [slider.value() / 10 for _, slider, _ in self.mouth_sliders],
            "lead": self.lead_slider.value(),
            "shapes": self.shapes_slider.value(),
            "interval": int(self.interval_combo.currentText()),
            "eye": self.eye_check.isChecked(),
        }

    def set_status(self, key):
        self.status_key = key or "idle"
        self.status_text = ""
        self.status.setText(self.text(self.status_key))

    def set_status_text(self, message):
        self.status_key = "" if message else "idle"
        self.status_text = message
        self.status.setText(message if message else self.text("idle"))

    def eventFilter(self, watched, event):
        if event.type() in (QEvent.Type.DragEnter, QEvent.Type.DragMove):
            if self.accept_audio(event):
                return True
        elif event.type() == QEvent.Type.DragLeave:
            self.set_drop_active(False)
        elif event.type() == QEvent.Type.Drop:
            if self.drop_audio(event):
                return True
        elif event.type() in (QEvent.Type.Enter, QEvent.Type.Leave) and watched in self.drop_widgets:
            self.set_drop_hover(self.drop_area.underMouse())
        elif (
            event.type() in (QEvent.Type.Enter, QEvent.Type.Leave)
            and self.reset_icons is not None
            and watched is self.reset_button
        ):
            self.reset_button.setIcon(self.reset_icons[event.type() == QEvent.Type.Enter])
        elif event.type() == QEvent.Type.MouseButtonRelease and watched in self.drop_widgets:
            self.pick_audio()
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

    def pick_audio(self):
        selected, _ = QFileDialog.getOpenFileName(self, "", "", "Audio (*.wav *.mp3)")
        if selected:
            self.set_audio(Path(selected))

    def set_drop_active(self, active):
        self.drop_area.setProperty("dragActive", active)
        self.drop_area.style().unpolish(self.drop_area)
        self.drop_area.style().polish(self.drop_area)

    def set_drop_hover(self, hovered):
        if self.drop_area.property("hovered") == hovered:
            return
        self.drop_area.setProperty("hovered", hovered)
        self.drop_area.style().unpolish(self.drop_area)
        self.drop_area.style().polish(self.drop_area)

    def set_audio(self, path):
        self.audio_path = path
        self.drop_title.setText(path.name)
        self.drop_path.setText(file_size(path))
        self.drop_path.setVisible(True)
        self.run_button.setEnabled(True)
        self.run_vrma_button.setEnabled(True)
        print(f"Selected audio: {path}")

    def start(self, suffix=".vmd"):
        if not self.audio_path or not self.audio_path.is_file():
            self.set_status("audio_required")
            return
        if not (self.model_dir / "phoneme.onnx").is_file():
            self.set_status("model_missing")
            return
        output = output_path(
            self.directory_edit.text(),
            self.name_edit.text(),
            f"{self.audio_path.stem}_lipsync",
            suffix,
        )
        try:
            output.parent.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            self.set_status_text(str(error))
            return
        self.progress.setValue(0)
        self.run_button.setEnabled(False)
        self.run_vrma_button.setEnabled(False)
        self.set_status("converting")
        self.thread = QThread(self)
        self.worker = Worker(
            str(self.audio_path),
            str(output),
            str(self.model_dir),
            self.read_settings(),
        )
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.update_progress)
        self.worker.status.connect(self.set_status_text)
        self.worker.complete.connect(self.finish)
        self.worker.failed.connect(self.fail)
        self.worker.complete.connect(self.thread.quit)
        self.worker.failed.connect(self.thread.quit)
        self.thread.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def update_progress(self, value):
        self.progress.setValue(value)
        if value >= 90:
            self.set_status("writing")

    def finish(self, result):
        print(f"VMD written: {result}")
        self.progress.setValue(100)
        self.set_status("done")
        self.run_button.setEnabled(True)
        self.run_vrma_button.setEnabled(True)

    def fail(self, detail):
        print(detail)
        lines = [line for line in detail.strip().splitlines() if line.strip()]
        self.set_status_text(lines[-1] if lines else "")
        self.progress.setValue(0)
        self.run_button.setEnabled(True)
        self.run_vrma_button.setEnabled(True)


def main():
    application = QApplication(sys.argv)
    window = Window()
    window.show()
    raise SystemExit(application.exec())
