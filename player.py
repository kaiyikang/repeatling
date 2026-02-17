#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "pygame",
#     "pysrt",
#     "pydub",
#     "pyperclip",
# ]
# ///

import pygame
import pysrt
from pydub import AudioSegment
from pydub.silence import split_on_silence
import sys
import re
import os
import pyperclip

# ==============================================================================
# ⚙️ 全局配置区域 (Configuration)
# ==============================================================================
class Config:
    # --- 1. 文件路径 ---
    AUDIO_FILE = "AUDIO_FILE.mp3"
    SRT_FILE = "SRT_FILE.srt"

    # --- 2. 窗口与显示 ---
    WINDOW_WIDTH = 800
    WINDOW_HEIGHT = 400
    WINDOW_TITLE = "Whisper Loop Player (V8 - Smooth Replay)"
    FPS = 30

    # --- 3. 字体设置 ---
    FONT_NAME = "Helvetica" 
    FONT_SIZE_SUBTITLE = 32
    FONT_SIZE_UI = 20
    LINE_SPACING = 10
    TEXT_MARGIN_X = 100

    # --- 4. 音频参数 ---
    PADDING_MS = 100
    FADE_MS = 30       # 这是一个静态淡入淡出，用于片段首尾
    
    # 动态交叉淡入淡出参数，用于消除按键爆音
    REPLAY_FADEOUT_MS = 50  # 旧声音淡出时间 (越短越快，但太短会爆音，30-50ms最佳)
    REPLAY_FADEIN_MS = 10   # 新声音淡入时间 (让开头更柔和)

    # 静音移除参数 (导出专用)
    # 任何低于 dBFS-16 的声音被视为静音
    # 持续超过 400ms 的静音会被切掉
    # 切割后保留 100ms 的余量(keep_silence)，避免声音太突兀
    SILENCE_MIN_LEN = 400 
    SILENCE_KEEP = 100

    # --- 5. 颜色主题 ---
    COLOR_BG = (30, 30, 30)
    COLOR_LOADING_BG = (20, 20, 20)
    COLOR_TEXT_VISIBLE = (255, 255, 255)
    COLOR_TEXT_HIDDEN = (100, 100, 100)
    COLOR_STATUS_TEXT = (100, 200, 100)
    COLOR_HINT_TEXT = (150, 150, 150)
    COLOR_LOADING_TEXT = (200, 200, 200)
    COLOR_TOAST_TEXT = (50, 255, 50)

# ==============================================================================

def wrap_text(text, font, max_width):
    """文本自动换行算法"""
    words = text.split(' ')
    lines = []
    current_line = []
    
    for word in words:
        test_line = ' '.join(current_line + [word])
        w, h = font.size(test_line)
        
        if w < max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(' '.join(current_line))
                current_line = [word]
            else:
                lines.append(word)
                current_line = []
    if current_line:
        lines.append(' '.join(current_line))
    return lines

def mask_text(text):
    return re.sub(r'\S', '-', text)

def remove_long_silence(sound_clip):
    """
    移除音频片段中过长的静音部分，并紧凑拼接。
    不修改原对象，返回一个新的 AudioSegment。
    """
    try:
        # 动态计算静音阈值：比当前片段的平均响度低 16dB
        thresh = sound_clip.dBFS - 16
        
        # split_on_silence 返回的是非静音片段的列表
        chunks = split_on_silence(
            sound_clip, 
            min_silence_len=Config.SILENCE_MIN_LEN, 
            silence_thresh=thresh, 
            keep_silence=Config.SILENCE_KEEP
        )
        
        if len(chunks) == 0:
            return sound_clip # 如果没检测到（或者是纯静音），返回原片段
            
        # 将切碎的非静音片段重新拼起来
        processed_clip = chunks[0]
        for i in range(1, len(chunks)):
            processed_clip += chunks[i]
            
        return processed_clip
    except Exception as e:
        print(f"Silence removal failed: {e}")
        return sound_clip # 出错则返回原版

