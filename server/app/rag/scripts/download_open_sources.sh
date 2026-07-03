#!/bin/bash
# 计算机本科专业知识库下载脚本
# 用途: 下载开源Markdown格式的计算机教材
# 日期: 2026-07-03

set -e

BOOK_DIR="/Users/apple/Code/software/server/app/rag/data/book"
LOG_FILE="/Users/apple/Code/software/server/app/rag/scripts/download.log"

echo "========================================" | tee -a "$LOG_FILE"
echo "知识库下载脚本 - $(date)" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

cd "$BOOK_DIR"

# 1. 动手学深度学习 (李沐) - 官方开源Markdown
if [ ! -d "d2l" ]; then
    echo "[1/6] 下载《动手学深度学习》d2l-zh..." | tee -a "$LOG_FILE"
    git clone --depth=1 https://github.com/d2l-ai/d2l-zh.git d2l
    echo "✓ 完成" | tee -a "$LOG_FILE"
else
    echo "[1/6] 《动手学深度学习》已存在，跳过" | tee -a "$LOG_FILE"
fi

# 2. 神经网络与深度学习 (邱锡鹏) - 官方开源Markdown
if [ ! -d "nndl" ]; then
    echo "[2/6] 下载《神经网络与深度学习》nndl..." | tee -a "$LOG_FILE"
    git clone --depth=1 https://github.com/nndl/nndl.github.io.git nndl
    echo "✓ 完成" | tee -a "$LOG_FILE"
else
    echo "[2/6] 《神经网络与深度学习》已存在，跳过" | tee -a "$LOG_FILE"
fi

# 3. 南瓜书 (西瓜书公式推导) - Datawhale开源
if [ ! -d "pumpkin-book" ]; then
    echo "[3/6] 下载《南瓜书》(西瓜书配套)..." | tee -a "$LOG_FILE"
    git clone --depth=1 https://github.com/DatawhaleChina/pumpkin-book.git pumpkin-book
    echo "✓ 完成" | tee -a "$LOG_FILE"
else
    echo "[3/6] 《南瓜书》已存在，跳过" | tee -a "$LOG_FILE"
fi

# 4. 微软机器学习入门教程 - 官方开源
if [ ! -d "ml-beginners" ]; then
    echo "[4/6] 下载《ML-For-Beginners》微软教程..." | tee -a "$LOG_FILE"
    git clone --depth=1 https://github.com/microsoft/ML-For-Beginners.git ml-beginners
    echo "✓ 完成" | tee -a "$LOG_FILE"
else
    echo "[4/6] 《ML-For-Beginners》已存在，跳过" | tee -a "$LOG_FILE"
fi

# 5. 计算机面试知识总结 - huihut
if [ ! -d "cs-interview" ]; then
    echo "[5/6] 下载《计算机面试知识总结》..." | tee -a "$LOG_FILE"
    git clone --depth=1 https://github.com/huihut/interview.git cs-interview
    echo "✓ 完成" | tee -a "$LOG_FILE"
else
    echo "[5/6] 《计算机面试知识总结》已存在，跳过" | tee -a "$LOG_FILE"
fi

# 6. CS-Notes - CyC2018
if [ ! -d "cs-notes" ]; then
    echo "[6/6] 下载《CS-Notes》..." | tee -a "$LOG_FILE"
    git clone --depth=1 https://github.com/CyC2018/CS-Notes.git cs-notes
    echo "✓ 完成" | tee -a "$LOG_FILE"
else
    echo "[6/6] 《CS-Notes》已存在，跳过" | tee -a "$LOG_FILE"
fi

echo "" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo "下载完成！检查目录大小：" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
du -sh */ 2>/dev/null | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
echo "总计：" | tee -a "$LOG_FILE"
du -sh "$BOOK_DIR" | tee -a "$LOG_FILE"
