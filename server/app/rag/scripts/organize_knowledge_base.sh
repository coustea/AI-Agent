#!/bin/bash
# 知识库整理脚本 - 将所有Markdown文档统一到一个目录
# 日期: 2026-07-03

set -e

SOURCE_DIR="/Users/apple/Code/software/server/app/rag/data/book"
TARGET_DIR="/Users/apple/Code/software/server/app/rag/data/knowledge_base"
LOG_FILE="/Users/apple/Code/software/server/app/rag/scripts/organize.log"

echo "========================================" | tee "$LOG_FILE"
echo "知识库整理脚本 - $(date)" | tee "$LOG_FILE"
echo "========================================" | tee "$LOG_FILE"
echo "目标: 将所有MD文件统一到 $TARGET_DIR" | tee "$LOG_FILE"
echo "" | tee "$LOG_FILE"

# 清空目标目录（首次运行）
if [ ! -d "$TARGET_DIR" ]; then
    mkdir -p "$TARGET_DIR"
fi

# 1. 处理原有教材 - 直接复制
echo "[1/7] 处理原有教材..." | tee -a "$LOG_FILE"
for md_file in "$SOURCE_DIR"/*.final.md; do
    if [ -f "$md_file" ]; then
        filename=$(basename "$md_file" .final.md)
        # 清理文件名中的噪音字符串
        clean_name=$(echo "$filename" | sed 's/(z-library\.sk, 1lib\.sk, z-lib\.sk)//g' | sed 's/\[数字版\]/（数字版）/g' | sed 's/  */ /g' | sed 's/\.\.//' | sed 's/^\s*//;s/\s*$//')
        target_file="$TARGET_DIR/${clean_name}.md"
        cp "$md_file" "$target_file"
        echo "  ✓ $clean_name" | tee -a "$LOG_FILE"
    fi
done

# 2. 处理 d2l - 动手学深度学习（按章节整理）
echo "[2/7] 处理《动手学深度学习》d2l..." | tee -a "$LOG_FILE"
mkdir -p "$TARGET_DIR/深度学习-d2l"
for chapter_dir in "$SOURCE_DIR/d2l"/chapter_*; do
    if [ -d "$chapter_dir" ]; then
        chapter_name=$(basename "$chapter_dir")
        # 提取章节中的所有MD文件
        find "$chapter_dir" -name "*.md" -type f | while read md_file; do
            relative_path=$(realpath --relative-to="$SOURCE_DIR/d2l" "$md_file" 2>/dev/null || echo "$chapter_name/$(basename $md_file)")
            target_subdir="$TARGET_DIR/深度学习-d2l/$chapter_name"
            mkdir -p "$target_subdir"
            cp "$md_file" "$target_subdir/"
        done
        echo "  ✓ $chapter_name" | tee -a "$LOG_FILE"
    fi
done

# 3. 处理 nndl - 神经网络与深度学习
echo "[3/7] 处理《神经网络与深度学习》nndl..." | tee -a "$LOG_FILE"
mkdir -p "$TARGET_DIR/神经网络与深度学习-nndl"
# 复制主要版本目录
for subdir in nndl-v2 nndl-ge nndl-practice llm-agent reading-path; do
    if [ -d "$SOURCE_DIR/nndl/$subdir" ]; then
        mkdir -p "$TARGET_DIR/神经网络与深度学习-nndl/$subdir"
        find "$SOURCE_DIR/nndl/$subdir" -name "*.md" -type f -exec cp {} "$TARGET_DIR/神经网络与深度学习-nndl/$subdir/" \;
        echo "  ✓ $subdir" | tee -a "$LOG_FILE"
    fi
done

# 4. 处理 pumpkin-book - 南瓜书
echo "[4/7] 处理《南瓜书》pumpkin-book..." | tee -a "$LOG_FILE"
mkdir -p "$TARGET_DIR/南瓜书-机器学习公式推导"
find "$SOURCE_DIR/pumpkin-book" -name "*.md" -type f | while read md_file; do
    cp "$md_file" "$TARGET_DIR/南瓜书-机器学习公式推导/"
done
md_count=$(find "$TARGET_DIR/南瓜书-机器学习公式推导" -name "*.md" | wc -l)
echo "  ✓ 复制 $md_count 个MD文件" | tee -a "$LOG_FILE"

# 5. 处理 ml-beginners - 微软ML教程
echo "[5/7] 处理《微软ML教程》ml-beginners..." | tee -a "$LOG_FILE"
mkdir -p "$TARGET_DIR/微软ML教程"
for lesson_dir in "$SOURCE_DIR/ml-beginners"/*; do
    if [ -d "$lesson_dir" ]; then
        lesson_name=$(basename "$lesson_dir")
        target_subdir="$TARGET_DIR/微软ML教程/$lesson_name"
        mkdir -p "$target_subdir"
        find "$lesson_dir" -name "*.md" -type f -exec cp {} "$target_subdir/" \;
        echo "  ✓ $lesson_name" | tee -a "$LOG_FILE"
    elif [ -f "$lesson_dir" ] && [[ "$lesson_dir" == *.md ]]; then
        cp "$lesson_dir" "$TARGET_DIR/微软ML教程/"
    fi
done

# 6. 处理 cs-notes - CS笔记
echo "[6/7] 处理《CS-Notes》..." | tee -a "$LOG_FILE"
mkdir -p "$TARGET_DIR/CS基础笔记"
for subdir in docs notes; do
    if [ -d "$SOURCE_DIR/cs-notes/$subdir" ]; then
        mkdir -p "$TARGET_DIR/CS基础笔记/$subdir"
        find "$SOURCE_DIR/cs-notes/$subdir" -name "*.md" -type f -exec cp {} "$TARGET_DIR/CS基础笔记/$subdir/" \;
        echo "  ✓ $subdir" | tee -a "$LOG_FILE"
    fi
done

# 7. 处理 cs-interview - 面试总结
echo "[7/7] 处理《计算机面试知识总结》..." | tee -a "$LOG_FILE"
mkdir -p "$TARGET_DIR/计算机面试知识总结"
find "$SOURCE_DIR/cs-interview" -name "*.md" -type f -exec cp {} "$TARGET_DIR/计算机面试知识总结/" \;
md_count=$(find "$TARGET_DIR/计算机面试知识总结" -name "*.md" | wc -l)
echo "  ✓ 复制 $md_count 个MD文件" | tee -a "$LOG_FILE"

echo "" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo "整理完成！统计信息：" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

# 统计各目录MD文件数量
echo "" | tee -a "$LOG_FILE"
echo "目录结构：" | tee -a "$LOG_FILE"
for dir in "$TARGET_DIR"/*; do
    if [ -d "$dir" ]; then
        name=$(basename "$dir")
        count=$(find "$dir" -name "*.md" | wc -l)
        size=$(du -sh "$dir" | cut -f1)
        echo "  $name: $count 个MD文件, $size" | tee -a "$LOG_FILE"
    fi
done

echo "" | tee -a "$LOG_FILE"
total_md=$(find "$TARGET_DIR" -name "*.md" | wc -l)
total_size=$(du -sh "$TARGET_DIR" | cut -f1)
echo "总计: $total_md 个MD文件, $total_size" | tee -a "$LOG_FILE"

echo "" | tee -a "$LOG_FILE"
echo "目录位置: $TARGET_DIR" | tee -a "$LOG_FILE"
