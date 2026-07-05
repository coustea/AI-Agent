# 计算机本科专业知识库拓展方案

> 生成日期: 2026-07-03
> 目标: 构建覆盖计算机本科核心课程 + AI/机器学习领域的完整知识库

---

## 一、计算机本科专业课程体系概览

根据教育部《高等学校计算机科学与技术专业规范》，计算机本科核心课程分为：

### 1. 专业基础课（必修）

| 课程名称 | 当前覆盖 | 建议补充教材 |
|----------|---------|-------------|
| **计算机导论** | ❌ | 《计算机科学导论》- Behrouz A. Forouzan |
| **程序设计基础** | ✅ Java/Python | 《C程序设计语言》- K&R |
| **数据结构** | ✅ 严蔚敏 | 《数据结构与算法分析》- Mark Allen Weiss |
| **计算机组成原理** | ✅ 谭志虎/唐朔飞 | 《计算机组成与设计》- Patterson & Hennessy |
| **操作系统** | ✅ 汤小丹/OSTEP | 《现代操作系统》- Tanenbaum |
| **计算机网络** | ✅ 谢希仁 | 《计算机网络》- Tanenbaum |
| **数据库系统** | ✅ 概念+MySQL | 《数据库系统实现》- Hector Garcia-Molina |
| **软件工程** | ✅ 案例教程 | 《软件工程：实践者的研究方法》- Pressman |

### 2. 专业核心课（必修/选修）

| 课程名称 | 当前覆盖 | 建议补充教材 |
|----------|---------|-------------|
| **算法设计与分析** | ✅ 算法第4版 | 《算法导论》- CLRS |
| **编译原理** | ❌ | 《编译原理》- Alfred V. Aho (龙书) |
| **计算机图形学** | ❌ | 《计算机图形学》- Foley |
| **计算机安全/网络安全** | ❌ | 《网络安全基础》- William Stallings |
| **人工智能** | ❌ | 《人工智能：一种现代方法》- Russell & Norvig |
| **离散数学** | ❌ | 《离散数学及其应用》- Kenneth Rosen |
| **数字逻辑** | ❌ | 《数字逻辑电路》- 王毓银 |

### 3. AI/机器学习方向（新增）

| 课程名称 | 优先级 | 推荐教材 |
|----------|--------|----------|
| **机器学习** | ⭐⭐⭐⭐⭐ | 《机器学习》- 周志华 (西瓜书) |
| **深度学习** | ⭐⭐⭐⭐⭐ | 《动手学深度学习》- 李沐 (Dive into Deep Learning) |
| **自然语言处理** | ⭐⭐⭐⭐ | 《自然语言处理》- Daniel Jurafsky |
| **计算机视觉** | ⭐⭐⭐⭐ | 《计算机视觉：算法与应用》- Richard Szeliski |
| **强化学习** | ⭐⭐⭐ | 《强化学习》- Sutton & Barto |
| **模式识别** | ⭐⭐⭐ | 《模式识别》- 边肇祺 |
| **神经网络与深度学习** | ⭐⭐⭐ | 《神经网络与深度学习》- 邱锡鹏 |

### 4. 前沿技术方向（新增）

| 课程名称 | 优先级 | 推荐教材 |
|----------|--------|----------|
| **分布式系统** | ⭐⭐⭐⭐ | 《分布式系统原理与范型》- Tanenbaum |
| **云计算与容器技术** | ⭐⭐⭐ | Kubernetes官方文档、Docker指南 |
| **大数据处理** | ⭐⭐⭐ | 《大数据技术原理与应用》- 林子雨 |
| **区块链技术** | ⭐⭐ | 《区块链技术指南》- 邹均 |
| **物联网技术** | ⭐⭐ | 《物联网技术导论》- 刘云浩 |

---

## 二、知识库拓展优先级规划

### Phase 1: AI核心教材 (5本，最高优先级) ⭐⭐⭐⭐⭐

