from .common import *

class ScraperWorker(QThread):
    """Háttérszálban futó scraper."""
    finished = Signal(int)
    log_signal = Signal(str)

    def __init__(self, mode="update"):
        super().__init__()
        self.mode = mode
        self.scraper = Scraper(log_callback=self.log_signal.emit)

    def run(self):
        try:
            if self.mode == "update":
                count = self.scraper.scrape_update()
            elif self.mode == "older":
                count = self.scraper.scrape_older(max_pages=3000)
            else:
                count = self.scraper.scrape_full(max_pages=3000)
            self.finished.emit(count)
        except Exception as e:
            self.log_signal.emit(f"❌ Hiba: {e}")
            self.finished.emit(0)

    def stop(self):
        self.scraper.stop()


# ====================== SETTINGS DIALOG ======================
