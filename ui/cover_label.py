from .common import *

class CoverLabel(QLabel):
    """Borítókép, ami a rendelkezésre álló helyhez igazodik (arányosan)."""

    def __init__(self, parent=None):
        super().__init__("Nincs borító", parent)
        self._pix = None
        self.setMinimumSize(80, 110)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet(
            "border: 3px solid #444; background: #1a1a1a; border-radius: 6px;"
        )

    def set_cover(self, path):
        self._pix = QPixmap(path) if path and os.path.exists(path) else None
        if self._pix is None or self._pix.isNull():
            self._pix = None
            self.setText("Nincs borító")
        self._rescale()

    def _rescale(self):
        if self._pix is not None:
            self.setPixmap(self._pix.scaled(
                self.width() - 8, self.height() - 8,
                Qt.KeepAspectRatio, Qt.SmoothTransformation
            ))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._rescale()


# ====================== DETAILS PANEL ======================
