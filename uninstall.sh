#!/bin/bash

set -e

# 定义颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}=== 开始卸载音频处理环境 ===${NC}\n"
echo -e "${YELLOW}⚠️  此操作将卸载通过 setup.sh 安装的工具，请谨慎操作。${NC}\n"

# 通用确认函数
confirm() {
    read -r -p "$1 [y/N] " _ans
    [[ "$_ans" =~ ^[Yy]$ ]]
}

# ---------------------------------------------------------
# 1. 卸载 FFmpeg
# ---------------------------------------------------------
echo -e "${YELLOW}步骤 1: 卸载 FFmpeg...${NC}"

if command -v ffmpeg &> /dev/null; then
    if confirm "确认使用 Homebrew 卸载 FFmpeg？"; then
        brew uninstall ffmpeg
        echo -e "${GREEN}✅ FFmpeg 已卸载。${NC}\n"
    else
        echo -e "跳过卸载 FFmpeg。\n"
    fi
else
    echo -e "FFmpeg 未安装，跳过。\n"
fi

# ---------------------------------------------------------
# 2. 卸载 Homebrew
# ---------------------------------------------------------
echo -e "${YELLOW}步骤 2: 卸载 Homebrew...${NC}"

if command -v brew &> /dev/null; then
    echo -e "${RED}⚠️  注意：卸载 Homebrew 会同时移除所有通过它安装的软件包。${NC}"
    if confirm "确认卸载 Homebrew？"; then
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/uninstall.sh)"
        echo -e "${GREEN}✅ Homebrew 已卸载。${NC}\n"
    else
        echo -e "跳过卸载 Homebrew。\n"
    fi
else
    echo -e "Homebrew 未安装，跳过。\n"
fi

# ---------------------------------------------------------
# 3. 卸载 uv
# ---------------------------------------------------------
echo -e "${YELLOW}步骤 3: 卸载 uv...${NC}"

UV_BIN="$HOME/.local/bin/uv"
UV_DIR="$HOME/.local/share/uv"
UVX_BIN="$HOME/.local/bin/uvx"

if command -v uv &> /dev/null || [ -f "$UV_BIN" ]; then
    if confirm "确认卸载 uv？"; then
        rm -f "$UV_BIN" "$UVX_BIN"
        rm -rf "$UV_DIR"
        echo -e "${GREEN}✅ uv 已卸载。${NC}\n"
    else
        echo -e "跳过卸载 uv。\n"
    fi
else
    echo -e "uv 未安装，跳过。\n"
fi

# ---------------------------------------------------------
# 结束提示
# ---------------------------------------------------------
echo -e "${BLUE}=======================================${NC}"
echo -e "${GREEN}🎉 卸载流程完成。${NC}"
