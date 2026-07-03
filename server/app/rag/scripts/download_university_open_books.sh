#!/bin/bash
# 下载高校计算机开源教材（免费高质量资源）
# 日期: 2026-07-03

KB_DIR="/Users/apple/Code/software/server/app/rag/data/knowledge_base"
TEMP_DIR="/Users/apple/Code/software/server/app/rag/data/temp_university"
LOG="/Users/apple/Code/software/server/app/rag/scripts/download_university.log"

echo "========================================" | tee "$LOG"
echo "下载高校计算机开源教材 - $(date)" | tee "$LOG"
echo "========================================" | tee "$LOG"

mkdir -p "$TEMP_DIR"
mkdir -p "$KB_DIR/MIT开源教材"
mkdir -p "$KB_DIR/算法理论"
mkdir -p "$KB_DIR/计算机系统"

# 1. MIT Mathematics for Computer Science（免费）
echo "[1/5] 下载MIT数学教材..." | tee -a "$LOG"
if [ ! -d "$TEMP_DIR/mitmath" ]; then
    git clone --depth=1 https://github.com/mitmath/6042 "$TEMP_DIR/mitmath" 2>&1 | tee -a "$LOG"
    # 复制Markdown文件到知识库
    mkdir -p "$KB_DIR/MIT开源教材/Mathematics-for-CS"
    find "$TEMP_DIR/mitmath" -name "*.md" -type f | while read f; do
        cp "$f" "$KB_DIR/MIT开源教材/Mathematics-for-CS/"
    done
    count=$(find "$KB_DIR/MIT开源教材/Mathematics-for-CS" -name "*.md" | wc -l)
    echo "  ✓ MIT数学for CS: $count 个MD" | tee -a "$LOG"
else
    echo "  ⊙ 已存在，跳过" | tee -a "$LOG"
fi

# 2. Algorithmica算法导论笔记（免费）
echo "[2/5] 下载算法导论笔记..." | tee -a "$LOG"
if [ ! -d "$TEMP_DIR/algorithmica" ]; then
    git clone --depth=1 https://github.com/algorithmica-git/lectures "$TEMP_DIR/algorithmica" 2>&1 | tee -a "$LOG"
    mkdir -p "$KB_DIR/算法理论/算法导论笔记"
    find "$TEMP_DIR/algorithmica" -name "*.md" -type f | while read f; do
        cp "$f" "$KB_DIR/算法理论/算法导论笔记/"
    done
    count=$(find "$KB_DIR/算法理论/算法导论笔记" -name "*.md" | wc -l)
    echo "  ✓ 算法导论笔记: $count 个MD" | tee -a "$LOG"
else
    echo "  ⊙ 已存在，跳过" | tee -a "$LOG"
fi

# 3. CSAPP中文笔记（免费）
echo "[3/5] 下载CSAPP中文笔记..." | tee -a "$LOG"
if [ ! -d "$TEMP_DIR/csapp-cn" ]; then
    git clone --depth=1 https://github.com/dongweiming/CSAPP-3e "$TEMP_DIR/csapp-cn" 2>&1 | tee -a "$LOG"
    mkdir -p "$KB_DIR/计算机系统/CSAPP中文笔记"
    find "$TEMP_DIR/csapp-cn" -name "*.md" -type f | while read f; do
        cp "$f" "$KB_DIR/计算机系统/CSAPP中文笔记/"
    done
    count=$(find "$KB_DIR/计算机系统/CSAPP中文笔记" -name "*.md" | wc -l)
    echo "  ✓ CSAPP中文笔记: $count 个MD" | tee -a "$LOG"
else
    echo "  ⊙ 已存在，跳过" | tee -a "$LOG"
fi

# 4. Operating Systems: Three Easy Pieces（OSTEP免费）
echo "[4/5] 下载OSTEP补充材料..." | tee -a "$LOG"
if [ ! -d "$TEMP_DIR/ostep-projects" ]; then
    git clone --depth=1 https://github.com/remzi-arpaci/ostep-projects "$TEMP_DIR/ostep-projects" 2>&1 | tee -a "$LOG"
    mkdir -p "$KB_DIR/操作系统补充"
    find "$TEMP_DIR/ostep-projects" -name "*.md" -type f | while read f; do
        cp "$f" "$KB_DIR/操作系统补充/"
    done
    count=$(find "$KB_DIR/操作系统补充" -name "*.md" | wc -l)
    echo "  ✓ OSTEP补充材料: $count 个MD" | tee -a "$LOG"
else
    echo "  ⊙ 已存在，跳过" | tee -a "$LOG"
fi

# 5. 编译原理入门（免费）
echo "[5/5] 下载编译原理入门..." | tee -a "$LOG"
if [ ! -d "$TEMP_DIR/compiler-book" ]; then
    git clone --depth=1 https://github.com/q parish/compiler-book "$TEMP_DIR/compiler-book" 2>&1 | tee -a "$LOG" || echo "  ⚠ GitHub仓库不存在，跳过" | tee -a "$LOG"
    if [ -d "$TEMP_DIR/compiler-book" ]; then
        mkdir -p "$KB_DIR/编译原理入门"
        find "$TEMP_DIR/compiler-book" -name "*.md" -type f | while read f; do
            cp "$f" "$KB_DIR/编译原理入门/"
        done
        count=$(find "$KB_DIR/编译原理入门" -name "*.md" | wc -l)
        echo "  ✓ 编译原理入门: $count 个MD" | tee -a "$LOG"
    fi
else
    echo "  ⊙ 已存在，跳过" | tee -a "$LOG"
fi

echo "" | tee -a "$LOG"
echo "========================================" | tee -a "$LOG"
echo "下载完成！最终统计：" | tee -a "$LOG"
echo "========================================" | tee -a "$LOG"

for dir in "$KB_DIR"/*/; do
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

echo "" | tee -a "$LOG"
echo "✅ 高校开源教材下载完成！" | tee -a "$LOG"
