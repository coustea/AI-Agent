#!/bin/sh
# Tide 一键安装脚本 (支持 macOS 与 Linux)
# 用法: curl -fsSL https://raw.githubusercontent.com/coustea/AI-Agent/my-agent/install.sh | bash

set -e

REPO="coustea/AI-Agent"
DEFAULT_VERSION="v1.2.0"
VERSION="${TIDE_VERSION:-$DEFAULT_VERSION}"

# 颜色控制
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

echo "${BOLD}${CYAN}====================================================${NC}"
echo "${BOLD}${CYAN}   🌊 正在安装 Tide (本地终端通用 AI 个人助手)      ${NC}"
echo "${BOLD}${CYAN}====================================================${NC}"

# 1. 检测操作系统
OS="$(uname -s)"
case "$OS" in
    Darwin)
        TARGET_OS="darwin"
        ;;
    Linux)
        TARGET_OS="linux"
        ;;
    *)
        echo "${RED}错误: 暂不支持的操作系统: $OS (仅支持 macOS 与 Linux)${NC}"
        echo "Windows 用户请在 PowerShell 中使用 install.ps1 安装。"
        exit 1
        ;;
esac

# 2. 检测系统架构
ARCH="$(uname -m)"
case "$ARCH" in
    x86_64|amd64)
        TARGET_ARCH="amd64"
        ;;
    arm64|aarch64)
        TARGET_ARCH="arm64"
        ;;
    *)
        echo "${RED}错误: 暂不支持的 CPU 架构: $ARCH (仅支持 amd64 与 arm64)${NC}"
        exit 1
        ;;
esac

echo "=> 检测到系统平台: ${GREEN}${TARGET_OS}/${TARGET_ARCH}${NC}"
echo "=> 安装目标版本:   ${GREEN}${VERSION}${NC}"

# 3. 准备下载路径与临时工作目录
TAR_NAME="tide-${TARGET_OS}-${TARGET_ARCH}.tar.gz"
DOWNLOAD_URL="https://github.com/${REPO}/releases/download/${VERSION}/${TAR_NAME}"

TMP_DIR="$(mktemp -d 2>/dev/null || mktemp -d -t 'tide-install')"
trap 'rm -rf "$TMP_DIR"' EXIT

echo "=> 正在从 GitHub 官方 Release 下载发布包..."
echo "   URL: ${BLUE}${DOWNLOAD_URL}${NC}"

HTTP_CODE=""
if command -v curl >/dev/null 2>&1; then
    HTTP_CODE=$(curl -sSL -w "%{http_code}" -o "${TMP_DIR}/${TAR_NAME}" "${DOWNLOAD_URL}")
elif command -v wget >/dev/null 2>&1; then
    wget -q -O "${TMP_DIR}/${TAR_NAME}" "${DOWNLOAD_URL}" && HTTP_CODE="200" || HTTP_CODE="000"
else
    echo "${RED}错误: 未检测到 curl 或 wget 工具，请先安装。${NC}"
    exit 1
fi

# 4. 如果下载未找到（如该 Release 尚未发布或网络受限），尝试通过本地 Go 源码构建回退安装
if [ "$HTTP_CODE" != "200" ] && [ "$HTTP_CODE" != "302" ]; then
    echo "${CYAN}=> 预编译包直接下载响应 ($HTTP_CODE)，正在检测本地 Go 工具链...${NC}"
    if command -v go >/dev/null 2>&1; then
        echo "=> 检测到 Go 环境，正在通过 Go 工具链一键安装最新版..."
        go install "github.com/${REPO}/cmd/tide@latest" 2>/dev/null || {
            echo "=> 正在从 Git 源码编译构建..."
            git clone --depth 1 "https://github.com/${REPO}.git" "${TMP_DIR}/src"
            (cd "${TMP_DIR}/src" && make build && cp tide "${TMP_DIR}/tide")
        }
    else
        echo "${RED}错误: 无法下载发布包 (${DOWNLOAD_URL})${NC}"
        echo "请检查网络连接，或访问 https://github.com/${REPO}/releases 手动下载二进制。"
        exit 1
    fi
else
    # 解压下载包
    tar -xzf "${TMP_DIR}/${TAR_NAME}" -C "${TMP_DIR}"
fi

if [ ! -f "${TMP_DIR}/tide" ]; then
    echo "${RED}错误: 未能找到解压后的 tide 二进制文件。${NC}"
    exit 1
fi

chmod +x "${TMP_DIR}/tide"

# 5. 选择安装路径与写入
INSTALL_DIR="/usr/local/bin"
IS_UPGRADE=0

if [ -f "${INSTALL_DIR}/tide" ] || [ -f "$HOME/.local/bin/tide" ]; then
    IS_UPGRADE=1
    echo "=> 检测到已安装版本，正在平滑升级至 ${VERSION}..."
fi

if [ -w "$INSTALL_DIR" ]; then
    rm -f "${INSTALL_DIR}/tide" 2>/dev/null || true
    cp -f "${TMP_DIR}/tide" "${INSTALL_DIR}/tide"
    chmod 755 "${INSTALL_DIR}/tide"
else
    if command -v sudo >/dev/null 2>&1 && [ -t 0 ]; then
        echo "=> 需要管理员权限将 tide 安装到 ${INSTALL_DIR}，请输入密码:"
        sudo rm -f "${INSTALL_DIR}/tide" 2>/dev/null || true
        sudo cp -f "${TMP_DIR}/tide" "${INSTALL_DIR}/tide"
        sudo chmod 755 "${INSTALL_DIR}/tide"
    else
        INSTALL_DIR="$HOME/.local/bin"
        mkdir -p "$INSTALL_DIR"
        rm -f "${INSTALL_DIR}/tide" 2>/dev/null || true
        cp -f "${TMP_DIR}/tide" "${INSTALL_DIR}/tide"
        chmod 755 "${INSTALL_DIR}/tide"
    fi
fi

echo ""
if [ "$IS_UPGRADE" = "1" ]; then
    echo "${BOLD}${GREEN}✔ Tide 平滑更新成功！${NC}"
else
    echo "${BOLD}${GREEN}✔ Tide 安装成功！${NC}"
fi
echo "=> 安装位置: ${BOLD}${INSTALL_DIR}/tide${NC}"

# 6. PATH 检测与提示
case ":$PATH:" in
    *":${INSTALL_DIR}:"*)
        ;;
    *)
        echo ""
        echo "${RED}注意: ${INSTALL_DIR} 似乎不在您的 PATH 环境变量中。${NC}"
        echo "请将以下内容加入您的 Shell 配置文件 (~/.zshrc 或 ~/.bashrc):"
        echo "  ${CYAN}export PATH=\"${INSTALL_DIR}:\$PATH\"${NC}"
        ;;
esac

echo ""
echo "=> 版本验证:"
"${INSTALL_DIR}/tide" --version || true

echo ""
echo "${BOLD}${CYAN}快速开始:${NC}"
echo "  1. 运行 ${BOLD}tide${NC} 启动交互式终端界面"
echo "  2. 首次启动输入 ${BOLD}/model${NC} 可配置 API Key 或切换模型平台"
echo "  3. 输入 ${BOLD}/think${NC} 或按 ${BOLD}Ctrl+T${NC} 可随时查看全屏深度思考看板"
echo ""
