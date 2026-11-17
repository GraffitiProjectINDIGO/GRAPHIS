# Copyright (C) 2026 Martin Wieser, Geert Verhoeven
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

"""Speech recognition with faster-whisper on CPU.

faster-whisper (CTranslate2, int8) is fast enough on CPU for dictated descriptions and
transcriptions, so speech needs neither PyTorch nor a GPU and behaves the same on Windows,
Linux and macOS. ``LiveTranscriber`` adds real-time output: finished utterances are
committed at speech pauses, and the utterance still being spoken is shown as partial text.
"""

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from threading import Lock

import numpy as np

from graphis.app.ki.model_paths import speech_model_dir

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16000
DEFAULT_SPEECH_MODEL = "base"
SPEECH_LANGUAGE_CHOICES = ("auto", "en", "de", "fr", "it", "es", "nl", "pt", "pl", "cs", "hu", "sk", "sl", "hr")

MIN_AUDIO_SECONDS = 0.3
COMMIT_PAUSE_SECONDS = 0.5
MAX_LIVE_CHUNK_SECONDS = 20.0
KEEP_SILENCE_SECONDS = 0.5
PROMPT_CONTEXT_CHARACTERS = 200


def speech_available() -> tuple[bool, str]:
    try:
        import faster_whisper  # noqa: F401
    except ImportError as err:
        return False, f"Missing Python dependency: {err.name}. Install with: pip install .[speech]"
    return True, "Speech recognition available."


def _is_model_folder(path: Path) -> bool:
    return (path / "model.bin").is_file()


def available_speech_models(folder: Path | None = None) -> list[str]:
    """Names of the faster-whisper model folders (containing model.bin) in the speech model folder."""
    folder = speech_model_dir() if folder is None else folder
    if folder is None or not folder.is_dir():
        return []
    if _is_model_folder(folder):
        return [folder.name]
    return sorted(child.name for child in folder.iterdir() if child.is_dir() and _is_model_folder(child))


def resolve_speech_model(model_name: str, folder: Path | None = None) -> str:
    """Return the local folder of a speech model. GRAPHIS never downloads models itself."""
    model_name = (model_name or DEFAULT_SPEECH_MODEL).strip()
    if Path(model_name).suffix.lower() == ".pt":
        raise RuntimeError(
            "OpenAI Whisper .pt files are not supported. Use a faster-whisper (CTranslate2) model folder."
        )
    path = Path(model_name).expanduser()
    if path.is_absolute() or len(path.parts) > 1:
        if not _is_model_folder(path):
            raise RuntimeError(f"No faster-whisper model (model.bin) found in: {path}")
        return os.fspath(path)

    folder = speech_model_dir() if folder is None else folder
    if folder is None:
        raise RuntimeError(
            "No speech model folder is configured. Select it in the AI configuration (see README, AI models)."
        )
    candidates = (folder, folder / model_name, folder / f"faster-whisper-{model_name}")
    for candidate in candidates:
        if _is_model_folder(candidate) and (candidate != folder or folder.name == model_name):
            return os.fspath(candidate)
    raise RuntimeError(
        f"Speech model '{model_name}' not found in {folder}. "
        "Download it as described in the README (AI models) or choose another model."
    )


def default_cpu_threads() -> int:
    # Leave one core for the GUI and audio capture.
    return max(1, min(8, (os.cpu_count() or 4) - 1))


def normalize_language(language: str | None) -> str | None:
    language = (language or "").strip().lower()
    return None if language in {"", "auto"} else language


class SpeechRecognizer:
    """Keeps one faster-whisper model loaded and transcribes 16 kHz mono float32 audio."""

    def __init__(self, cpu_threads: int | None = None):
        self._cpu_threads = cpu_threads or default_cpu_threads()
        self._model = None
        self._model_name: str | None = None
        self._model_source: str | None = None
        self._lock = Lock()

    @property
    def model_name(self) -> str | None:
        return self._model_name

    def load(self, model_name: str = DEFAULT_SPEECH_MODEL) -> None:
        model_name = (model_name or DEFAULT_SPEECH_MODEL).strip()
        with self._lock:
            source = resolve_speech_model(model_name)
            if self._model is not None and self._model_source == source:
                return
            available, message = speech_available()
            if not available:
                raise RuntimeError(message)
            from faster_whisper import WhisperModel

            logger.info("Loading speech model %s on CPU with %d threads", source, self._cpu_threads)
            self._model = None
            self._model_name = None
            self._model = WhisperModel(
                source, device="cpu", compute_type="int8", cpu_threads=self._cpu_threads, local_files_only=True
            )
            self._model_name = model_name
            self._model_source = source

    def transcribe(
        self,
        audio: np.ndarray,
        language: str | None = None,
        initial_prompt: str | None = None,
        beam_size: int = 5,
        vad_filter: bool = False,
    ) -> tuple[str, str | None]:
        """Return the text and the language used or detected."""
        if self._model is None:
            raise RuntimeError("No speech model is loaded.")
        audio = np.ascontiguousarray(audio, dtype=np.float32)
        if audio.size < int(MIN_AUDIO_SECONDS * SAMPLE_RATE):
            return "", language
        with self._lock:
            segments, info = self._model.transcribe(
                audio,
                language=language,
                beam_size=beam_size,
                initial_prompt=initial_prompt or None,
                condition_on_previous_text=False,
                vad_filter=vad_filter,
                without_timestamps=True,
            )
            text = " ".join(segment.text.strip() for segment in segments).strip()
        return text, getattr(info, "language", language)

    def speech_regions(self, audio: np.ndarray) -> list[tuple[int, int]]:
        """Return (start, end) sample ranges that contain speech."""
        from faster_whisper.vad import VadOptions, get_speech_timestamps

        options = VadOptions(min_silence_duration_ms=300, speech_pad_ms=150)
        timestamps = get_speech_timestamps(np.ascontiguousarray(audio, dtype=np.float32), options)
        return [(int(item["start"]), int(item["end"])) for item in timestamps]


