#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "faster-whisper",
# ]
# ///

import os
import sys
from faster_whisper import WhisperModel

# ================= 配置区域 =================
# 1. 音频路径 (请修改为你自己的文件)
AUDIO_FILE = "AUDIO_FILE.mp3" 

# 2. 模型大小 (macOS 推荐 base 或 small 进行测试，large-v3 效果最好但慢)
MODEL_SIZE = "large-v3"

# 3. 运行设备 (macOS M1/M2/M3 推荐 cpu + int8)
DEVICE = "cpu"
COMPUTE_TYPE = "int8"
# ===========================================

def is_sentence_end(word_text):
    """
    检查一个单词是否包含句子结束标点。
    支持中文和英文的常见结束符号。
    """
    end_chars = {'.', '?', '!', '。', '？', '！', '…'}
    # 清理空白字符后检查最后一个字符
    clean_word = word_text.strip()
    if not clean_word:
        return False
    return clean_word[-1] in end_chars

def format_timestamp(seconds):
    """将秒数转换为 SRT 格式的时间戳 (HH:MM:SS,mmm)"""
    millis = int((seconds - int(seconds)) * 1000)
    seconds = int(seconds)
    minutes = seconds // 60
    hours = minutes // 60
    minutes %= 60
    seconds %= 60
    return f"{hours:02}:{minutes:02}:{seconds:02},{millis:03}"

def main():
    # 从命令行参数获取音频文件，如果没有提供则使用默认配置
    if len(sys.argv) > 1:
        audio_file = sys.argv[1]
        print(f"📁 使用指定的音频文件: {audio_file}")
    else:
        audio_file = AUDIO_FILE
        print(f"📁 使用默认的音频文件: {audio_file}")

    if not os.path.exists(audio_file):
        print(f"❌ 错误：找不到文件 '{audio_file}'，请确保文件存在。")
        print(f"用法: python {os.path.basename(__file__)} [音频文件路径]")
        return

    print(f"🚀 正在加载模型 ({MODEL_SIZE}) on {DEVICE}...")
    model = WhisperModel(MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE)

    print("🎙️ 正在转录并进行词级对齐 (这可能需要一些时间)...")
    
    # 关键参数：
    # word_timestamps=True: 获取每个词的时间，用于精准重组句子
    # vad_filter=True: 过滤静音片段，提高时间轴准确度
    segments, info = model.transcribe(
        audio_file,
        beam_size=5,
        word_timestamps=True,
        vad_filter=True
    )

    print(f"检测语言: {info.language} (置信度: {info.language_probability:.2f})")
    print("-" * 50)

    #用于存储重组后的句子
    sentences = []
    current_words = []
    
    # 开始遍历 Whisper 生成的片段
    for segment in segments:
        for word in segment.words:
            current_words.append(word)
            
            # 如果检测到该词是句子的结尾
            if is_sentence_end(word.word):
                # 提取当前句子的信息
                start_time = current_words[0].start
                end_time = current_words[-1].end
                text = "".join([w.word for w in current_words]).strip()
                
                sentences.append({
                    "start": start_time,
                    "end": end_time,
                    "text": text
                })
                
                # 打印进度
                print(f"[{format_timestamp(start_time)} --> {format_timestamp(end_time)}] {text}")
                
                # 重置缓冲区
                current_words = []

    # 处理最后可能剩余的单词（没有标点结尾的情况）
    if current_words:
        start_time = current_words[0].start
        end_time = current_words[-1].end
        text = "".join([w.word for w in current_words]).strip()
        sentences.append({"start": start_time, "end": end_time, "text": text})
        print(f"[{format_timestamp(start_time)} --> {format_timestamp(end_time)}] {text}")

    # ================= 导出 SRT 字幕文件 =================
    srt_filename = os.path.splitext(audio_file)[0] + ".srt"
    with open(srt_filename, "w", encoding="utf-8") as f:
        for i, sent in enumerate(sentences):
            f.write(f"{i + 1}\n")
            f.write(f"{format_timestamp(sent['start'])} --> {format_timestamp(sent['end'])}\n")
            f.write(f"{sent['text']}\n\n")
            
    print("-" * 50)
    print(f"✅ 处理完成！字幕已保存为: {srt_filename}")

if __name__ == "__main__":
    main()