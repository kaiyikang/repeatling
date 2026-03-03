#!/usr/bin/env bash
# batch_transcribe.sh — 批量转录文件夹中的所有 MP3 文件
# 用法: ./batch_transcribe.sh <mp3文件夹路径>

set -euo pipefail

# ── 参数检查 ──────────────────────────────────────────────
if [[ $# -lt 1 ]]; then
    echo "用法: $0 <mp3文件夹路径>"
    exit 1
fi

FOLDER="$1"

if [[ ! -d "$FOLDER" ]]; then
    echo "❌ 错误：'$FOLDER' 不是一个有效的文件夹。"
    exit 1
fi

# ── 内嵌转录脚本 ─────────────────────────────────────────
TRANSCRIBE_PY=$(cat <<'EOF'
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "faster-whisper",
# ]
# ///

import os
import sys
from faster_whisper import WhisperModel

MODEL_SIZE   = "large-v3"
DEVICE       = "cpu"
COMPUTE_TYPE = "int8"

def is_sentence_end(word_text):
    end_chars = {'.', '?', '!', '。', '？', '！', '…'}
    clean = word_text.strip()
    return bool(clean) and clean[-1] in end_chars

def format_timestamp(seconds):
    ms = int((seconds % 1) * 1000)
    s  = int(seconds)
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

def main():
    audio_file = sys.argv[1]

    print(f"🚀 正在加载模型 ({MODEL_SIZE}) on {DEVICE}...")
    model = WhisperModel(MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE)

    print("🎙️ 正在转录...")
    segments, info = model.transcribe(audio_file, beam_size=5, word_timestamps=True, vad_filter=True)
    print(f"检测语言: {info.language} (置信度: {info.language_probability:.2f})")
    print("-" * 50)

    sentences, current_words = [], []
    for segment in segments:
        for word in segment.words:
            current_words.append(word)
            if is_sentence_end(word.word):
                start = current_words[0].start
                end   = current_words[-1].end
                text  = "".join(w.word for w in current_words).strip()
                sentences.append({"start": start, "end": end, "text": text})
                print(f"[{format_timestamp(start)} --> {format_timestamp(end)}] {text}")
                current_words = []

    if current_words:
        start = current_words[0].start
        end   = current_words[-1].end
        text  = "".join(w.word for w in current_words).strip()
        sentences.append({"start": start, "end": end, "text": text})
        print(f"[{format_timestamp(start)} --> {format_timestamp(end)}] {text}")

    srt_path = os.path.splitext(audio_file)[0] + ".srt"
    with open(srt_path, "w", encoding="utf-8") as f:
        for i, s in enumerate(sentences, 1):
            f.write(f"{i}\n{format_timestamp(s['start'])} --> {format_timestamp(s['end'])}\n{s['text']}\n\n")

    print("-" * 50)
    print(f"✅ 处理完成！字幕已保存为: {srt_path}")

if __name__ == "__main__":
    main()
EOF
)

# ── 收集 MP3 文件 ─────────────────────────────────────────
MP3_FILES=()
while IFS= read -r -d '' f; do
    MP3_FILES+=("$f")
done < <(find "$FOLDER" -maxdepth 1 -iname "*.mp3" -print0 | sort -z)

TOTAL=${#MP3_FILES[@]}

if [[ $TOTAL -eq 0 ]]; then
    echo "⚠️  文件夹中没有找到 MP3 文件：$FOLDER"
    exit 0
fi

echo "════════════════════════════════════════════════════"
echo "  批量转录任务"
echo "  文件夹 : $FOLDER"
echo "  共找到 : $TOTAL 个 MP3 文件"
echo "════════════════════════════════════════════════════"

# ── 逐一处理 ─────────────────────────────────────────────
PASS=0
FAIL=0

for i in "${!MP3_FILES[@]}"; do
    FILE="${MP3_FILES[$i]}"
    INDEX=$((i + 1))
    BASENAME="$(basename "$FILE")"
    SRT_FILE="${FILE%.*}.srt"

    echo ""
    echo "──────────────────────────────────────────────────"
    echo "  [$INDEX/$TOTAL] $BASENAME"

    if [[ -f "$SRT_FILE" ]]; then
        echo "  ⏭️  已有对应 SRT，跳过。"
        PASS=$((PASS + 1))
        continue
    fi

    echo "  ⏳ 开始转录..."

    if echo "$TRANSCRIBE_PY" | uv run --script - "$FILE"; then
        echo "  ✅ 完成 → $(basename "$SRT_FILE")"
        PASS=$((PASS + 1))
    else
        echo "  ❌ 转录失败：$BASENAME"
        FAIL=$((FAIL + 1))
    fi
done

# ── 汇总 ─────────────────────────────────────────────────
echo ""
echo "════════════════════════════════════════════════════"
echo "  批量转录完成"
echo "  成功：$PASS  失败：$FAIL  共：$TOTAL"
echo "════════════════════════════════════════════════════"

[[ $FAIL -eq 0 ]] && exit 0 || exit 1
