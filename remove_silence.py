#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
# 注意: 此脚本依赖系统安装的 ffmpeg，请确保 ffmpeg 已添加到环境变量

import sys
import os
import subprocess
from pathlib import Path


def remove_silence(input_file_path):
    # 1. 检查输入文件是否存在
    if not os.path.exists(input_file_path):
        print(f"错误: 文件 '{input_file_path}' 不存在。")
        sys.exit(1)

    # 2. 构建输出文件名 (原文件名 + 后缀)
    path_obj = Path(input_file_path)
    suffix_str = "_trimmed"  # 你可以在这里修改想要的后缀

    # 逻辑：文件名(不含扩展) + 后缀 + 原扩展名
    # 例如: input.mp3 -> input_trimmed.mp3
    output_file_path = path_obj.with_name(
        f"{path_obj.stem}{suffix_str}{path_obj.suffix}"
    )

    # 3. 构建 FFmpeg 命令
    # 注意：在 subprocess 中，不需要像 Bash 那样给参数加引号，列表项会自动处理
    cmd = [
        "ffmpeg",
        "-i",
        str(input_file_path),
        "-af",
        "silenceremove=start_periods=1:start_threshold=-50dB:stop_periods=-1:stop_duration=0.5:stop_threshold=-50dB",
        "-y",  # 自动覆盖同名输出文件 (可选)
        str(output_file_path),
    ]

    print(f"正在处理: {input_file_path} -> {output_file_path}")

    # 4. 执行命令
    try:
        # check=True 会在 ffmpeg 返回错误代码时抛出异常
        subprocess.run(cmd, check=True)
        print("✅ 处理完成！")
    except subprocess.CalledProcessError:
        print("❌ FFmpeg 处理出错。")
        sys.exit(1)
    except FileNotFoundError:
        print("❌ 错误: 未找到 ffmpeg。请确保已安装 ffmpeg 并添加到环境变量中。")
        sys.exit(1)


if __name__ == "__main__":
    # 检查命令行参数
    if len(sys.argv) < 2:
        print("错误: 请提供输入音频文件。")
        print(f"用法: python {os.path.basename(__file__)} <音频文件>")
        sys.exit(1)

    input_arg = sys.argv[1]
    remove_silence(input_arg)
