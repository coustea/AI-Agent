#!/bin/bash
# 重新整理知识库（保留核心内容）

KB_DIR="/Users/apple/Code/software/server/app/rag/data/knowledge_base"
SOURCE_DIR="/Users/apple/Code/software/server/app/rag/data/book"
LOG="/Users/apple/Code/software/server/app/rag/scripts/restore.log"

echo "========================================" | tee "$LOG"
echo "重新整理知识库 - $(date)" | tee "$LOG"
echo "========================================" | tee "$LOG"

# 清空目标目录重建
rm -rf "$KB_DIR"
mkdir -p "$KB_DIR"

# 1. 计算机经典教材（原有教材）
echo "[1/7] 复制经典教材..." | tee -a "$LOG"
mkdir -p "$KB_DIR/计算机经典教材"
for md in "$SOURCE_DIR"/*.final.md; do
    if [ -f "$md" ]; then
        name=$(basename "$md" .final.md | sed 's/(z-library.*)//g' | sed 's/\[数字版\]/（数字版）/g' | sed 's/  */ /g')
        cp "$md" "$KB_DIR/计算机经典教材/${name}.md"
    fi
done
count=$(find "$KB_DIR/计算机经典教材" -name "*.md" | wc -l)
echo "  ✓ $count 本教材" | tee -a "$LOG"

# 2. d2l深度学习（排除_origin和配置文件）
echo "[2/7] 复制d2l深度学习..." | tee -a "$LOG"
mkdir -p "$KB_DIR/深度学习-d2l"
for chapter in "$SOURCE_DIR/d2l"/chapter_*; do
    if [ -d "$chapter" ]; then
        chap_name=$(basename "$chapter")
        mkdir -p "$KB_DIR/深度学习-d2l/$chap_name"
        # 只复制主文件，排除_origin
        find "$chapter" -name "*.md" -type f | grep -v "_origin" | grep -v "README" | grep -v "INFO" | grep -v "STYLE" | grep -v "TERMINOLOGY" | while read f; do
            cp "$f" "$KB_DIR/深度学习-d2l/$chap_name/"
        done
    fi
done
count=$(find "$KB_DIR/深度学习-d2l" -name "*.md" | wc -l)
echo "  ✓ $count 个MD" | tee -a "$LOG"

# 3. nndl神经网络（排除配置）
echo "[3/7] 复制nndl..." | tee -a "$LOG"
mkdir -p "$KB_DIR/神经网络与深度学习-nndl"
for subdir in nndl-v2 nndl-ge nndl-practice llm-agent; do
    if [ -d "$SOURCE_DIR/nndl/$subdir" ]; then
        mkdir -p "$KB_DIR/神经网络与深度学习-nndl/$subdir"
        find "$SOURCE_DIR/nndl/$subdir" -name "*.md" -type f | while read f; do
            cp "$f" "$KB_DIR/神经网络与深度学习-nndl/$subdir/"
        done
    fi
done
count=$(find "$KB_DIR/神经网络与深度学习-nndl" -name "*.md" | wc -l)
echo "  ✓ $count 个MD" | tee -a "$LOG"

# 4. 南瓜书（只保留chapter文件）
echo "[4/7] 复制南瓜书..." | tee -a "$LOG"
mkdir -p "$KB_DIR/南瓜书-公式推导"
find "$SOURCE_DIR/pumpkin-book" -name "chapter*.md" -type f | while read f; do
    cp "$f" "$KB_DIR/南瓜书-公式推导/"
done
count=$(find "$KB_DIR/南瓜书-公式推导" -name "*.md" | wc -l)
echo "  ✓ $count 个章节" | tee -a "$LOG"

# 5. 微软ML（只保留lesson目录下的主文件）
echo "[5/7] 复制微软ML教程..." | tee -a "$LOG"
mkdir -p "$KB_DIR/微软ML教程"
for lesson in "$SOURCE_DIR/ml-beginners"/*-*/; do
    if [ -d "$lesson" ]; then
        lesson_name=$(basename "$lesson")
        mkdir -p "$KB_DIR/微软ML教程/$lesson_name"
        # 只保留英文和中文主文件
        find "$lesson" -name "*.md" | grep -E "(README|assignment)" | grep -v -E "(fr|es|it|pt|ko|ja|id)" | while read f; do
            cp "$f" "$KB_DIR/微软ML教程/$lesson_name/"
        done
    fi
done
count=$(find "$KB_DIR/微软ML教程" -name "*.md" | wc -l)
echo "  ✓ $count 个MD" | tee -a "$LOG"

# 6. CS笔记（保留docs和notes主内容）
echo "[6/7] 复制CS基础笔记..." | tee -a "$LOG"
mkdir -p "$KB_DIR/CS基础笔记"
for area in docs notes; do
    if [ -d "$SOURCE_DIR/cs-notes/$area" ]; then
        mkdir -p "$KB_DIR/CS基础笔记/$area"
        find "$SOURCE_DIR/cs-notes/$area" -name "*.md" -type f | grep -v "README" | grep -v "CHANGELOG" | grep -v "_404" | grep -v "_coverpage" | while read f; do
            cp "$f" "$KB_DIR/CS基础笔记/$area/"
        done
    fi
done
count=$(find "$KB_DIR/CS基础笔记" -name "*.md" | wc -l)
echo "  ✓ $count 个MD" | tee -a "$LOG"

# 7. 面试知识（保留主要内容）
echo "[7/7] 复制面试知识..." | tee -a "$LOG"
mkdir -p "$KB_DIR/计算机面试知识总结"
find "$SOURCE_DIR/cs-interview" -name "*.md" | grep -v "README" | grep -v "_navbar" | grep -v "en" | while read f; do
    cp "$f" "$KB_DIR/计算机面试知识总结/"
done
count=$(find "$KB_DIR/计算机面试知识总结" -name "*.md" | wc -l)
echo "  ✓ $count 个MD" | tee -a "$LOG"

echo "" | tee -a "$LOG"
echo "========================================" | tee -a "$LOG"
echo "最终统计" | tee -a "$LOG"
echo "========================================" | tee -a "$LOG"

for dir in "$KB_DIR"/*; do
    if [ -d "$dir" ]; then
        name=$(basename "$dir")
        count=$(find "$dir" -name "*.md" | wc -l)
        size=$(du -sh "$dir" | cut -f1)
        printf "  %-25s %4s 个MD (%s)\n" "$name" "$count" "$size" | tee -a "$LOG"
    fi
done

total=$(find "$KB_DIR" -name "*.md" | wc -l)
total_size=$(du -sh "$KB_DIR" | cut -f1)
echo "" | tee -a "$LOG"
echo "总计: $total 个MD文件, $total_size" | tee -a "$LOG"
