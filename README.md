# Repeatling: Language Learning Audio Toolkit

Python tools for audio-based language learning: transcribe, split, and loop-play with subtitles.

## Quick Start

```bash
./setup_env.sh          # Install uv and ffmpeg
uv run player.py        # Launch player (edit AUDIO_FILE/SRT_FILE in script)
```

## Tools

| Script                          | Purpose                              |
| ------------------------------- | ------------------------------------ |
| `player.py`                     | Loop-play audio by subtitle segments |
| `transcribe_whisper.py <audio>` | Speech-to-text with Whisper          |
| `split_audio.py <audio>`        | Split audio by silence               |
| `remove_silence.py <audio>`     | Remove silent parts                  |

## Requirements

- Python 3.10+
- [uv](https://github.com/astral-sh/uv)
- ffmpeg