| 教材名称 | 作者 | 格式来源 | 获取方式 |
|----------|------|----------|----------|
| 《动手学深度学习》 | 李沐等 | Markdown (官方开源) | d2l.ai 官方GitHub |
| 《神经网络与深度学习》 | 邱锡鹏 | Markdown (官方开源) | nndl.github.io |
| 《机器学习》西瓜书 | 周志华 | PDF需转换 | 官方购买/GitHub转换版 |
| 《统计学习方法》 | 李航 | PDF需转换 | 官方购买/GitHub |
| 《深度学习》花书 | Goodfellow | PDF需转换 | GitHub翻译版 |

### Phase 2: 计算机理论补充 (5本) ⭐⭐⭐⭐

| 教材名称 | 作者 | 说明 |
|----------|------|------|
| 《算法导论》CLRS | Cormen等 | 算法圣经，覆盖更全面 |
| 《编译原理》龙书 | Aho等 | 编译器经典 |
| 《离散数学及其应用》 | Rosen | 数学基础 |
| 《计算机科学导论》 | Forouzan | 入门必读 |
| 《计算机安全基础》 | Stallings | 网络安全 |

### Phase 3: 前沿技术 (5-10本) ⭐⭐⭐

| 教材名称 | 来源 | 说明 |
|----------|------|------|
| 《分布式系统原理》 | Tanenbaum | 分布式经典 |
| Kubernetes官方文档 | k8s.io | 容器编排 |
| Docker官方指南 | docker.com | 容器技术 |
| 《大数据技术原理》 | 林子雨 | 大数据入门 |
| 《自然语言处理》 | Jurafsky | NLP权威 |

---

## 三、开源Markdown资源清单

### GitHub优质开源项目（可直接使用）

#### 1. AI/机器学习（官方开源Markdown）

```
📦 d2l-ai/d2l-zh
   名称: 动手学深度学习（中文版）
   作者: 李沐、Alex Smola等
   格式: Markdown (官方)
   来源: https://github.com/d2l-ai/d2l-zh
   特点: 交互式学习，代码+理论，Jupyter Notebook

📦 nndl/nndl.github.io
   名称: 神经网络与深度学习
   作者: 邱锡鹏
   格式: Markdown (官方)
   来源: https://github.com/nndl/nndl.github.io
   特点: 开源免费，理论扎实

📦 microsoft/ML-For-Beginners
   名称: 机器学习入门教程
   作者: Microsoft
   格式: Markdown
   来源: https://github.com/microsoft/ML-For-Beginners
   特点: 24课时，实践导向

📦 apachecn/sklearn-doc-zh
   名称: Scikit-learn中文文档
   作者: ApacheCN
   格式: Markdown
   来源: https://github.com/apachecn/sklearn-doc-zh
   特点: 机器学习库文档

📦 DatawhaleChina/pumpkin-book
   名称: 南瓜书（西瓜书公式推导）
   作者: Datawhale
   格式: Markdown
   来源: https://github.com/DatawhaleChina/pumpkin-book
   特点: 西瓜书配套，公式推导
```

#### 2. 计算机基础（开源笔记/总结）

```
📦 huihut/interview
   名称: 计算机面试知识总结
   内容: C/C++、操作系统、网络、数据库
   格式: Markdown
   来源: https://github.com/huihut/interview

📦 CyC2018/CS-Notes
   名称: 计算机基础知识笔记
   内容: 算法、网络、操作系统、数据库
   格式: Markdown
   来源: https://github.com/CyC2018/CS-Notes

📦 js-interview-question
   名称: 前端面试题库
   格式: Markdown
   来源: GitHub

📦 apachecn/InterviewBooks
   名称: 计算机面试书籍合集
   内容: 算法、Java、Python等
   格式: Markdown
   来源: https://github.com/apachecn/InterviewBooks
```

#### 3. 免费书籍索引

```
📦 justjavac/free-programming-books-zh_CN
   名称: 免费中文编程书籍索引
   来源: https://github.com/justjavac/free-programming-books-zh_CN

📦 EbookFoundation/free-programming-books
   名称: 全球免费编程书籍索引
   来源: https://github.com/EbookFoundation/free-programming-books

📦 iamseancheney/python_books
   名称: Python编程书籍合集
   来源: https://github.com/iamseancheney/python_books
```

---

## 四、获取与处理流程

### Step 1: 下载开源Markdown教材

