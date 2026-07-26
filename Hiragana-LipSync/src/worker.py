import traceback

from PySide6.QtCore import QObject, Signal, Slot


class Worker(QObject):
    progress = Signal(int)
    status = Signal(str)
    complete = Signal(dict)
    failed = Signal(str)

    def __init__(self, audio_path, output_path, model_dir, settings):
        super().__init__()
        self.audio_path = audio_path
        self.output_path = output_path
        self.model_dir = model_dir
        self.settings = settings

    @Slot()
    def run(self):
        try:
            from .core import generate

            result = generate(
                self.audio_path,
                self.output_path,
                self.model_dir,
                self.settings,
                self.progress.emit,
                self.status.emit,
            )
            self.complete.emit(result)
        except Exception:
            detail = traceback.format_exc()
            print(detail)
            self.failed.emit(detail)
