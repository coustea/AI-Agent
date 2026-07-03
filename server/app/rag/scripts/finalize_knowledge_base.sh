#!/bin/bash
# 知识库最终整理脚本 - 规范化所有文件名
# 日期: 2026-07-03

set -e

KB_DIR="/Users/apple/Code/software/server/app/rag/data/knowledge_base"
LOG_FILE="/Users/apple/Code/software/server/app/rag/scripts/finalize.log"

echo "========================================" | tee "$LOG_FILE"
echo "知识库最终整理 - $(date)" | tee "$LOG_FILE"
echo "========================================" | tee "$LOG_FILE"

# 1. 创建原有教材子目录
echo "[1/3] 创建原有教材目录..." | tee -a "$LOG_FILE"
mkdir -p "$KB_DIR/计算机经典教材"

# 2. 移动并重命名原有教材
echo "[2/3] 移动原有教材到统一目录..." | tee -a "$LOG_FILE"
cd "$KB_DIR"

for md_file in *.md; do
    if [ -f "$md_file" ]; then
        # 提取教材名（去掉作者、出版社等噪音）
        clean_name=$(echo "$md_file" | \
            sed 's/ (明日科技) //g' | \
            sed 's/ (埃里克·马瑟斯.*etc\.) //g' | \
            sed 's/ (Python) //g' | \
            sed 's/ (黄健宏) //g' | \
            sed 's/ (王金柱) //g' | \
            sed 's/ (王海鹏 译) //g' | \
            sed 's/ (Steve McConnell) //g' | \
            sed 's/ (马丁·戴维斯) //g' | \
            sed 's/ (张天德.*主编.*副主编) //g' | \
            sed 's/ (同济大学数学科学学院) //g' | \
            sed 's/ (Jeremy Tinley Silvia Botros) //g' | \
            sed 's/ (汤小丹.*汤子瀛) //g' | \
            sed 's/ (十二五普通高等教育本科国家级规划教材) //g' | \
            sed 's/ (谢希仁 \[谢希仁\]) //g' | \
            sed 's/ ( etc\.) //g' | \
            sed 's/ (谭志虎) //g' | \
            sed 's/ (唐朔飞) //g' | \
            sed 's/ (\[美\] 弗雷德里克·布鲁克斯) //g' | \
            sed 's/ (国家示范性软件学院系列教材) //g' | \
            sed 's/ (韩万江 姜立新) //g' | \
            sed 's/ (严蔚敏.*吴伟民) //g' | \
            sed 's/ (Yan Weimin.*etc\.) //g' | \
            sed 's/ (高一凡) //g' | \
            sed 's/ (张宇带你学系列丛书) //g' | \
            sed 's/ (张宇) //g' | \
            sed 's/ (Randal E-Bryant) //g' | \
            sed 's/ (Randal E\. Bryant) //g' | \
            sed 's/【数字版】//g' | \
            sed 's/\[数字版\]/（数字版）/g' | \
            sed 's/^\s*//;s/\s*$//g' | \
            sed 's/  */ /g' | \
            sed 's/\.\.\.md$/.md/g' | \
            sed 's/\.md$//g')
        
        # 特殊处理一些教材名
        if [[ "$clean_name" == *"计算机网络（第7版）"* ]]; then
            clean_name="计算机网络（第7版）-谢希仁"
        elif [[ "$clean_name" == *"计算机组成原理第3版"* ]]; then
            clean_name="计算机组成原理第3版-唐朔飞"
        elif [[ "$clean_name" == *"深入理解计算机系统"* ]]; then
            clean_name="深入理解计算机系统-CSAPP"
        fi
        
        target_file="$KB_DIR/计算机经典教材/${clean_name}.md"
        mv "$md_file" "$target_file"
        echo "  ✓ $clean_name" | tee -a "$LOG_FILE"
    fi
done

# 3. 生成最终统计
echo "[3/3] 生成最终统计..." | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo "最终知识库结构：" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

for dir in "$KB_DIR"/*; do
    if [ -d "$dir" ]; then
        name=$(basename "$dir")
        count=$(find "$dir" -name "*.md" | wc -l | tr -d ' ')
        size=$(du -sh "$dir" | cut -f1)
        printf "  %-30s %5s 个MD文件 (%s)\n" "$name" "$count" "$size" | tee -a "$LOG_FILE"
    fi
done

echo "" | tee -a "$LOG_FILE"
total_md=$(find "$KB_DIR" -name "*.md" | wc -l | tr -d ' ')
total_size=$(du -sh "$KB_DIR" | cut -f1)
echo "总计: $total_md 个MD文件, $total_size" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
echo "✅ 知识库整理完成！" | tee -a "$LOG_FILE"
echo "目录: $KB_DIR" | tee -a "$LOG_FILE"
