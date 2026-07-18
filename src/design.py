APP_STYLE = """
QWidget#root {
    background: #F6F8FB;
    color: #111827;
    font-family: "Segoe UI", "Yu Gothic UI", sans-serif;
}
QWidget#content { background: transparent; }
QFrame#dropOverlay {
    background: rgba(15, 118, 110, 18);
    border: 1px solid rgba(15, 118, 110, 70);
}
QFrame#dropOverlay[dragActive="true"] {
    background: rgba(15, 118, 110, 42);
    border: 2px solid #0F766E;
}
QFrame#dropArea {
    background: transparent;
    border: 0;
    min-height: 150px;
}
QLabel#dropTitle {
    color: #101828;
    font-size: 16px;
    font-weight: 700;
}
QLabel#dropPath {
    color: #344054;
    font-size: 12px;
}
QPushButton#languageButton {
    background: #FFFFFF;
    border: 1px solid #B8C4D0;
    border-radius: 0;
    color: #344054;
    font-size: 12px;
    font-weight: 700;
    min-height: 30px;
    padding: 0 12px;
}
QPushButton#languageButton:hover { background: #E8F1F0; }
QPushButton#languageButton:checked {
    background: #0F766E;
    border-color: #0F766E;
    color: #FFFFFF;
}
QToolButton#options {
    background: #FFFFFF;
    border: 1px solid #B8C4D0;
    border-radius: 0;
    color: #1F2937;
    font-size: 13px;
    font-weight: 700;
    min-height: 30px;
    padding: 0 10px;
    text-align: left;
}
QToolButton#options:hover { background: #E8F1F0; border-color: #7C919F; }
QFrame#optionPanel {
    background: #FFFFFF;
    border: 1px solid #B8C4D0;
    border-radius: 0;
}
QCheckBox { color: #1F2937; font-size: 13px; font-weight: 600; spacing: 8px; }
QCheckBox::indicator {
    width: 16px; height: 16px; border: 1px solid #7C919F;
    border-radius: 0; background: #FFFFFF;
}
QCheckBox::indicator:checked { background: #0F766E; border-color: #0F766E; }
QPushButton#run {
    background: #0F766E;
    border: 1px solid #0F766E;
    border-radius: 0;
    color: #FFFFFF;
    font-size: 14px;
    font-weight: 700;
    min-height: 44px;
}
QPushButton#run:hover { background: #0B625C; border-color: #0B625C; }
QPushButton#run:pressed { background: #094E49; border-color: #094E49; }
QPushButton#run:disabled { background: #D6DCE4; border-color: #D6DCE4; color: #667085; }
QProgressBar {
    background: #DCE3EA; border: 0; border-radius: 0;
    min-height: 6px; max-height: 6px;
}
QProgressBar::chunk { background: #0F766E; border-radius: 0; }
"""