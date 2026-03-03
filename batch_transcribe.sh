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

# transcribe_whisper.py 的路径（与本脚本在同一目录）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TRANSCRIBE_PY="$SCRIPT_DIR/transcribe_whisper.py"

if [[ ! -f "$TRANSCRIBE_PY" ]]; then
    echo "❌ 找不到 transcribe_whisper.py（期望路径：$TRANSCRIBE_PY）"
    exit 1
fi

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

    # 如果 SRT 已存在则跳过
    if [[ -f "$SRT_FILE" ]]; then
        echo "  ⏭️  已有对应 SRT，跳过。"
        PASS=$((PASS + 1))
        continue
    fi

    echo "  ⏳ 开始转录..."

    if uv run "$TRANSCRIBE_PY" "$FILE"; then
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
