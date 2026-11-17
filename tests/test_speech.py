import tempfile
import unittest
from pathlib import Path

import numpy as np
from PySide6.QtWidgets import QApplication

from graphis.app.ki.backends import find_segmentation_models, mobile_sam_model_candidates
from graphis.app.ki.model_paths import AIModelSettings, apply_ai_settings, load_ai_settings, write_ai_settings
from graphis.app.ki.speech import (
    SAMPLE_RATE,
    LiveTranscriber,
    available_speech_models,
    normalize_language,
    resolve_speech_model,
)
from graphis.app.popups.ai_config_popup import segmentation_status_text
from graphis.app.popups.speech_transcription_popup import SpeechTranscriptionPopup, SpeechWorker


def seconds(value):
    return int(value * SAMPLE_RATE)


class FakeRecognizer:
    """Treats samples with value 1.0 as speech and returns one word per transcribed region."""

    def __init__(self):
        self.calls = []
        self.loaded = []

    def load(self, model_name):
        self.loaded.append(model_name)

    def speech_regions(self, audio):
        speech = np.flatnonzero(audio > 0.5)
        if speech.size == 0:
            return []
        breaks = np.flatnonzero(np.diff(speech) > 1)
        starts = np.concatenate(([speech[0]], speech[breaks + 1]))
        ends = np.concatenate((speech[breaks] + 1, [speech[-1] + 1]))
        return list(zip(starts.tolist(), ends.tolist(), strict=True))

    def transcribe(self, audio, language=None, initial_prompt=None, beam_size=5, vad_filter=False):
        self.calls.append(
            {"samples": audio.size, "language": language, "prompt": initial_prompt, "beam": beam_size,
             "vad": vad_filter}
        )
        words = len(self.speech_regions(audio))
        return " ".join(f"word{len(self.calls)}" for _ in range(words)), "de"


def tone(duration):
    return np.ones(seconds(duration), dtype=np.float32)


def silence(duration):
    return np.zeros(seconds(duration), dtype=np.float32)


class LiveTranscriberTests(unittest.TestCase):
    def test_speech_in_progress_gives_fast_partial_text(self):
        recognizer = FakeRecognizer()
        live = LiveTranscriber(recognizer)
        live.append(silence(0.2))
        live.append(tone(1.0))
        update = live.step()
        self.assertEqual(update.committed, "")
        self.assertTrue(update.partial)
        self.assertEqual(recognizer.calls[-1]["beam"], 1)

    def test_pause_commits_utterance_and_locks_detected_language(self):
        recognizer = FakeRecognizer()
        live = LiveTranscriber(recognizer, "auto")
        live.append(tone(1.0))
        live.append(silence(0.8))
        update = live.step()
        self.assertTrue(update.committed)
        self.assertEqual(update.partial, "")
        self.assertEqual(recognizer.calls[-1]["beam"], 5)
        self.assertEqual(live.language, "de")
        live.append(tone(1.0))
        live.step()
        self.assertEqual(recognizer.calls[-1]["language"], "de")
        self.assertEqual(recognizer.calls[-1]["prompt"], live.text)

    def test_silence_is_not_transcribed_and_buffer_stays_small(self):
        recognizer = FakeRecognizer()
        live = LiveTranscriber(recognizer)
        for _ in range(20):
            live.append(silence(1.0))
            self.assertEqual(live.step().committed, "")
        self.assertEqual(recognizer.calls, [])
        self.assertLessEqual(live._pending.size, seconds(1.5))

    def test_long_speech_without_pause_is_cut_at_last_short_pause(self):
        recognizer = FakeRecognizer()
        live = LiveTranscriber(recognizer)
        live.append(tone(12.0))
        live.append(silence(0.1))
        live.append(tone(9.0))
        update = live.step()
        self.assertTrue(update.committed)
        self.assertEqual(recognizer.calls[-1]["samples"], seconds(12.0))
        self.assertEqual(live._pending.size, seconds(9.1))

    def test_final_step_commits_rest_with_vad(self):
        recognizer = FakeRecognizer()
        live = LiveTranscriber(recognizer, "en")
        live.append(tone(2.0))
        update = live.step(final=True)
        self.assertTrue(update.committed)
        self.assertTrue(recognizer.calls[-1]["vad"])
        self.assertEqual(recognizer.calls[-1]["language"], "en")
        self.assertEqual(live._pending.size, 0)


