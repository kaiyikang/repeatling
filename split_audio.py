#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
# 注意: 此脚本依赖系统安装的 ffmpeg，请确保 ffmpeg 已添加到环境变量

import os
import sys
import subprocess
import re
import argparse
import shutil

# ================= 配置区域 =================
DEFAULT_SEGMENT_TIME = 180  # 目标切分时长 (5分钟)
SILENCE_THRESH = "-40dB"  # 静音阈值
SILENCE_DURATION = 0.5  # 持续多久算静音 (秒)
SEARCH_WINDOW = 60  # 在目标时间点前后多少秒内寻找静音
# ===========================================


def check_ffmpeg():
    """检查系统是否安装了 ffmpeg"""
    if shutil.which("ffmpeg") is None:
        print("❌ 错误: 未找到 ffmpeg。请先安装 ffmpeg 并将其加入环境变量。")
        sys.exit(1)


def get_silence_points_and_duration(input_file):
    """
    第一步：扫描整个音频，获取总时长和所有静音点
    返回: (total_duration, silence_starts_list)
    """
    print(f"🔍 正在分析音频 '{input_file}' 寻找静音点...")

    # 构造命令：只处理音频，使用 silencedetect 滤镜，不输出文件
    cmd = [
        "ffmpeg",
        "-i",
        input_file,
        "-af",
        f"silencedetect=noise={SILENCE_THRESH}:d={SILENCE_DURATION}",
        "-f",
        "null",
        "-",
    ]

    # 运行命令并捕获 stderr (ffmpeg 的日志都在 stderr)
    try:
        result = subprocess.run(
            cmd, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="ignore"
        )
    except Exception as e:
        print(f"❌ 运行 FFmpeg 失败: {e}")
        sys.exit(1)

    log = result.stderr

    # 1. 获取总时长 (Duration: 00:05:20.10)
    duration_match = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", log)
    total_seconds = 0.0
    if duration_match:
        h, m, s = map(float, duration_match.groups())
        total_seconds = h * 3600 + m * 60 + s
    else:
        print("⚠️ 警告: 无法读取音频总时长，可能导致处理异常。")

    # 2. 获取所有静音开始点 (silence_start: 123.456)
    silence_starts = []
    for line in log.split("\n"):
        if "silence_start" in line:
            match = re.search(r"silence_start: ([\d\.]+)", line)
            if match:
                silence_starts.append(float(match.group(1)))

    print(
        f"✅ 分析完成。总时长: {total_seconds:.2f}秒，发现 {len(silence_starts)} 个静音点。"
    )
    return total_seconds, silence_starts


def calculate_split_points(total_duration, silence_starts, target_segment_time):
    """
    第二步：算法核心。计算最佳切割点。
    """
    split_points = []
    current_target = target_segment_time
    last_split_point = 0.0

    # 如果音频比目标时长短，不需要切割
    if total_duration <= target_segment_time:
        return []

    while current_target < total_seconds:
        best_point = -1
        min_diff = float("inf")

        # 在静音点列表中寻找距离 current_target 最近的点
        # 搜索范围：current_target - WINDOW 到 current_target + WINDOW
        window_start = current_target - SEARCH_WINDOW
        window_end = current_target + SEARCH_WINDOW

        found_silence = False

        for s_time in silence_starts:
            # 必须在上次切割点之后
            if s_time <= last_split_point + 10:  # 加10秒缓冲，避免切太碎
                continue

            # 优化：如果静音点已经远超搜索窗口，停止循环
            if s_time > window_end:
                break

            # 如果在窗口内
            if window_start <= s_time <= window_end:
                diff = abs(s_time - current_target)
                if diff < min_diff:
                    min_diff = diff
                    best_point = s_time
                    found_silence = True

        if found_silence:
            split_points.append(f"{best_point:.3f}")
            last_split_point = best_point
            current_target = best_point + target_segment_time
            # print(f"  -> 找到静音点: {best_point:.2f} (偏移 {min_diff:.2f}s)")
        else:
            # 没找到合适的静音，强制按时间切
            split_points.append(f"{current_target:.3f}")
            last_split_point = current_target
            current_target += target_segment_time
            # print(f"  -> 未找到静音，强制切割: {last_split_point:.2f}")

    return ",".join(split_points)


def split_audio(input_file, output_dir, split_points_str):
    """
    第三步：执行切割
    """
    filename = os.path.basename(input_file)
    name_no_ext = os.path.splitext(filename)[0]

    # 输出文件模板
    output_template = os.path.join(output_dir, f"{name_no_ext}_%03d.mp3")

    cmd = [
        "ffmpeg",
        "-i",
        input_file,
        "-f",
        "segment",
        "-c:a",
        "libmp3lame",
        "-q:a",
        "2",  # MP3 VBR 质量 2 (高)
        "-reset_timestamps",
        "1",  # 重置时间戳
    ]

    if split_points_str:
        # 智能切割模式
        cmd.extend(["-segment_times", split_points_str])
        print(f"🚀 开始执行智能切割 (共 {len(split_points_str.split(',')) + 1} 段)...")
    else:
        # 备用：如果没有计算出切割点（可能是短音频或无静音），按固定时间切
        cmd.extend(["-segment_time", str(DEFAULT_SEGMENT_TIME)])
        print("⚠️ 未使用智能切割点，将执行标准等分切割...")

    cmd.append(output_template)

    # 为了保持界面整洁，可以把 ffmpeg 的输出隐藏，只显示 Python 的提示
    # 如果想看 ffmpeg 进度，可以把 stdout/stderr 去掉
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    # subprocess.run(cmd) # 调试时用这行


def main():
    parser = argparse.ArgumentParser(
        description="智能音频切割工具：在静音处将音频切分为5分钟片段。"
    )
    parser.add_argument("input_file", help="输入的音频文件路径")
    args = parser.parse_args()

    input_path = args.input_file

    # 1. 检查文件
    if not os.path.isfile(input_path):
        print(f"❌ 错误: 文件 '{input_path}' 不存在。")
        return

    check_ffmpeg()

    # 2. 准备输出目录
    file_dir = os.path.dirname(os.path.abspath(input_path))
    file_name = os.path.basename(input_path)
    name_no_ext = os.path.splitext(file_name)[0]
    output_dir = os.path.join(file_dir, name_no_ext)

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"📂 创建目录: {output_dir}")
    else:
        print(f"📂 目录已存在: {output_dir}")

    # 3. 获取信息与静音点
    global total_seconds
    total_seconds, silence_starts = get_silence_points_and_duration(input_path)

    # 4. 计算切割时间戳
    split_points_str = calculate_split_points(
        total_seconds, silence_starts, DEFAULT_SEGMENT_TIME
    )

    if split_points_str:
        print(f"💡 计算出的切割时间点: {split_points_str}")

    # 5. 执行切割
    split_audio(input_path, output_dir, split_points_str)

    print(f"🎉 全部完成！文件已保存在: {output_dir}")


if __name__ == "__main__":
    main()