@dataclass(frozen=True)
class LiveUpdate:
    committed: str = ""
    partial: str = ""


class LiveTranscriber:
    """Real-time transcription of a growing recording.

    Call ``append`` with new audio and ``step`` regularly. Each utterance is transcribed once
    when the speaker pauses and returned as committed text. Until then, ``step`` returns a
    fast partial transcription of the utterance in progress. ``step(final=True)`` commits
    everything that is left when recording stops.
    """

    def __init__(self, recognizer: SpeechRecognizer, language: str | None = None):
        self._recognizer = recognizer
        self.language = normalize_language(language)
        self._pending = np.zeros(0, dtype=np.float32)
        self._new_chunks: list[np.ndarray] = []
        self._committed: list[str] = []

    @property
    def text(self) -> str:
        return " ".join(self._committed)

    def append(self, samples: np.ndarray) -> None:
        if samples.size:
            self._new_chunks.append(np.asarray(samples, dtype=np.float32))

    def step(self, final: bool = False) -> LiveUpdate:
        if self._new_chunks:
            self._pending = np.concatenate([self._pending, *self._new_chunks])
            self._new_chunks = []
        audio = self._pending

        if final:
            self._pending = np.zeros(0, dtype=np.float32)
            text, _ = self._transcribe(audio, vad_filter=True)
            return LiveUpdate(committed=self._commit(text))

        if audio.size < int(MIN_AUDIO_SECONDS * SAMPLE_RATE):
            return LiveUpdate()

        regions = self._recognizer.speech_regions(audio)
        if not regions:
            # Silence only: keep a short tail so the start of the next word is not cut.
            self._pending = audio[-int(KEEP_SILENCE_SECONDS * SAMPLE_RATE):]
            return LiveUpdate()

        speech_start = regions[0][0]
        speech_end = regions[-1][1]
        if audio.size - speech_end >= int(COMMIT_PAUSE_SECONDS * SAMPLE_RATE):
            text, _ = self._transcribe(audio[speech_start:speech_end])
            self._pending = audio[speech_end:]
            return LiveUpdate(committed=self._commit(text))

        if audio.size >= int(MAX_LIVE_CHUNK_SECONDS * SAMPLE_RATE):
            # Long speech without a clear pause: cut at the last short pause, or here.
            cut = regions[-2][1] if len(regions) > 1 else audio.size
            text, _ = self._transcribe(audio[speech_start:cut])
            self._pending = audio[cut:]
            return LiveUpdate(committed=self._commit(text))

        partial, _ = self._transcribe(audio[speech_start:], beam_size=1)
        return LiveUpdate(partial=partial)

    def _transcribe(self, audio: np.ndarray, beam_size: int = 5, vad_filter: bool = False) -> tuple[str, str | None]:
        prompt = self.text[-PROMPT_CONTEXT_CHARACTERS:] or None
        text, detected = self._recognizer.transcribe(audio, self.language, prompt, beam_size, vad_filter)
        if text and self.language is None and detected:
            # Keep the language of the first utterance; detection on short partials is unreliable.
            self.language = detected
        return text, detected

    def _commit(self, text: str) -> str:
        text = text.strip()
        if text:
            self._committed.append(text)
        return text


def transcribe_audio(
    audio: np.ndarray, model_name: str = DEFAULT_SPEECH_MODEL, language: str | None = None,
    recognizer: SpeechRecognizer | None = None,
) -> str:
    """Transcribe a complete recording in one call."""
    recognizer = recognizer or SpeechRecognizer()
    recognizer.load(model_name)
    text, _ = recognizer.transcribe(audio, normalize_language(language), vad_filter=True)
    return text