def main():
    # 1. 初始化 (关键：Pre_init 减小 Buffer 以降低延迟)
    # buffer=1024 比默认的 4096 响应更快，能减少操作时的迟滞感
    pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=1024)
    pygame.init()
    pygame.font.init()
    
    # 2. 设置窗口
    screen = pygame.display.set_mode((Config.WINDOW_WIDTH, Config.WINDOW_HEIGHT))
    pygame.display.set_caption(Config.WINDOW_TITLE)
    clock = pygame.time.Clock()
    
    # 3. 加载字体
    try:
        ui_font = pygame.font.SysFont(Config.FONT_NAME, Config.FONT_SIZE_UI) 
        sub_font = pygame.font.SysFont(Config.FONT_NAME, Config.FONT_SIZE_SUBTITLE, bold=True)
    except:
        ui_font = pygame.font.SysFont(None, Config.FONT_SIZE_UI)
        sub_font = pygame.font.SysFont(None, Config.FONT_SIZE_SUBTITLE)

    # 4. 加载界面
    screen.fill(Config.COLOR_LOADING_BG)
    loading_str = f"Processing audio..."
    loading_text = ui_font.render(loading_str, True, Config.COLOR_LOADING_TEXT)
    txt_rect = loading_text.get_rect(center=(Config.WINDOW_WIDTH // 2, Config.WINDOW_HEIGHT // 2))
    screen.blit(loading_text, txt_rect)
    pygame.display.flip()

    # 5. 数据处理
    try:
        subs = pysrt.open(Config.SRT_FILE)
        full_audio = AudioSegment.from_file(Config.AUDIO_FILE)
        audio_len_ms = len(full_audio)
        
        audio_segments = [] # 用于播放 (Pygame Sound objects)
        raw_clips = []      # 用于导出 (Pydub AudioSegment objects)        print(f"Processing {len(subs)} segments...")
        print(f"Processing {len(subs)} segments...")
        
        for sub in subs:
            start_ms = (sub.start.hours * 3600 + sub.start.minutes * 60 + sub.start.seconds) * 1000 + sub.start.milliseconds
            end_ms = (sub.end.hours * 3600 + sub.end.minutes * 60 + sub.end.seconds) * 1000 + sub.end.milliseconds
            
            safe_start = max(0, start_ms - Config.PADDING_MS)
            safe_end = min(audio_len_ms, end_ms + Config.PADDING_MS)
            
            clip = full_audio[safe_start:safe_end]
            clip = clip.fade_in(Config.FADE_MS).fade_out(Config.FADE_MS)
            
            # 保存原始片段
            raw_clips.append(clip)

            # 保存播放对象
            sound = pygame.mixer.Sound(buffer=clip.raw_data)
            audio_segments.append(sound)

    except Exception as e:
        print(f"Error loading files: {e}")
        return

    # ==========================================================================
    # 双通道音频管理系统
    # ==========================================================================
    pygame.mixer.set_num_channels(8) # 确保有足够通道
    channel_list = [pygame.mixer.Channel(0), pygame.mixer.Channel(1)]
    active_channel_index = 0 # 0 或 1，指示当前主要使用的通道

    # 6. 状态变量
    current_idx = 0
    is_looping = False
    is_paused = False
    show_subtitle = True
    running = True
    toast_end_time = 0
    toast_message = "" # 动态消息内容
    
    def play_sound(force_restart=True):
        """
        force_restart: 如果为True，则执行平滑切换逻辑（用于重播或切句）
        """
        nonlocal active_channel_index
        
        if 0 <= current_idx < len(audio_segments):
            target_sound = audio_segments[current_idx]
            
            if force_restart:
                # 策略：Ping-Pong 切换
                # 1. 获取正在播放的旧通道，让它快速淡出（不要 stop，stop 会爆音）
                old_channel = channel_list[active_channel_index]
                old_channel.fadeout(Config.REPLAY_FADEOUT_MS)
                
                # 2. 切换到另一个通道作为新通道
                active_channel_index = 1 - active_channel_index
                new_channel = channel_list[active_channel_index]
                
                # 3. 在新通道播放新声音，并带一点点淡入，进一步掩盖接缝
                new_channel.play(target_sound, fade_ms=Config.REPLAY_FADEIN_MS)
            else:
                # 简单的恢复播放 (如果之前只是 paused)
                # 注意：Pygame的 channel.unpause() 比较简单，这里我们主要处理重播逻辑
                # 如果是解除暂停，通常使用 unpause
                pygame.mixer.unpause()

    # 初始播放
    play_sound(force_restart=True)

    # 7. 主循环
    while running:
        # --- 事件处理 ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            elif event.type == pygame.KEYDOWN:
                # [Ctrl+C / Cmd+C] 复制文本
                if event.key == pygame.K_c and (event.mod & pygame.KMOD_CTRL or event.mod & pygame.KMOD_META):
                    text_to_copy = subs[current_idx].text
                    pyperclip.copy(text_to_copy)
                    toast_message = "Copied Text!"
                    toast_end_time = pygame.time.get_ticks() + 1500

                # [x] 导出音频
                elif event.key == pygame.K_x:
                    try:
                        # 构造文件名: id_原文件名
                        base_name = os.path.basename(Config.AUDIO_FILE)
                        # 使用 current_idx + 1 作为 id，格式化为 001_xxx.mp3 以便排序
                        file_name = f"{current_idx + 1:03d}_{base_name}"
                        
                        # 导出
                        original_clip = raw_clips[current_idx]
                        clean_clip = remove_long_silence(original_clip)
                        clean_clip.export(file_name, format="mp3")
                        
                        toast_message = f"Saved: {file_name}"
                        toast_end_time = pygame.time.get_ticks() + 2000
                        print(f"Exported: {file_name}")
                    except Exception as e:
                        print(f"Export Error: {e}")
                        toast_message = "X Save Error!"
                        toast_end_time = pygame.time.get_ticks() + 2000

                # [Space] 暂停/播放
                elif event.key == pygame.K_SPACE:
                    if is_paused:
                        # 1. 如果是暂停状态 -> 继续播放
                        pygame.mixer.unpause()
                        is_paused = False
                    elif pygame.mixer.get_busy():
                        # 2. 如果正在播放 -> 暂停
                        pygame.mixer.pause()
                        is_paused = True
                    else:
                        # 3. 如果没播放也没暂停（说明播放完了） -> 重头播放
                        play_sound(force_restart=True)
                        is_paused = False
                
                # [Up] 重播本句 (无爆音版)
                elif event.key == pygame.K_UP:
                    play_sound(force_restart=True)
                    is_paused = False

                # [Down] 显隐字幕
                elif event.key == pygame.K_DOWN:
                    show_subtitle = not show_subtitle

                # [Right] 下一句
                elif event.key == pygame.K_RIGHT:
                    if current_idx < len(subs) - 1:
                        current_idx += 1
                        play_sound(force_restart=True)
                        is_paused = False
                
                # [Left] 上一句
                elif event.key == pygame.K_LEFT:
                    if current_idx > 0:
                        current_idx -= 1
                        play_sound(force_restart=True)
                        is_paused = False
                
                # [R] 循环模式
                elif event.key == pygame.K_r:
                    is_looping = not is_looping

        # --- 播放逻辑 (自动循环) ---
        if not pygame.mixer.get_busy() and not is_paused:
            if is_looping:
                play_sound(force_restart=True)
            else:
                pass

        # --- 绘制逻辑 ---
        screen.fill(Config.COLOR_BG)

        # A. 状态栏
        status_str = f"Seg: {current_idx+1}/{len(subs)} | Loop: {'ON' if is_looping else 'OFF'} | Subs: {'SHOW' if show_subtitle else 'HIDDEN'}"
        status_surface = ui_font.render(status_str, True, Config.COLOR_STATUS_TEXT)
        screen.blit(status_surface, (20, 20))

        # B. 字幕内容
        raw_text = subs[current_idx].text
        
        if show_subtitle:
            display_text = raw_text
            txt_color = Config.COLOR_TEXT_VISIBLE
        else:
            display_text = mask_text(raw_text)
            txt_color = Config.COLOR_TEXT_HIDDEN

        wrapped_lines = wrap_text(display_text, sub_font, Config.WINDOW_WIDTH - Config.TEXT_MARGIN_X)
        
        line_height = sub_font.get_height() + Config.LINE_SPACING
        total_height = len(wrapped_lines) * line_height
        start_y = (Config.WINDOW_HEIGHT - total_height) // 2
        
        for i, line in enumerate(wrapped_lines):
            txt_surface = sub_font.render(line, True, txt_color)
            txt_rect = txt_surface.get_rect(center=(Config.WINDOW_WIDTH // 2, start_y + i * line_height))
            screen.blit(txt_surface, txt_rect)

        # C. 操作提示
        hint_str = "[Space]:Pause [Up]:Replay [x]:Export Audio [Cmd+C]:Copy"
        hint_surface = ui_font.render(hint_str, True, Config.COLOR_HINT_TEXT)
        screen.blit(hint_surface, (20, Config.WINDOW_HEIGHT - 30))

        if pygame.time.get_ticks() < toast_end_time:
            toast_surf = ui_font.render(toast_message, True, Config.COLOR_TOAST_TEXT)
            screen.blit(toast_surf, (Config.WINDOW_WIDTH - toast_surf.get_width() - 20, 20))

        pygame.display.flip()
        clock.tick(Config.FPS)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()