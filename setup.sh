#!/bin/bash

# 设置遇到错误立即停止，保证脚本的安全性
set -e

# 定义颜色输出
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # 恢复默认颜色

echo -e "${BLUE}=== 开始配置音频处理环境 ===${NC}\n"

# ---------------------------------------------------------
# 1. 创建并进入文件夹
# ---------------------------------------------------------
FOLDER_NAME="AudioProject"
echo -e "${YELLOW}步骤 1: 准备工作目录...${NC}"

if [ ! -d "$FOLDER_NAME" ]; then
    mkdir "$FOLDER_NAME"
    echo -e "${GREEN}✅ 已创建文件夹: $FOLDER_NAME${NC}"
else
    echo -e "${GREEN}✅ 文件夹 $FOLDER_NAME 已存在，直接使用。${NC}"
fi

# 进入文件夹
cd "$FOLDER_NAME"
echo -e "当前路径: $(pwd)\n"

# ---------------------------------------------------------
# 2. 安装 Python 包管理工具 uv
# ---------------------------------------------------------
echo -e "${YELLOW}步骤 2: 检查并安装 uv...${NC}"

# 检查 uv 是否已经安装
if command -v uv &> /dev/null; then
    echo -e "${GREEN}✅ uv 已经安装，跳过此步骤。${NC}\n"
else
    echo -e "正在安装 uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    echo -e "${GREEN}✅ uv 安装完成！${NC}\n"
fi

# ---------------------------------------------------------
# 3. 安装 Homebrew (macOS 必备工具)
# ---------------------------------------------------------
echo -e "${YELLOW}步骤 3: 检查并安装 Homebrew...${NC}"

if command -v brew &> /dev/null; then
    echo -e "${GREEN}✅ Homebrew 已经安装，跳过此步骤。${NC}\n"
else
    echo -e "正在安装 Homebrew (这可能需要几分钟时间，且需要输入电脑密码)..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    
    # 动态加载 Homebrew 环境变量 (防止首次安装后当前终端找不到 brew 命令)
    if [ -x "/opt/homebrew/bin/brew" ]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    elif [ -x "/usr/local/bin/brew" ]; then
        eval "$(/usr/local/bin/brew shellenv)"
    fi
    echo -e "${GREEN}✅ Homebrew 安装完成！${NC}\n"
fi

# ---------------------------------------------------------
# 4. 安装音频处理工具 FFmpeg
# ---------------------------------------------------------
echo -e "${YELLOW}步骤 4: 检查并安装 FFmpeg...${NC}"

if command -v ffmpeg &> /dev/null; then
    echo -e "${GREEN}✅ FFmpeg 已经安装，跳过此步骤。${NC}\n"
else
    echo -e "正在使用 Homebrew 安装 FFmpeg..."
    brew install ffmpeg
    echo -e "${GREEN}✅ FFmpeg 安装完成！${NC}\n"
fi

# ---------------------------------------------------------
# 结束提示
# ---------------------------------------------------------
echo -e "${BLUE}=======================================${NC}"
echo -e "${GREEN}🎉 恭喜！所有基础工具已准备完毕！${NC}"
echo -e "你可以输入 ${YELLOW}cd $FOLDER_NAME${NC} 来确保你在工作目录中，然后开始编写代码吧！"