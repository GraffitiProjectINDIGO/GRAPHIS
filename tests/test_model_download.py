import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtWidgets import QApplication

from graphis.app.ki.backends import find_segmentation_models
from graphis.app.ki.model_download import (
    DownloadCancelled,
    download_segmentation_model,
    download_speech_model,
    is_downloaded,
    is_segmentation_model_downloaded,
    segmentation_model_info,
    speech_model_info,
)
from graphis.app.ki.model_paths import AIModelSettings, apply_ai_settings
from graphis.app.popups.model_download_popup import SegmentationModelDownloadPopup, SpeechModelDownloadPopup


class FakeResponse(io.BytesIO):
    def __init__(self, data, content_length=None):
        super().__init__(data)
        self.headers = {"Content-Length": str(len(data) if content_length is None else content_length)}

FILES = {"config.json": b"{}", "model.bin": b"x" * 3000, "tokenizer.json": b"t" * 10}


def fake_open(files, sizes=None):
    sizes = sizes or {name: len(data) for name, data in files.items()}

    def _open(url):
        if "/api/models/" in url:
            siblings = [{"rfilename": ".gitattributes", "size": 5}, {"rfilename": "README.md", "size": 5}]
            siblings += [{"rfilename": name, "size": sizes[name]} for name in files]
            return io.BytesIO(json.dumps({"sha": "abc123", "siblings": siblings}).encode())
        assert "/resolve/abc123/" in url, url
        return io.BytesIO(files[url.rsplit("/", 1)[1]])

    return _open


class SpeechModelDownloadTests(unittest.TestCase):
    def setUp(self):
        self.info = speech_model_info("base")
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name) / "speech"

    def tearDown(self):
        self.temp.cleanup()

    def test_download_creates_model_subfolder_atomically(self):
        progress = []
        with patch("graphis.app.ki.model_download._open", side_effect=fake_open(FILES)), \
                patch("graphis.app.ki.model_download.CHUNK_BYTES", 1000):
            target = download_speech_model(self.info, self.folder, lambda done, total: progress.append((done, total)))
        self.assertEqual(target, self.folder / "base")
        self.assertEqual(sorted(p.name for p in target.iterdir()), ["config.json", "model.bin", "tokenizer.json"])
        self.assertTrue(is_downloaded(self.folder, "base"))
        self.assertEqual(progress[-1], (3012, 3012))
        self.assertEqual([p.name for p in self.folder.iterdir()], ["base"])
        with patch("graphis.app.ki.model_download._open", side_effect=AssertionError("no network")):
            self.assertEqual(download_speech_model(self.info, self.folder), target)

    def test_cancel_and_incomplete_download_leave_no_model_folder(self):
        with patch("graphis.app.ki.model_download._open", side_effect=fake_open(FILES)), \
                patch("graphis.app.ki.model_download.CHUNK_BYTES", 1000):
            with self.assertRaises(DownloadCancelled):
                download_speech_model(self.info, self.folder, cancelled=lambda: True)
        self.assertEqual(list(self.folder.iterdir()), [])

        sizes = {name: len(data) for name, data in FILES.items()} | {"model.bin": 5000}
        with patch("graphis.app.ki.model_download._open", side_effect=fake_open(FILES, sizes)):
            with self.assertRaisesRegex(RuntimeError, "incomplete"):
                download_speech_model(self.info, self.folder)
        self.assertEqual(list(self.folder.iterdir()), [])
        self.assertFalse(is_downloaded(self.folder, "base"))

    def test_existing_unrelated_folder_is_not_overwritten(self):
        (self.folder / "base").mkdir(parents=True)
        (self.folder / "base" / "notes.txt").write_text("keep")
        with self.assertRaisesRegex(RuntimeError, "already exists"):
            download_speech_model(self.info, self.folder)
        self.assertEqual((self.folder / "base" / "notes.txt").read_text(), "keep")


class SegmentationModelDownloadTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name) / "segmentation"
        self.info = segmentation_model_info("SAM2")

    def tearDown(self):
        apply_ai_settings(AIModelSettings())
        self.temp.cleanup()

    def test_download_saves_checkpoint_directly_in_folder_and_backend_finds_it(self):
        data = b"w" * 2500
        progress = []
        with patch("graphis.app.ki.model_download._open", return_value=FakeResponse(data)) as opened, \
                patch("graphis.app.ki.model_download.CHUNK_BYTES", 1000):
            target = download_segmentation_model(self.info, self.folder, lambda d, t: progress.append((d, t)))
        opened.assert_called_once_with(self.info.url)
        self.assertEqual(target, self.folder / "sam2.1_l.pt")
        self.assertEqual(target.read_bytes(), data)
        self.assertEqual(progress[-1], (2500, 2500))
        self.assertEqual([p.name for p in self.folder.iterdir()], ["sam2.1_l.pt"])
        self.assertTrue(is_segmentation_model_downloaded(self.folder, "SAM2"))
        apply_ai_settings(AIModelSettings(segmentation_dir=str(self.folder)))
        self.assertEqual(find_segmentation_models()["ultralytics_sam2"], target)

    def test_cancelled_or_truncated_download_leaves_no_file(self):
        with patch("graphis.app.ki.model_download._open", return_value=FakeResponse(b"w" * 2500)), \
                patch("graphis.app.ki.model_download.CHUNK_BYTES", 1000):
            with self.assertRaises(DownloadCancelled):
                download_segmentation_model(self.info, self.folder, cancelled=lambda: True)
        self.assertEqual(list(self.folder.iterdir()), [])
        with patch("graphis.app.ki.model_download._open", return_value=FakeResponse(b"w" * 10, 5000)):
            with self.assertRaisesRegex(RuntimeError, "incomplete"):
                download_segmentation_model(self.info, self.folder)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_popup_offers_only_mobilesam_and_sam2(self):
        app = QApplication.instance() or QApplication([])  # noqa: F841
        popup = SegmentationModelDownloadPopup(default_folder=str(self.folder))
        names = [popup.model_list.item(i).data(0x0100) for i in range(popup.model_list.count())]
        self.assertEqual(names, ["MobileSAM", "SAM2"])
        self.assertEqual(popup._selected_info().name, "MobileSAM")
        self.assertIn("README", popup.status_label.text())


class SpeechModelDownloadPopupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_downloaded_models_are_marked_and_cannot_be_downloaded_again(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "small").mkdir()
            (Path(folder) / "small" / "model.bin").write_bytes(b"")
            popup = SpeechModelDownloadPopup(default_folder=folder)
            self.assertEqual(popup._selected_info().name, "small")
            self.assertIn("[downloaded]", popup.model_list.currentItem().text())
            self.assertFalse(popup.download_button.isEnabled())
            popup._select("base")
            self.assertTrue(popup.download_button.isEnabled())
            popup.folder_edit.setText("")
            self.assertFalse(popup.download_button.isEnabled())


if __name__ == "__main__":
    unittest.main()