```bash
# 进入知识库目录
cd /Users/apple/Code/software/server/app/rag/data/book

# 1. 动手学深度学习 (官方开源，约50MB)
git clone --depth=1 https://github.com/d2l-ai/d2l-zh.git d2l

# 2. 神经网络与深度学习 (官方开源，约10MB)
git clone --depth=1 https://github.com/nndl/nndl.github.io.git nndl

# 3. 微软ML教程 (约30MB)
git clone --depth=1 https://github.com/microsoft/ML-For-Beginners.git ml-beginners

# 4. 计算机面试知识总结 (约5MB)
git clone --depth=1 https://github.com/huihut/interview.git cs-interview

# 5. CS-Notes (约10MB)
git clone --depth=1 https://github.com/CyC2018/CS-Notes.git cs-notes

# 6. 南瓜书（西瓜书配套）
git clone --depth=1 https://github.com/DatawhaleChina/pumpkin-book.git pumpkin-book
```

### Step 2: PDF转Markdown工具

对于PDF格式教材，推荐以下工具：

#### 方案A: Marker (推荐)

```bash
# 安装
pip install marker-pdf

# 单文件转换
marker_single input.pdf output_dir --output_format markdown

# 批量转换
marker path/to/pdfs output_dir --workers 4
```

#### 方案B: Mathpix (数学公式最佳)

- 官网: https://mathpix.com
- 特点: OCR识别数学公式，效果最佳
- 费用: 免费额度有限，付费较贵

#### 方案C: pdf2md

```bash
pip install pdf2md

pdf2md input.pdf output.md
```

#### 方案D: Calibre

```bash
# 安装
brew install calibre

# 转换
ebook-convert input.pdf output.md
```

### Step 3: 格式标准化脚本

创建标准化处理脚本：

```python
# scripts/normalize_markdown.py
import re
from pathlib import Path

def normalize_markdown(file_path: Path, metadata: dict) -> str:
    """标准化Markdown格式，添加元数据头部"""
    content = file_path.read_text(encoding='utf-8')

    # 添加YAML Front Matter
    front_matter = "---\n"
    for key, value in metadata.items():
        front_matter += f"{key}: {value}\n"
    front_matter += "---\n\n"

    return front_matter + content

# 批量处理
def process_book_dir(book_dir: Path, book_name: str, domain: str):
    for md_file in book_dir.rglob("*.md"):
        metadata = {
            "book_name": book_name,
            "domain": domain,
            "source_file": str(md_file.relative_to(book_dir))
        }
        normalized = normalize_markdown(md_file, metadata)
        md_file.write_text(normalized, encoding='utf-8')
```

### Step 4: 更新注册表

在 `config/source_registry.json` 中添加新教材：

```json
{
  "canonical_source_id": "动手学深度学习",
  "display_name": "动手学深度学习",
  "aliases": ["Dive into Deep Learning", "d2l", "李沐 深度学习"],
  "domain": "deep_learning",
  "language": "zh-CN",
  "trust_tier": "primary",
  "priority": 100
}
```

在 `config/knowledge_routes.json` 中添加路由：

```json
{
  "course_routing": {
    "深度学习": {
      "深度学习": 2.0,
      "神经网络": 2.0,
      "CNN": 2.0,
      "RNN": 2.0,
      "Transformer": 2.0,
      "PyTorch": 1.5,
      "反向传播": 2.0
    },
    "机器学习": {
      "机器学习": 2.0,
      "监督学习": 2.0,
      "无监督学习": 2.0,
      "决策树": 2.0,
      "SVM": 2.0,
      "随机森林": 1.5
    }
  },
  "course_linkage": {
    "深度学习": ["机器学习", "神经网络"],
    "机器学习": ["深度学习", "数据结构", "算法"]
  }
}
```

### Step 5: 重建向量索引

```bash
cd /Users/apple/Code/software/server

# 运行索引构建脚本
uv run python app/rag/build_chroma.py
```

---

## 五、知识库现状与目标对比

### 当前状态 (28本，22MB)

