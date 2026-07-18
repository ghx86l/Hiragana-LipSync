import traceback

from PySide6.QtCore import QObject, Signal, Slot

from .core import generate


class Worker(QObject):
    progress = Signal(int)
    complete = Signal(dict)
    failed = Signal(str)

    def __init__(self, audio_path, output_path, model_dir, use_gpu):
        super().__init__()
        self.audio_path = audio_path
        self.output_path = output_path
        self.model_dir = model_dir
        self.use_gpu = use_gpu

    @Slot()
    def run(self):
        try:
            result = generate(
                self.audio_path,
                self.output_path,
                self.model_dir,
                self.use_gpu,
                self.progress.emit,
            )
            self.complete.emit(result)
        except Exception:
            detail = traceback.format_exc()
            print(detail)
            self.failed.emit(detail)