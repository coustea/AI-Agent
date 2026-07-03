#!/bin/bash
# 知识库清理脚本 - 删除无关MD文件
# 日期: 2026-07-03

KB_DIR="/Users/apple/Code/software/server/app/rag/data/knowledge_base"
LOG_FILE="/Users/apple/Code/software/server/app/rag/scripts/cleanup.log"

echo "========================================" | tee "$LOG_FILE"
echo "知识库清理脚本 - $(date)" | tee "$LOG_FILE"
echo "========================================" | tee "$LOG_FILE"

# 记录初始状态
initial_count=$(find "$KB_DIR" -name "*.md" | wc -l)
initial_size=$(du -sh "$KB_DIR" | cut -f1)
echo "初始状态: $initial_count 个MD文件, $initial_size" | tee "$LOG_FILE"
echo "" | tee "$LOG_FILE"

# 1. 删除 _origin 后缀文件（d2l的重复文件）
echo "[1/5] 删除_origin重复文件..." | tee -a "$LOG_FILE"
origin_count=$(find "$KB_DIR" -name "*_origin.md" | wc -l)
find "$KB_DIR" -name "*_origin.md" -type f -delete
echo "  ✓ 删除 $origin_count 个_origin文件" | tee -a "$LOG_FILE"

# 2. 删除多语言翻译文件（保留中文和英文）
echo "[2/5] 删除非中英文翻译文件..." | tee -a "$LOG_FILE"
trans_count=$(find "$KB_DIR" -name "*.md" | grep -E "(fr|es|it|pt|ko|ja|id|zh-tw)" | wc -l)
find "$KB_DIR" -name "*.md" | grep -E "(fr|es|it|pt|ko|ja|id|zh-tw)" | xargs rm -f
echo "  ✓ 删除 $trans_count 个翻译文件" | tee -a "$LOG_FILE"

# 3. 删除配置/导航文件
echo "[3/5] 删除配置导航文件..." | tee -a "$LOG_FILE"
config_count=$(find "$KB_DIR" -name "_*.md" | wc -l)
find "$KB_DIR" -name "_*.md" -type f -delete
echo "  ✓ 删除 $config_count 个配置文件" | tee -a "$LOG_FILE"

# 4. 删除项目管理文件
echo "[4/5] 删除项目管理文件..." | tee -a "$LOG_FILE"
project_files="CODE_OF_CONDUCT.md CONTRIBUTING.md SECURITY.md SUPPORT.md TROUBLESHOOTING.md LICENSE.md for-teachers.md AGENTS.md"
deleted_project=0
for file in $project_files; do
    count=$(find "$KB_DIR" -name "$file" | wc -l)
    if [ $count > 0 ]; then
        find "$KB_DIR" -name "$file" -type f -delete
        deleted_project=$((deleted_project + count))
    fi
done
echo "  ✓ 删除 $deleted_project 个项目管理文件" | tee -a "$LOG_FILE"

# 5. 删除冗余README（保留知识库根目录README）
echo "[5/5] 删除冗余README..." | tee -a "$LOG_FILE"
readme_count=$(find "$KB_DIR" -name "README.md" | wc -l)
# 保留根目录README
find "$KB_DIR" -name "README.md" -type f | grep -v "^$KB_DIR/README.md$" | xargs rm -f
kept_readme=1
deleted_readme=$((readme_count - kept_readme))
echo "  ✓ 删除 $deleted_readme 个README（保留根目录）" | tee -a "$LOG_FILE"

echo "" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo "清理完成！" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

# 统计最终状态
final_count=$(find "$KB_DIR" -name "*.md" | wc -l)
final_size=$(du -sh "$KB_DIR" | cut -f1)
deleted_total=$((initial_count - final_count))

echo "" | tee -a "$LOG_FILE"
echo "清理结果：" | tee -a "$LOG_FILE"
echo "  删除文件数: $deleted_total" | tee -a "$LOG_FILE"
echo "  原始文件数: $initial_count" | tee -a "$LOG_FILE"
echo "  最终文件数: $final_count" | tee -a "$LOG_FILE"
echo "  原始大小: $initial_size" | tee -a "$LOG_FILE"
echo "  最终大小: $final_size" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

echo "各目录统计：" | tee -a "$LOG_FILE"
for dir in "$KB_DIR"/*/; do
    if [ -d "$dir" ]; then
        name=$(basename "$dir")
        count=$(find "$dir" -name "*.md" | wc -l)
        size=$(du -sh "$dir" | cut -f1)
        echo "  $name: $count 个MD文件 ($size)" | tee -a "$LOG_FILE"
    fi
done

echo "" | tee -a "$LOG_FILE"
echo "✅ 清理完成！知识库已精简。" | tee -a "$LOG_FILE"