class SpeechModelTests(unittest.TestCase):
    def tearDown(self):
        apply_ai_settings(AIModelSettings())

    def test_models_are_found_only_in_the_configured_folder(self):
        self.assertEqual(normalize_language(" Auto "), None)
        self.assertEqual(normalize_language("DE"), "de")
        with self.assertRaisesRegex(RuntimeError, "not supported"):
            resolve_speech_model("model.pt")
        with self.assertRaisesRegex(RuntimeError, "No speech model folder"):
            resolve_speech_model("base")
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "small").mkdir()
            (root / "small" / "model.bin").write_bytes(b"")
            (root / "faster-whisper-base").mkdir()
            (root / "faster-whisper-base" / "model.bin").write_bytes(b"")
            (root / "notes").mkdir()
            apply_ai_settings(AIModelSettings(speech_dir=folder))
            self.assertEqual(available_speech_models(), ["faster-whisper-base", "small"])
            self.assertEqual(resolve_speech_model("small"), str(root / "small"))
            self.assertEqual(resolve_speech_model("base"), str(root / "faster-whisper-base"))
            with self.assertRaisesRegex(RuntimeError, "not found"):
                resolve_speech_model("medium")
            with self.assertRaisesRegex(RuntimeError, "model.bin"):
                resolve_speech_model(str(root / "notes"))
            self.assertEqual(resolve_speech_model(str(root / "small")), str(root / "small"))

    def test_no_models_are_found_without_configured_folders(self):
        apply_ai_settings(AIModelSettings())
        self.assertEqual(set(find_segmentation_models().values()), {None})
        self.assertEqual(available_speech_models(), [])
        self.assertEqual(mobile_sam_model_candidates(), ())

    def test_settings_round_trip_and_segmentation_folder_is_used(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            settings_file = root / "config" / "ai_models.json"
            self.assertTrue(write_ai_settings(settings_file, AIModelSettings(f" {folder} ", "")))
            loaded = load_ai_settings(settings_file)
            self.assertEqual(loaded, AIModelSettings(folder, ""))
            (root / "mobile_sam.pt").write_bytes(b"")
            apply_ai_settings(loaded)
            self.assertEqual(mobile_sam_model_candidates()[0], root / "mobile_sam.pt")
            found = find_segmentation_models()
            self.assertEqual(found["ultralytics_mobile_sam"], root / "mobile_sam.pt")
            self.assertEqual(segmentation_status_text(found), "Found: MobileSAM. Missing: SAM3, SAM2, TextureSAM.")
        self.assertEqual(load_ai_settings(Path(folder) / "missing.json"), AIModelSettings())


class SpeechWorkerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_worker_streams_updates_and_loads_model_once(self):
        recognizer = FakeRecognizer()
        worker = SpeechWorker(recognizer)
        updates = []
        worker.update.connect(lambda committed, partial, final: updates.append((committed, partial, final)))
        worker.start_session("base", "auto")
        pcm = (np.concatenate([tone(1.0), silence(0.8)]) * 32767).astype(np.int16).tobytes()
        worker.append_audio(pcm)
        worker.step(False)
        worker.step(True)
        self.assertTrue(updates[0][0])
        self.assertTrue(updates[-1][2])
        self.assertEqual(recognizer.loaded, ["base"])

    def test_popup_appends_committed_text_and_shows_partial(self):
        popup = SpeechTranscriptionPopup(worker=SpeechWorker(FakeRecognizer()))
        try:
            popup.transcription_text.setPlainText("Existing")
            popup._finishing = True
            popup._transcription_update("next sentence", "", False)
            popup._transcription_update("", "in progress", False)
            self.assertEqual(popup.transcription_text.toPlainText(), "Existing next sentence")
            self.assertEqual(popup.partial_label.text(), "in progress")
            popup._transcription_update("end", "", True)
            self.assertFalse(popup._finishing)
            self.assertEqual(popup.partial_label.text(), "")
            self.assertEqual(popup.transcription_text.toPlainText(), "Existing next sentence end")
        finally:
            popup.shutdown()


if __name__ == "__main__":
    unittest.main()
