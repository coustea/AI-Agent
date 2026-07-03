#!/bin/bash
# 清理非权威教材，只保留计算机专业核心理论教材

KB_DIR="/Users/apple/Code/software/server/app/rag/data/knowledge_base"
LOG="/Users/apple/Code/software/server/app/rag/scripts/clean_authoritative.log"

echo "========================================" | tee "$LOG"
echo "清理非权威教材 - $(date)" | tee "$LOG"
echo "========================================" | tee "$LOG"

cd "$KB_DIR/计算机经典教材"

# 统计初始状态
initial=$(ls -1 *.md 2>/dev/null | wc -l)
echo "初始教材数: $initial" | tee -a "$LOG"
echo "" | tee -a "$LOG"

# 删除实践类/非核心课程教材
echo "[1/2] 删除非权威教材..." | tee -a "$LOG"

removed=0

# Java实践类
if ls Java*.md 1>/dev/null 2>&1; then
    rm -f Java*.md
    echo "  ✓ 删除 Java相关教材" | tee -a "$LOG"
    removed=$((removed + 1))
fi

# Python实践类
if ls Python*.md 1>/dev/null 2>&1; then
    rm -f Python*.md
    echo "  ✓ 删除 Python相关教材" | tee -a "$LOG"
    removed=$((removed + 1))
fi

# Redis非核心
if ls Redis*.md 1>/dev/null 2>&1; then
    rm -f Redis*.md
    echo "  ✓ 删除 Redis相关教材" | tee -a "$LOG"
    removed=$((removed + 1))
fi

# Vue实践类
if ls Vue*.md 1>/dev/null 2>&1; then
    rm -f Vue*.md
    echo "  ✓ 删除 Vue相关教材" | tee -a "$LOG"
    removed=$((removed + 1))
fi

# 代码大全非教材
if ls 代码大全*.md 1>/dev/null 2>&1; then
    rm -f 代码大全*.md
    echo "  ✓ 删除 代码大全" | tee -a "$LOG"
    removed=$((removed + 1))
fi

# 人月神话非教材
if ls 人月神话*.md 1>/dev/null 2>&1; then
    rm -f 人月神话*.md
    echo "  ✓ 删除 人月神话" | tee -a "$LOG"
    removed=$((removed + 1))
fi

# 高性能MySQL非核心
if ls 高性能MySQL*.md 1>/dev/null 2>&1; then
    rm -f 高性能MySQL*.md
    echo "  ✓ 删除 高性能MySQL" | tee -a "$LOG"
    removed=$((removed + 1))
fi

# 软件工程案例教程（应替换为软件工程导论）
if ls 软件工程案例教程*.md 1>/dev/null 2>&1; then
    rm -f 软件工程案例教程*.md
    echo "  ✓ 删除 软件工程案例教程（非权威）" | tee -a "$LOG"
    removed=$((removed + 1))
fi

# 计算机系统解密（非标准教材）
if ls 计算机系统解密*.md 1>/dev/null 2>&1; then
    rm -f 计算机系统解密*.md
    echo "  ✓ 删除 计算机系统解密（非标准）" | tee -a "$LOG"
    removed=$((removed + 1))
fi

# 第一推动丛书（非计算机核心课程）
if ls 第一推动丛书*.md 1>/dev/null 2>&1; then
    rm -f 第一推动丛书*.md
    echo "  ✓ 删除 第一推动丛书（非核心课程）" | tee -a "$LOG"
    removed=$((removed + 1))
fi

echo "" | tee -a "$LOG"
echo "[2/2] 保留权威教材..." | tee -a "$LOG"

# 列出保留的教材
final=$(ls -1 *.md 2>/dev/null | wc -l)
echo "" | tee -a "$LOG"
echo "保留的权威教材：" | tee -a "$LOG"
ls -1 *.md 2>/dev/null | while read f; do
    name=$(basename "$f" .md)
    echo "  ✅ $name" | tee -a "$LOG"
done

echo "" | tee -a "$LOG"
echo "========================================" | tee -a "$LOG"
echo "清理完成" | tee -a "$LOG"
echo "========================================" | tee -a "$LOG"
echo "删除: $removed 本非权威教材" | tee -a "$LOG"
echo "保留: $final 本权威教材" | tee -a "$LOG"