| 领域 | 覆盖情况 | 数量 |
|------|---------|------|
| 计算机网络 | ✅ 完整 | 2本 |
| 操作系统 | ✅ 完整 | 2本 |
| 数据结构 | ✅ 完整 | 4本 |
| 计算机组成原理 | ✅ 完整 | 4本 |
| Java | ✅ 基础 | 1本 |
| Python | ✅ 基础 | 2本 |
| 数据库 | ✅ 完整 | 2本 |
| Redis | ✅ 完整 | 1本 |
| Vue | ✅ 完整 | 1本 |
| 算法 | ✅ 基础 | 1本 |
| 软件工程 | ✅ 完整 | 3本 |
| 数学 | ✅ 基础 | 3本 |
| **AI/机器学习** | ❌ 缺失 | 0本 |
| **编译原理** | ❌ 缺失 | 0本 |
| **网络安全** | ❌ 缺失 | 0本 |
| **分布式系统** | ❌ 缺失 | 0本 |

### 目标状态 (50+本，50-100MB)

| 阶段 | 新增领域 | 新增数量 |
|------|---------|----------|
| Phase 1 | AI/机器学习/深度学习 | 5-10本 |
| Phase 2 | 编译原理/离散数学/安全 | 5本 |
| Phase 3 | 分布式/云原生/大数据 | 5-10本 |
| **总计** | - | **20-25本** |

---

## 六、立即执行清单

### 今天可以完成（开源Markdown）

```bash
# 创建下载脚本
cat > /Users/apple/Code/software/server/app/rag/scripts/download_open_sources.sh << 'EOF'
#!/bin/bash
set -e

BOOK_DIR="/Users/apple/Code/software/server/app/rag/data/book"
cd "$BOOK_DIR"

echo "开始下载开源Markdown教材..."

# 1. 动手学深度学习
if [ ! -d "d2l" ]; then
    echo "下载 d2l-zh..."
    git clone --depth=1 https://github.com/d2l-ai/d2l-zh.git d2l
fi

# 2. 神经网络与深度学习
if [ ! -d "nndl" ]; then
    echo "下载 nndl..."
    git clone --depth=1 https://github.com/nndl/nndl.github.io.git nndl
fi

# 3. 南瓜书
if [ ! -d "pumpkin-book" ]; then
    echo "下载 pumpkin-book..."
    git clone --depth=1 https://github.com/DatawhaleChina/pumpkin-book.git pumpkin-book
fi

# 4. 微软ML教程
if [ ! -d "ml-beginners" ]; then
    echo "下载 ML-For-Beginners..."
    git clone --depth=1 https://github.com/microsoft/ML-For-Beginners.git ml-beginners
fi

# 5. 计算机面试知识总结
if [ ! -d "cs-interview" ]; then
    echo "下载 interview..."
    git clone --depth=1 https://github.com/huihut/interview.git cs-interview
fi

# 6. CS-Notes
if [ ! -d "cs-notes" ]; then
    echo "下载 CS-Notes..."
    git clone --depth=1 https://github.com/CyC2018/CS-Notes.git cs-notes
fi

echo "下载完成！"
echo "检查目录大小："
du -sh */
EOF

chmod +x /Users/apple/Code/software/server/app/rag/scripts/download_open_sources.sh
```

### 需要手动获取的PDF教材

| 教材名称 | 获取方式 | 转换工具 |
|----------|----------|----------|
| 《机器学习》周志华 | 购买正版PDF | Marker/Mathpix |
| 《统计学习方法》李航 | 购买正版PDF | Marker |
| 《算法导论》CLRS | GitHub转换版 | - |
| 《编译原理》龙书 | 购买正版PDF | Marker |

---

## 七、质量保障措施

1. **格式统一**：所有Markdown文件添加统一YAML Front Matter
2. **编码规范**：统一UTF-8编码，处理特殊字符
3. **索引验证**：构建索引后运行测试案例验证
4. **定期更新**：关注开源项目更新，定期同步
5. **版权合规**：优先使用开源资源，PDF资源确保合规使用

---

## 八、参考资源

- 教育部《高等学校计算机科学与技术专业规范》
- ACM/IEEE Computing Curricula 2020
- 中国人工智能学会《人工智能本科专业人才培养方案》
- GitHub Awesome Lists

---

**文档维护**: 本文档应随知识库拓展进度持续更新
**最后更新**: 2026-07-03
