#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "mlx-audio",
# ]
# ///
# 注意: mlx-audio 仅支持 Apple Silicon (M1/M2/M3) Mac

from mlx_audio.stt.utils import load

DEBUG = True


def transcribe():

    model = load("mlx-community/VibeVoice-ASR-bf16")

    result = model.generate(
        audio="AUDIO_FILE.mp3",
        max_tokens=8192,
        temperature=0.0,
    )

    return result.text


print(transcribe())
