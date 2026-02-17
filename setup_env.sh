#!/bin/bash

# =============================================================================
# 一键配置脚本: 安装 uv 和 ffmpeg (带检查功能)
# =============================================================================

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 检查命令是否存在
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# 检测操作系统
detect_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "linux"
    else
        echo "unknown"
    fi
}

OS=$(detect_os)

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  环境配置脚本 - uv & ffmpeg${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "检测到操作系统: ${YELLOW}$OS${NC}"
echo ""

# =============================================================================
# 1. 检查并安装 uv
# =============================================================================
echo -e "${BLUE}[1/2] 检查 uv 安装状态...${NC}"

if command_exists uv; then
    UV_VERSION=$(uv --version)
    echo -e "${GREEN}✓ uv 已安装${NC}: $UV_VERSION"
else
    echo -e "${YELLOW}✗ uv 未安装，开始安装...${NC}"

    # 使用官方安装脚本安装 uv
    curl -LsSf https://astral.sh/uv/install.sh | sh

    # 检查安装结果
    if command_exists uv; then
        echo -e "${GREEN}✓ uv 安装成功${NC}: $(uv --version)"
    else
        # 尝试添加到当前 shell 的 PATH
        if [ -f "$HOME/.cargo/bin/uv" ]; then
            export PATH="$HOME/.cargo/bin:$PATH"
            echo -e "${YELLOW}已将 uv 添加到当前会话的 PATH${NC}"
            echo -e "${GREEN}✓ uv 安装成功${NC}: $(uv --version)"
        else
            echo -e "${RED}✗ uv 安装可能失败，请手动检查${NC}"
            exit 1
        fi
    fi
fi

echo ""

# =============================================================================
# 2. 检查并安装 ffmpeg
# =============================================================================
echo -e "${BLUE}[2/2] 检查 ffmpeg 安装状态...${NC}"

if command_exists ffmpeg; then
    FFMPEG_VERSION=$(ffmpeg -version | head -n 1)
    echo -e "${GREEN}✓ ffmpeg 已安装${NC}: $FFMPEG_VERSION"
else
    echo -e "${YELLOW}✗ ffmpeg 未安装，开始安装...${NC}"

    case $OS in
        macos)
            if command_exists brew; then
                echo "使用 Homebrew 安装 ffmpeg..."
                brew install ffmpeg
            else
                echo -e "${RED}✗ 未检测到 Homebrew，请先安装 Homebrew:${NC}"
                echo "    /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
                exit 1
            fi
            ;;

        linux)
            if command_exists apt-get; then
                echo "使用 apt 安装 ffmpeg..."
                sudo apt-get update
                sudo apt-get install -y ffmpeg
            elif command_exists yum; then
                echo "使用 yum 安装 ffmpeg..."
                sudo yum install -y ffmpeg
            elif command_exists dnf; then
                echo "使用 dnf 安装 ffmpeg..."
                sudo dnf install -y ffmpeg
            elif command_exists pacman; then
                echo "使用 pacman 安装 ffmpeg..."
                sudo pacman -S ffmpeg --noconfirm
            else
                echo -e "${RED}✗ 无法自动安装 ffmpeg，请手动安装${NC}"
                exit 1
            fi
            ;;

        *)
            echo -e "${RED}✗ 不支持的操作系统，请手动安装 ffmpeg${NC}"
            exit 1
            ;;
    esac

    # 验证安装
    if command_exists ffmpeg; then
        echo -e "${GREEN}✓ ffmpeg 安装成功${NC}: $(ffmpeg -version | head -n 1)"
    else
        echo -e "${RED}✗ ffmpeg 安装失败${NC}"
        exit 1
    fi
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  环境配置完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "你现在可以直接运行项目中的 Python 脚本了:"
echo ""
echo "  uv run player.py              # 启动播放器"
echo "  uv run transcribe_whisper.py <音频文件>  # 语音转文字（不传参数使用默认文件）"
echo "  uv run split_audio.py <文件>  # 音频切割"
echo "  uv run remove_silence.py <文件> # 去除静音"
echo ""
