#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "faster-whisper",
#     "questionary",
# ]
# ///

import os
import sys
from pathlib import Path
from dataclasses import dataclass

import questionary
from questionary import Style
from faster_whisper import WhisperModel

# ─────────────────────────────────────────────
#  Constants
# ─────────────────────────────────────────────

MODEL_DIR = Path(__file__).resolve().parent / "models"

SENTENCE_END_CHARS = {'.', '?', '!', '。', '？', '！', '…'}

MODELS = [
    ("tiny",     "· 最快，精度较低"),
    ("base",     "· 快，适合测试"),
    ("small",    "· 均衡"),
    ("medium",   "· 较准确"),
    ("large-v2", "· 高精度"),
    ("large-v3", "· 最高精度 （默认）"),
    ("turbo",    "· 快速高精度 (需GPU)"),
]

DEVICES = [
    ("cpu",  "· 兼容所有设备，macOS 推荐 ✦"),
    ("cuda", "· NVIDIA GPU"),
    ("auto", "· 自动检测"),
]

CPU_COMPUTE_TYPES = [
    ("int8",    "· 最快，内存占用小 ✦ CPU推荐"),
    ("float32", "· 全精度"),
]

GPU_COMPUTE_TYPES = [
    ("float16",      "· GPU 推荐 ✦"),
    ("int8_float16", "· 省显存"),
    ("int8",         "· 最省内存"),
    ("float32",      "· 全精度"),
]

PROMPT_STYLE = Style([
    ("qmark",       "fg:#2563eb bold"),
    ("question",    "bold"),
    ("answer",      "fg:#2563eb bold"),
    ("pointer",     "fg:#2563eb bold"),
    ("highlighted", "fg:#2563eb bold"),
    ("selected",    "fg:#93c5fd"),
    ("instruction", "fg:#6b7280 italic"),
])

# ─────────────────────────────────────────────
#  Data
# ─────────────────────────────────────────────

@dataclass
class TranscribeConfig:
    audio_file: str
    model_size: str
    device: str
    compute_type: str

# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────

def is_model_cached(name: str) -> bool:
    return (MODEL_DIR / f"models--Systran--faster-whisper-{name}").exists()

def model_label(name: str, desc: str) -> str:
    badge = "✓ 已下载" if is_model_cached(name) else "↓ 需下载"
    return f"{name:<12}{desc}  [{badge}]"

def is_sentence_end(word: str) -> bool:
    clean = word.strip()
    return bool(clean) and clean[-1] in SENTENCE_END_CHARS

def format_timestamp(seconds: float) -> str:
    ms = int((seconds % 1) * 1000)
    s  = int(seconds)
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

def select(prompt: str, options: list[tuple], default: str, label_fn=None) -> str:
    fmt = label_fn or (lambda n, d: f"{n:<14}{d}")
    choices = [questionary.Choice(fmt(n, d), n) for n, d in options]
    answer = questionary.select(
        prompt, choices=choices, default=default,
        style=PROMPT_STYLE, instruction="(↑↓ 移动，回车确认)", use_indicator=True,
    ).ask()
    if answer is None:
        print("\n  已取消。")
        sys.exit(0)
    return answer

# ─────────────────────────────────────────────
#  Steps
# ─────────────────────────────────────────────

def parse_audio_file() -> str:
    if len(sys.argv) < 2:
        print("❌ 错误：未指定音频文件。")
        print(f"用法: uv run {os.path.basename(__file__)} <音频文件路径>")
        sys.exit(1)
    return sys.argv[1]

def prompt_config(audio_file: str) -> TranscribeConfig:
    print("\n  🎙  \033[1mWhisper 字幕生成器\033[0m\n")
    model_size   = select("① 选择模型大小", 
                            MODELS, 
                            default="large-v3", 
                            label_fn=model_label)
    device       = select("② 选择运行设备", 
                            DEVICES, 
                            default="cpu")
    compute_type = select(
        "③ 选择计算精度",
        CPU_COMPUTE_TYPES if device == "cpu" else GPU_COMPUTE_TYPES,
        default="int8" if device == "cpu" else "float16",
    )

    return TranscribeConfig(audio_file, model_size, device, compute_type)

def confirm_config(cfg: TranscribeConfig) -> None:
    filename = os.path.basename(cfg.audio_file)
    print(f"""
  ╭─────────────────────────────────╮
  │  模型  {cfg.model_size:<28}│
  │  设备  {cfg.device:<28}│
  │  精度  {cfg.compute_type:<28}│
  │  文件  {filename:<28}│
  ╰─────────────────────────────────╯""")
    ok = questionary.confirm("  确认开始转录？", default=True, style=PROMPT_STYLE).ask()
    if ok is None or not ok:
        print("  已取消。\n")
        sys.exit(0)


def transcribe(cfg: TranscribeConfig) -> list[dict]:
    print(f"\n🚀 正在加载模型 {cfg.model_size} ({cfg.device} / {cfg.compute_type})…")
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    model = WhisperModel(cfg.model_size, device=cfg.device, compute_type=cfg.compute_type,
                         download_root=str(MODEL_DIR))

    print("🎙️  正在转录，请稍候…\n")
    segments, info = model.transcribe(cfg.audio_file, beam_size=5, word_timestamps=True, vad_filter=True)
    print(f"  检测语言: {info.language}  (置信度 {info.language_probability:.0%})")
    print("─" * 52)
    return build_sentences(segments)


def build_sentences(segments) -> list[dict]:
    def flush_sentence(words: list) -> dict:
        start = words[0].start
        end   = words[-1].end
        text  = "".join(w.word for w in words).strip()
        print(f"  [{format_timestamp(start)} → {format_timestamp(end)}] {text}")
        return {"start": start, "end": end, "text": text}

    sentences, current_words = [], []
    for segment in segments:
        for word in segment.words:
            current_words.append(word)
            if is_sentence_end(word.word):
                sentences.append(flush_sentence(current_words))
                current_words = []
    if current_words:
        sentences.append(flush_sentence(current_words))
    return sentences

def export_srt(sentences: list[dict], audio_file: str) -> str:
    srt_path = os.path.splitext(audio_file)[0] + ".srt"
    with open(srt_path, "w", encoding="utf-8") as f:
        for i, s in enumerate(sentences, 1):
            f.write(f"{i}\n{format_timestamp(s['start'])} --> {format_timestamp(s['end'])}\n{s['text']}\n\n")
    return srt_path

# ─────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────

def main():
    
    audio_file = parse_audio_file()
    cfg        = prompt_config(audio_file)
    confirm_config(cfg)
    sentences  = transcribe(cfg)
    srt_path   = export_srt(sentences, audio_file)

    print("─" * 52)
    print(f"✅ 完成！字幕已保存至: {srt_path}\n")

if __name__ == "__main__":
    main()