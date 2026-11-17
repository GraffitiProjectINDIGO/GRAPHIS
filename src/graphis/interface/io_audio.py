# Copyright (C) 2026 Martin Wieser, Geert Verhoeven
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import numpy as np
from PySide6.QtMultimedia import QAudioDevice, QAudioFormat

WHISPER_SAMPLE_RATE = 16000
PCM16_SAMPLE_WIDTH = 2
MONO_CHANNELS = 1


def whisper_pcm16_format(device: QAudioDevice) -> QAudioFormat | None:
    audio_format = QAudioFormat()
    audio_format.setSampleRate(WHISPER_SAMPLE_RATE)
    audio_format.setChannelCount(MONO_CHANNELS)
    audio_format.setSampleFormat(QAudioFormat.SampleFormat.Int16)
    return audio_format if device.isFormatSupported(audio_format) else None


def pcm16_bytes_to_float32(data: bytes) -> np.ndarray:
    if len(data) < PCM16_SAMPLE_WIDTH:
        return np.zeros(0, dtype=np.float32)
    usable_length = len(data) - (len(data) % PCM16_SAMPLE_WIDTH)
    samples = np.frombuffer(data[:usable_length], dtype=np.int16)
    return samples.astype(np.float32) / 32768.0


def pcm16_audio_level(data: bytes) -> int:
    samples = pcm16_bytes_to_float32(data)
    if samples.size == 0:
        return 0
    return min(100, int(np.max(np.abs(samples)) * 100))
