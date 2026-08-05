APP_STYLE = """
QWidget#root {
    background: #1C1C1E;
    color: #FFFFFF;
    font-family: {font_family};
}

QTabWidget#tabs::pane {
    background: #2C2C2E;
    border: none;
    border-top: 1px solid #3A3A3C;
}
QTabBar {
    background: #1C1C1E;
}
QTabBar::tab {
    background: #1C1C1E;
    border: none;
    border-right: 1px solid #141416;
    color: #8E8E93;
    font-size: 12px;
    font-weight: 700;
    min-width: 89px;
    max-width: 89px;
    min-height: 38px;
    max-height: 38px;
    padding: 0;
    margin: 0;
}
QTabWidget#tabs::tab-bar {
    left: 0;
}
QTabBar::tab:selected {
    background: #2C2C2E;
    border-top: 2px solid #0A84FF;
    color: #FFFFFF;
}
QTabBar::tab:hover:!selected {
    background: #262628;
    color: #EBEBF5;
}
QWidget#corner { background: transparent; }
QFrame#dropArea {
    background: transparent;
    border: 2px dashed #48484A;
    min-height: 56px;
    max-height: 56px;
}
QFrame#dropArea[hovered="true"],
QFrame#dropArea[dragActive="true"] {
    background: #3A3A3C;
    border: 2px dashed #8E8E93;
}
QLabel#dropTitle {
    color: #FFFFFF;
    font-size: 12px;
    font-weight: 700;
}
QLabel#dropPath {
    color: #8E8E93;
    font-size: 11px;
}
QLabel#status {
    color: #8E8E93;
    font-size: 12px;
    min-height: 16px;
}
QPushButton#run,
QPushButton#browse,
QPushButton#envSecondary {
    background: #3A3A3C;
    border: 1px solid #48484A;
    border-radius: 0;
    color: #EBEBF5;
    font-size: 12px;
    min-height: 25px;
    padding: 2px 16px;
}
QPushButton#run {
    font-size: 14px;
    font-weight: 700;
    min-height: 44px;
    padding: 2px 8px;
}
QPushButton#run:hover,
QPushButton#browse:hover,
QPushButton#envSecondary:hover {
    border-color: #0A84FF;
    color: #FFFFFF;
}
QPushButton#run:pressed,
QPushButton#browse:pressed,
QPushButton#envSecondary:pressed {
    background: #2C2C2E;
    border-color: #0868CC;
    color: #EBEBF5;
}
QPushButton#run:disabled,
QPushButton#browse:disabled,
QPushButton#envSecondary:disabled {
    background: #2C2C2E;
    border-color: #3A3A3C;
    color: #636366;
}
QProgressBar {
    background: #3A3A3C; border: 0; border-radius: 0;
    min-height: 6px; max-height: 6px;
}
QProgressBar::chunk { background: #0A84FF; border-radius: 0; }
QFrame#settingsPanel {
    background: #2C2C2E;
    border: 1px solid #3A3A3C;
    border-radius: 0;
}
QLabel#settingsTitle {
    color: #FFFFFF;
    font-size: 13px;
    font-weight: 700;
}
QToolButton#reset {
    background: transparent;
    border: 0;
    color: #8E8E93;
    font-size: 16px;
    padding: 2px;
}
QToolButton#reset:hover { color: #FFFFFF; }
QLabel#rowLabel { color: #EBEBF5; font-size: 12px; }
QLabel#rowHint { color: #8E8E93; font-size: 11px; }
QLabel#rowValue {
    color: #FFFFFF;
    font-size: 12px;
    font-weight: 700;
    padding-right: 8px;
}
QLabel#mouthName { color: #EBEBF5; font-size: 12px; }
QLabel#mouthValue {
    color: #FFFFFF;
    font-size: 11px;
    font-weight: 700;
}
QLineEdit#field {
    background: #1C1C1E;
    border: 1px solid #48484A;
    border-radius: 0;
    color: #FFFFFF;
    font-size: 12px;
    min-height: 25px;
    padding: 2px 8px;
    selection-background-color: #0A84FF;
}
QLineEdit#field:hover { border-color: #5A5A5E; }
QLineEdit#field:focus { border-color: #0A84FF; }
QLineEdit#path {
    background: #3A3A3C;
    border: 1px solid #48484A;
    border-radius: 0;
    color: #FFFFFF;
    font-size: 12px;
    min-height: 25px;
    padding: 2px 8px;
    selection-background-color: #0A84FF;
}
QSlider::groove:horizontal { background: #3A3A3C; height: 3px; border-radius: 0; }
QSlider::sub-page:horizontal { background: #0A84FF; height: 3px; }
QSlider::handle:horizontal {
    background: #0A84FF;
    border: 0;
    width: 14px;
    height: 14px;
    margin: -6px 0;
    border-radius: 7px;
}
QSlider::groove:vertical { background: #3A3A3C; width: 3px; border-radius: 0; }
QSlider::add-page:vertical { background: #0A84FF; width: 3px; }
QSlider::sub-page:vertical { background: #3A3A3C; width: 3px; }
QSlider::handle:vertical {
    background: #0A84FF;
    border: 0;
    width: 14px;
    height: 14px;
    margin: 0 -6px;
    border-radius: 7px;
}
QComboBox {
    background: #3A3A3C;
    border: 1px solid #48484A;
    border-radius: 0;
    color: #FFFFFF;
    font-size: 12px;
    padding: 2px 8px;
}
QComboBox:hover { border-color: #0A84FF; }

QFrame#squarePopup {
    background: #2C2C2E;
    border: 1px solid #48484A;
    border-radius: 0;
}
QPushButton#squarePopupItem {
    background: #2C2C2E;
    border: 0;
    border-radius: 0;
    color: #FFFFFF;
    font-size: 12px;
    padding: 0 8px;
    text-align: left;
}
QPushButton#squarePopupItem[hovered="true"] {
    background: #333335;
}
QPushButton#squarePopupItem[selected="true"] {
    background: #3A3A3C;
    border-left: 3px solid #0A84FF;
    padding-left: 5px;
}
QCheckBox { color: #EBEBF5; font-size: 12px; spacing: 8px; background: transparent; }
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #48484A;
    border-radius: 0;
    background: #3A3A3C;
}
QCheckBox::indicator:unchecked { background: #3A3A3C; border: 1px solid #48484A; image: none; }
QCheckBox::indicator:checked {
    background: #0A84FF;
    border: 1px solid #0A84FF;
    image: url({check_icon});
}
QCheckBox::indicator:hover { border: 1px solid #0A84FF; }
QLabel#envHead {
    color: #8E8E93;
    font-size: 11px;
    font-weight: 700;
}
QLabel#envCell { color: #EBEBF5; font-size: 12px; }
QLabel#envState { color: #FFFFFF; font-size: 12px; font-weight: 400; }
QLabel#envState[state="missing"] { color: #FF453A; font-weight: 700; }
QLabel#envState[state="match"] { color: #FFFFFF; font-weight: 400; }
QPlainTextEdit#envLog {
    margin: 0;
    background: #1C1C1E;
    border: 1px solid #3A3A3C;
    border-radius: 0;
    color: #EBEBF5;
    font-family: "Consolas", {mono_family};
    font-size: 11px;
}
QLabel#credit { color: #8E8E93; font-size: 11px; }
"""
