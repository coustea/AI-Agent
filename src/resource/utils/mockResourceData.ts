// 假的资源数据用来观看样式
import type { GeneratedResourceItem, GeneratedResourceBundle } from '@/resource/api/resource-history'

// 动态计算相对时间，返回 ISO 格式字符串
function getRelativeTime(offsetMs: number): string {
  return new Date(Date.now() - offsetMs).toISOString()
}

// 10 个预设任务列表
export function getMockResourceHistory(): GeneratedResourceItem[] {
  return [
    {
      id: 1,
      learning_need: '深度学习核心概念',
      status: 'completed',
      resource_types: ['content', 'mindmap', 'quiz', 'code', 'reading', 'ppt', 'video'],
      created_at: getRelativeTime(0), // 刚刚
      updated_at: getRelativeTime(0)
    },
    {
      id: 2,
      learning_need: 'Python 高级编程指南',
      status: 'completed',
      resource_types: ['content', 'code', 'quiz', 'mindmap'],
      created_at: getRelativeTime(3600000 * 2), // 2小时前
      updated_at: getRelativeTime(3600000 * 2)
    },
    {
      id: 3,
      learning_need: '计算机视觉中的CNN',
      status: 'pending',
      resource_types: [],
      created_at: getRelativeTime(3600000 * 5), // 5小时前
      updated_at: null
    },
    {
      id: 4,
      learning_need: '数据结构：二叉树遍历',
      status: 'completed',
      resource_types: ['content', 'code', 'quiz', 'mindmap'],
      created_at: getRelativeTime(86400000), // 1天前
      updated_at: getRelativeTime(86400000)
    },
    {
      id: 5,
      learning_need: '考研复试英语口语准备',
      status: 'failed',
      resource_types: [],
      created_at: getRelativeTime(86400000 * 2), // 2天前
      updated_at: null
    },
    {
      id: 6,
      learning_need: 'Transformer 模型解析',
      status: 'completed',
      resource_types: ['content', 'mindmap', 'code', 'quiz'],
      created_at: getRelativeTime(86400000 * 3), // 3天前
      updated_at: getRelativeTime(86400000 * 3)
    },
    {
      id: 7,
      learning_need: '操作系统：进程与线程',
      status: 'completed',
      resource_types: ['content', 'quiz', 'mindmap'],
      created_at: getRelativeTime(86400000 * 4), // 4天前
      updated_at: getRelativeTime(86400000 * 4)
    },
    {
      id: 8,
      learning_need: '微服务架构与 Docker 部署',
      status: 'completed',
      resource_types: ['content', 'code', 'mindmap'],
      created_at: getRelativeTime(86400000 * 5), // 5天前
      updated_at: getRelativeTime(86400000 * 5)
    },
    {
      id: 9,
      learning_need: '计算机网络中的 TCP 三次握手',
      status: 'completed',
      resource_types: ['content', 'quiz', 'mindmap'],
      created_at: getRelativeTime(86400000 * 6), // 6天前
      updated_at: getRelativeTime(86400000 * 6)
    },
    {
      id: 10,
      learning_need: '机器学习：线性回归与梯度下降',
      status: 'completed',
      resource_types: ['content', 'code', 'quiz'],
      created_at: getRelativeTime(86400000 * 7), // 7天前
      updated_at: getRelativeTime(86400000 * 7)
    }
  ]
}

// 模拟详细资源内容数据
export function getMockResourceDetail(id: number | string): GeneratedResourceBundle | null {
  const numId = Number(id)
  if (isNaN(numId) || numId < 1 || numId > 10) return null

  // 通用默认数据结构，以防某些 ID 未单独定制
  const createDefaultBundle = (title: string, need: string): GeneratedResourceBundle => ({
    id: String(numId),
    task_id: `task-mock-${numId}`,
    title,
    learning_need: need,
    selected_agents: ['content', 'mindmap', 'quiz'],
    status: 'completed',
    study_path: [],
    review_result: null,
    created_at: getRelativeTime(86400000 * (numId - 1)),
    updated_at: getRelativeTime(86400000 * (numId - 1)),
    metadata: {},
    resources: [
      {
        id: numId * 10 + 1,
        type: 'content',
        title: `${title} - 核心概念讲解`,
        format: 'markdown',
        content: `# ${title} 核心讲解\n\n这是针对“${need}”的智能讲解资源。\n\n## 核心知识要点\n- **定义与概念**：该主题的核心学术或工程定义。\n- **核心机制**：系统分析和底层逻辑框架。\n- **应用场景**：在实际开发或研究中的典型落地场景。\n\n> 本文档为智能体协同生成的个性化学习资源。`,
        summary: `全面梳理了${title}的基础概念与核心运行机理。`,
        summary_data: {},
        metadata: {},
        status: 'completed',
        error_message: null,
        created_at: getRelativeTime(86400000 * (numId - 1)),
        updated_at: null
      },
      {
        id: numId * 10 + 2,
        type: 'mindmap',
        title: `${title} 知识结构图谱`,
        format: 'mermaid',
        content: `\`\`\`mermaid\nmindmap\n  root((${title}))\n    核心概念\n      基本定义\n      关键特征\n    主要内容\n      核心组成部分\n      核心工作原理\n    应用实践\n      工程落地\n      典型案例\n\`\`\``,
        summary: `一键看懂${title}的知识脉络结构。`,
        summary_data: {},
        metadata: {},
        status: 'completed',
        error_message: null,
        created_at: getRelativeTime(86400000 * (numId - 1)),
        updated_at: null
      },
      {
        id: numId * 10 + 3,
        type: 'quiz',
        title: `${title} 阶段能力自测`,
        format: 'json',
        content: JSON.stringify({
          questions: [
            {
              type: 'single_choice',
              question_type: 'single_choice',
              question: `关于 ${title} 的基本概念，以下说法中正确的是？`,
              stem: `关于 ${title} 的基本概念，以下说法中正确的是？`,
              difficulty: 'medium',
              options: [
                { label: 'A', content: '核心机制是由多个复杂模块相互串联而成的' },
                { label: 'B', content: '不需要任何前置知识即可完全掌握' },
                { label: 'C', content: '仅在极少数学术研究中被应用，没有工程实用价值' },
                { label: 'D', content: '以上选项都不对' }
              ],
              answer: 'A',
              explanation: '解析：该主题在实际生产和研究中被广泛应用，通常具有多层次、多模块关联的结构特征，故选 A。'
            },
            {
              type: 'true_false',
              question_type: 'true_false',
              question: `在处理该技术主题时，合理地进行结构优化能显著降低系统耗时。`,
              stem: `在处理该技术主题时，合理地进行结构优化能显著降低系统耗时。`,
              difficulty: 'easy',
              options: [
                { label: 'A', content: '正确' },
                { label: 'B', content: '错误' }
              ],
              answer: 'A',
              explanation: '解析：优化算法/网络设计是降低开销、提升效率的常规手段。'
            }
          ]
        }),
        summary: `包含单选及判断题的阶段性理解评估测验。`,
        summary_data: {},
        metadata: {},
        status: 'completed',
        error_message: null,
        created_at: getRelativeTime(86400000 * (numId - 1)),
        updated_at: null
      }
    ]
  })

  // ID 1: 深度学习核心概念
  if (numId === 1) {
    const bundle = createDefaultBundle('深度学习核心概念', '深度学习核心概念与模型结构')
    bundle.resources = [
      {
        id: 11,
        type: 'content',
        title: '深度学习核心概念与前馈网络',
        format: 'markdown',
        content: `# 深度学习核心概念精讲\n\n深度学习是机器学习的一个分支，它基于人工神经网络的表征学习，旨在通过建立多隐层的学习模型来自动学习特征。\n\n## 1. 神经元与激活函数\n神经元是神经网络的最基本单元。输入向量经权重加权求和，加入偏置后，通过一个非线性激活函数得到输出：\n\n$$y = f(\\sum_{i} w_i x_i + b)$$\n\n### 常见激活函数比较：\n- **Sigmoid**：将输出映射在 $(0, 1)$。由于饱和区导数趋近于0，容易导致梯度消失（Gradient Vanishing）。\n- **Tanh**：零对称输出，映射在 $(-1, 1)$，收敛速度略快于 Sigmoid，但也存在梯度消失问题。\n- **ReLU (Rectified Linear Unit)**：$f(x) = \\max(0, x)$。在正半区导数为1，能有效缓解梯度消失，且计算极快。但在负半区容易导致“神经元坏死（Dying ReLU）”。\n\n## 2. 前向传播与反向传播 (BP)\n- **前向传播 (Forward Propagation)**：输入信号依次通过隐层计算出预测输出，并评估损失函数（Loss Function）。\n- **反向传播 (Backpropagation)**：基于微积分的**链式法则 (Chain Rule)**，将损失函数的梯度从输出层向输入层反向传播，以此计算每个参数的梯度并使用梯度下降算法进行权重更新。`,
        summary: '精讲人工神经元、激活函数（Sigmoid、ReLU等）以及网络的前向与反向传播机制。',
        summary_data: {},
        metadata: {},
        status: 'completed',
        error_message: null,
        created_at: getRelativeTime(0),
        updated_at: null
      },
      {
        id: 12,
        type: 'mindmap',
        title: '深度学习基础知识图谱',
        format: 'mermaid',
        content: `\`\`\`mermaid\nmindmap\n  root((深度学习基础))\n    基本构件\n      人工神经元\n      权重与偏置\n      激活函数\n        Sigmoid\n        ReLU\n        Tanh\n    网络架构\n      前馈神经网络 FNN\n      卷积神经网络 CNN\n      循环神经网络 RNN\n    训练算法\n      损失函数\n      反向传播 BP\n      优化器\n        SGD\n        Adam\n\`\`\``,
        summary: '一图看清深度学习基础架构、网络类型 and 核心算法脉络。',
        summary_data: {},
        metadata: {},
        status: 'completed',
        error_message: null,
        created_at: getRelativeTime(0),
        updated_at: null
      },
      {
        id: 13,
        type: 'quiz',
        title: '神经网络与反向传播自测',
        format: 'json',
        content: JSON.stringify({
          questions: [
            {
              type: 'single_choice',
              question_type: 'single_choice',
              question: '在深层神经网络中，使用以下哪种激活函数能最有效地缓解梯度消失（Gradient Vanishing）问题？',
              stem: '在深层神经网络中，使用以下哪种激活函数能最有效地缓解梯度消失（Gradient Vanishing）问题？',
              difficulty: 'easy',
              options: [
                { label: 'A', content: 'Sigmoid 函数' },
                { label: 'B', content: 'Tanh 函数' },
                { label: 'C', content: 'ReLU 函数' },
                { label: 'D', content: 'Linear 函数' }
              ],
              answer: 'C',
              explanation: '解析：ReLU 函数在正区间的导数恒等于1，避免了深层求导时的级联衰减，因而能有效防止反向传播中的梯度消失，故选 C。'
            },
            {
              type: 'multiple_choice',
              question_type: 'multiple_choice',
              question: '关于神经网络的反向传播（BP）算法，下列说法中正确的有哪些？（多选）',
              stem: '关于神经网络的反向传播（BP）算法，下列说法中正确的有哪些？（多选）',
              difficulty: 'medium',
              options: [
                { label: 'A', content: '反向传播算法的数学基石是多元微积分的链式法则' },
                { label: 'B', content: '反向传播不仅能计算隐层参数的梯度，也能直接计算输入数据的梯度' },
                { label: 'C', content: '反向传播需要存储前向传播的激活值，因此会消耗较多显存' },
                { label: 'D', content: '只要损失函数可导，反向传播就一定能保证网络收敛到全局最小值' }
              ],
              answer: ['A', 'C'],
              explanation: '解析：A 正确；C 正确（反向传播计算梯度时需要前向传播的输出，需要占用显存缓冲）；B 错误（虽然可以对输入求导用于特征可视化，但常规 BP 目的是更新参数，不针对输入）；D 错误（非凸优化问题容易陷入局部极小值或鞍点）。'
            }
          ]
        }),
        summary: '考察激活函数特点与反向传播链式法则的经典概念测验。',
        summary_data: {},
        metadata: {},
        status: 'completed',
        error_message: null,
        created_at: getRelativeTime(0),
        updated_at: null
      },
      {
        id: 14,
        type: 'code',
        title: 'PyTorch 实战：前馈神经网络分类器',
        format: 'markdown',
        content: `### 简易三层前馈神经网络示例 (PyTorch)\n\n以下是使用 PyTorch 实现的一个简易三层前馈神经网络（全连接网络），用于处理模拟分类任务。\n\n\`\`\`python\nimport torch\nimport torch.nn as nn\nimport torch.optim as optim\n\n# 1. 定义网络架构\nclass SimpleFNN(nn.Module):\n    def __init__(self, input_dim, hidden_dim, output_dim):\n        super(SimpleFNN, self).__init__()\n        # 线性层 1\n        self.fc1 = nn.Linear(input_dim, hidden_dim)\n        # 激活函数\n        self.relu = nn.ReLU()\n        # 线性层 2\n        self.fc2 = nn.Linear(hidden_dim, output_dim)\n        \n    def forward(self, x):\n        out = self.fc1(x)\n        out = self.relu(out)\n        out = self.fc2(out)\n        return out\n\n# 2. 实例化模型、损失函数与优化器\ninput_size = 10\nhidden_size = 32\nnum_classes = 2\n\nmodel = SimpleFNN(input_size, hidden_size, num_classes)\ncriterion = nn.CrossEntropyLoss() # 自带 Softmax\noptimizer = optim.Adam(model.parameters(), lr=0.001)\n\n# 3. 产生模拟数据进行单步迭代测试\nx_dummy = torch.randn(5, input_size)   # Batch size = 5\ny_dummy = torch.tensor([1, 0, 1, 1, 0])\n\n# 前向传播\noutputs = model(x_dummy)\nloss = criterion(outputs, y_dummy)\n\n# 反向传播并更新\noptimizer.zero_grad()\nloss.backward()\noptimizer.step()\n\nprint(f"模拟训练单步 Loss: {loss.item():.4f}")\n\`\`\``,
        summary: '使用 PyTorch 编写的全连接神经网络模型定义、前向计算与反向梯度更新的极简模板。',
        summary_data: {},
        metadata: {},
        status: 'completed',
        error_message: null,
        created_at: getRelativeTime(0),
        updated_at: null
      },
      {
        id: 15,
        type: 'reading',
        title: '深度学习核心文献与论文导读',
        format: 'markdown',
        content: '',
        summary: '包括 Deep Learning (Nature 2015)、ImageNet 经典网络架构等在内的奠基性论著与学习指引。',
        summary_data: {
          resources: [
            {
              title: 'Deep Learning (Nature 2015 Review)',
              author_or_source: 'Yann LeCun, Yoshua Bengio, Geoffrey Hinton',
              type: 'Journal Paper',
              recommend_reason: '三大巨头联合撰写的综述性文章，全面阐述了多层网络表征学习的机制，是入局深度学习的必读经典。',
              description: '探讨了深层学习模型如何通过组合简单而非线性的特征来学习复杂映射，涵盖了卷积网、循环网及自然语言处理的先驱尝试。'
            },
            {
              title: 'Neural Networks and Deep Learning',
              author_or_source: 'Michael Nielsen',
              type: 'Free Online Book',
              recommend_reason: '目前对神经网络和反向传播数学推导讲解得最透彻、最直观的免费电子书之一，附带精炼的 Python 实现代码。',
              description: '通过手写体数字识别（MNIST）为切入点，细致讲解了网络损失函数、梯度计算和随机梯度下降的推导与工程实现技巧。'
            }
          ]
        },
        metadata: {},
        status: 'completed',
        error_message: null,
        created_at: getRelativeTime(0),
        updated_at: null
      },
      {
        id: 16,
        type: 'ppt',
        title: '深度学习极简入门大纲',
        format: 'json',
        content: JSON.stringify({
          slides: [
            { title: '深度学习：从感知机 to 多层网络', bullets: ['深度学习在多领域的突破', '什么是表征学习与自动特征提取', '本课程整体路线概览'] },
            { title: '核心基石：人工神经元模型', bullets: ['生物神经元 vs 仿真数学模型', '权重（Weights）与偏置（Bias）的作用', '为什么必须使用非线性激活函数（Activation Functions）'] },
            { title: '如何优化：反向传播与梯度下降', bullets: ['前向计算与误差计算', '链式法则在梯度回传中的应用', 'SGD 及常用优化算法（Adam）的区别'] }
          ]
        }),
        summary: '精炼的 3 页汇报大纲演示文稿，快速演示神经网络演进历程与核心优化方法。',
        summary_data: {},
        metadata: {},
        status: 'completed',
        error_message: null,
        created_at: getRelativeTime(0),
        updated_at: null
      },
      {
        id: 17,
        type: 'video',
        title: '深度学习核心概念与模型机制 - 视频课件',
        format: 'json',
        content: JSON.stringify({
          title: "深度学习与神经网络极简入门",
          duration: 75,
          scenes: [
            {
              time: 0,
              title: "什么是深度学习",
              image_url: "/src/assets/video/scene1.png",
              narration: "哈喽，大家好！欢迎来到学枢 AI 课堂。今天我们将一起探索深度学习的奇妙世界。深度学习是人工智能的核心引擎之一，它模仿人类大脑神经元的工作方式，通过构建深层神经网络，自动从海量数据中提取出复杂的特征。",
              subtitles: [
                { start: 0, end: 4, text: "哈喽，大家好！欢迎来到学枢 AI 课堂。" },
                { start: 4, end: 8, text: "今天我们将一起探索深度学习的奇妙世界。" },
                { start: 8, end: 13, text: "深度学习是人工智能的核心引擎之一，它模仿人脑工作方式。" },
                { start: 13, end: 18, text: "通过构建深层神经网络，自动从数据中提取特征。" }
              ]
            },
            {
              time: 20,
              title: "人工神经元模型",
              image_url: "/src/assets/video/scene2.png",
              narration: "神经网络的核心基石是人工神经元。输入信号经过权重的加权求和，再加上偏置，最后通过激活函数产生输出。为什么要激活函数呢？因为非线性激活函数赋予了神经网络逼近任意复杂函数的能力。",
              subtitles: [
                { start: 20, end: 24, text: "神经网络的核心基石是人工神经元。" },
                { start: 24, end: 29, text: "输入信号经过权重的加权求和，再加上偏置，最后通过激活函数产生输出。" },
                { start: 29, end: 35, text: "非线性激活函数赋予了神经网络逼近任意复杂函数的能力。" }
              ]
            },
            {
              time: 50,
              title: "反向传播与优化",
              image_url: "/src/assets/video/scene3.png",
              narration: "网络是如何学习的呢？这就需要反向传播算法。我们通过损失函数计算出当前的预测误差，然后利用多元微积分的链式法则，将误差梯度从输出层反向传播回输入层，更新网络中的所有权重。最终使误差达到最小。",
              subtitles: [
                { start: 50, end: 54, text: "网络是如何学习的呢？这就需要反向传播算法。" },
                { start: 54, end: 60, text: "我们通过损失函数计算误差，并利用链式法则将误差梯度反向传播。" },
                { start: 60, end: 65, text: "通过更新权重，使预测误差逐步达到最小。" }
              ]
            }
          ]
        }),
        summary: '智能多智能体生成的 1.25 分钟高画质视频课程大纲及讲解配音。',
        summary_data: {},
        metadata: {},
        status: 'completed',
        error_message: null,
        created_at: getRelativeTime(0),
        updated_at: null
      }
    ]
    return bundle
  }

  // ID 2: Python 高级编程指南
  if (numId === 2) {
    const bundle = createDefaultBundle('Python 高级编程指南', '高级语言特性：装饰器、生成器与多线程并发')
    bundle.resources = [
      {
        id: 21,
        type: 'content',
        title: 'Python 高级核心特性：装饰器与元编程',
        format: 'markdown',
        content: `# Python 高级编程核心\n\nPython 是一门极其灵活的动态语言。要写出符合 Python 哲学（Pythonic）的优雅代码，必须深入理解其底层高级特性。\n\n## 1. 装饰器 (Decorators)\n装饰器是一种在不改变原函数结构的情况下动态扩展其功能的高阶函数。它的数学本质是函数闭包：\n\n\`\`\`python\ndef my_decorator(func):\n    def wrapper(*args, **kwargs):\n        # 前置功能\n        print("函数调用前")\n        result = func(*args, **kwargs)\n        # 后置功能\n        print("函数调用后")\n        return result\n    return wrapper\n\`\`\`\n\n## 2. 迭代器与生成器 (Generators)\n- **迭代器协议**：实现了 \`__iter__()\` 和 \`__next__()\` 方法的对象。\n- **生成器**：使用 \`yield\` 关键字的特殊函数。生成器在运行时会**保存当前的上下文状态**，每次调用 \`next()\` 时恢复执行，这使它能以 $O(1)$ 的内存空间处理近乎无限的数据流（懒加载）。`,
        summary: '深度剖析 Python 函数闭包、高阶装饰器、元类以及基于 yield 的惰性求值生成器机制。',
        summary_data: {},
        metadata: {},
        status: 'completed',
        error_message: null,
        created_at: getRelativeTime(3600000 * 2),
        updated_at: null
      },
      {
        id: 22,
        type: 'code',
        title: '代码示例：通用计时装饰器与生成器管道',
        format: 'markdown',
        content: `### Python 高级特性代码演练\n\n#### 示例一：实现带参数的通用耗时计算装饰器\n\n\`\`\`python\nimport time\nimport functools\n\ndef log_execution_time(precision=4):\n    def decorator(func):\n        @functools.wraps(func) # 保持原函数的元数据不丢失\n        def wrapper(*args, **kwargs):\n            start_time = time.perf_counter()\n            res = func(*args, **kwargs)\n            duration = time.perf_counter() - start_time\n            print(f"[LOG] {func.__name__} 执行耗时: {duration:.{precision}f} 秒")\n            return res\n        return wrapper\n    return decorator\n\n@log_execution_time(precision=6)\ndef compute_heavy_task(n):\n    return sum(i * i for i in range(n))\n\n# 测试调用\n_ = compute_heavy_task(1000000)\n\`\`\`\n\n#### 示例二：生成器流处理大文件\n\n\`\`\`python\ndef read_large_file(file_path):\n    with open(file_path, 'r', encoding='utf-8') as f:\n        for line in f:\n            yield line.strip()\n\n# 生成器管道过滤：无额外内存占用\nlog_lines = read_large_file("server.log")\nerror_logs = (line for line in log_lines if "[ERROR]" in line)\n\n# 每次拉取一行\nfor i, err in enumerate(error_logs):\n    if i >= 5: break\n    print(f"异常行: {err}")\n\`\`\``,
        summary: '展示了带参数装饰器的闭包实现，以及基于生成器管道（generator pipelines）的高效流式数据读取方式。',
        summary_data: {},
        metadata: {},
        status: 'completed',
        error_message: null,
        created_at: getRelativeTime(3600000 * 2),
        updated_at: null
      },
      {
        id: 23,
        type: 'quiz',
        title: 'Python 动态特性与并发模型自测',
        format: 'json',
        content: JSON.stringify({
          questions: [
            {
              type: 'single_choice',
              question_type: 'single_choice',
              question: '在 Python 中，由于全局解释器锁（GIL）的存在，对于 CPU 密集型任务，以下哪种并发方式最为有效？',
              stem: '在 Python 中，由于全局解释器锁（GIL）的存在，对于 CPU 密集型任务，以下哪种并发方式最为有效？',
              difficulty: 'medium',
              options: [
                { label: 'A', content: '使用 threading 模块（多线程）' },
                { label: 'B', content: '使用 multiprocessing 模块（多进程）' },
                { label: 'C', content: '使用 asyncio 模块（协程）' },
                { label: 'D', content: '使用单线程循环结构' }
              ],
              answer: 'B',
              explanation: '解析：Python GIL 使得同一时刻只有一个线程能执行字节码，导致多线程无法利用多核 CPU。而多进程（multiprocessing）拥有独立的 Python 解释器和独立的 GIL 锁，能够真正实现多核并行计算，故选 B。'
            }
          ]
        }),
        summary: '考察 GIL 锁局限性与多进程/多线程在不同并发场景下差异的自测题。',
        summary_data: {},
        metadata: {},
        status: 'completed',
        error_message: null,
        created_at: getRelativeTime(3600000 * 2),
        updated_at: null
      },
      {
        id: 24,
        type: 'mindmap',
        title: 'Python 高级开发全景图谱',
        format: 'mermaid',
        content: `\`\`\`mermaid\nmindmap\n  root((Python 高级特性))\n    函数式编程\n      装饰器\n      闭包\n      匿名函数 Lambda\n    内存与流处理\n      迭代器协议\n      生成器 yield\n      弱引用 weakref\n    动态元编程\n      __getattr__与__getattribute__\n      元类 metaclass\n      反射 getattr/setattr\n    并发机制\n      GIL 限制\n      多线程 Threading\n      多进程 Multiprocessing\n      协程 asyncio\n\`\`\``,
        summary: '覆盖函数式、元编程、内存机制和并发模型的 Python 进阶技术全景思维导图。',
        summary_data: {},
        metadata: {},
        status: 'completed',
        error_message: null,
        created_at: getRelativeTime(3600000 * 2),
        updated_at: null
      }
    ]
    return bundle
  }

  // ID 3: 计算机视觉中的CNN (pending)
  if (numId === 3) {
    const bundle = createDefaultBundle('计算机视觉中的CNN', '卷积神经网络CNN：卷积层、池化层与图像分类')
    bundle.status = 'processing'
    bundle.resources = []
    return bundle
  }

  // ID 4: 数据结构：二叉树遍历
  if (numId === 4) {
    const bundle = createDefaultBundle('数据结构：二叉树遍历', '数据结构精讲：二叉树深度优先（前中后序）与广度优先遍历')
    bundle.resources = [
      {
        id: 41,
        type: 'content',
        title: '二叉树遍历的深度剖析与边界状态',
        format: 'markdown',
        content: `# 二叉树的深度优先与广度优先遍历\n\n二叉树遍历是指按照某种特定顺序访问二叉树中的所有节点，每个节点仅被访问一次。\n\n## 1. 深度优先搜索 (DFS)\n根据访问根节点、左子树、右子树的相对顺序，DFS 分为三种：\n- **前序遍历 (Pre-order)**：根 $\\to$ 左 $\\to$ 右\n- **中序遍历 (In-order)**：左 $\\to$ 根 $\\to$ 右（对于二叉搜索树，中序遍历结果为单调递增序列）\n- **后序遍历 (Post-order)**：左 $\\to$ 右 $\\to$ 根\n\n其递归实现极其自然，但在大规模数据下递归栈可能溢出。迭代实现需要借助**显式辅助栈**。\n\n## 2. 广度优先搜索 (BFS / 层序遍历)\n广度优先搜索按层从上到下、从左到右依次访问。层序遍历通常使用**双端队列 (Queue)** 辅助实现，算法时间复杂度为 $O(N)$，空间复杂度取决于树的最大宽度。`,
        summary: '系统讲解二叉树前序、中序、后序、层序遍历的递归与迭代原理及边界条件。',
        summary_data: {},
        metadata: {},
        status: 'completed',
        error_message: null,
        created_at: getRelativeTime(86400000),
        updated_at: null
      },
      {
        id: 42,
        type: 'code',
        title: '递归与非递归二叉树遍历算法实现',
        format: 'markdown',
        content: `### 二叉树遍历算法 Python 完整实现\n\n\`\`\`python\nfrom collections import deque\n\n# 定义二叉树节点\nclass TreeNode:\n    def __init__(self, val=0, left=None, right=None):\n        self.val = val\n        self.left = left\n        self.right = right\n\n# 1. 中序遍历 - 递归方式\ndef inorder_recursive(root):\n    res = []\n    def dfs(node):\n        if not node: return\n        dfs(node.left)\n        res.append(node.val)\n        dfs(node.right)\n    dfs(root)\n    return res\n\n# 2. 中序遍历 - 显式栈迭代方式 (非递归)\ndef inorder_iterative(root):\n    res = []\n    stack = []\n    curr = root\n    while curr or stack:\n        # 极左下探\n        while curr:\n            stack.append(curr)\n            curr = curr.left\n        # 弹出栈顶并记录\n        curr = stack.pop()\n        res.append(curr.val)\n        # 转向右子树\n        curr = curr.right\n    return res\n\n# 3. 广度优先层序遍历\ndef level_order(root):\n    if not root: return []\n    res = []\n    queue = deque([root])\n    while queue:\n        level_size = len(queue)\n        level_nodes = []\n        for _ in range(level_size):\n            node = queue.popleft()\n            level_nodes.append(node.val)\n            if node.left: queue.append(node.left)\n            if node.right: queue.append(node.right)\n        res.append(level_nodes)\n    return res\n\`\`\``,
        summary: '用 Python 实现的二叉树中序遍历（递归与双指针迭代）及基于队列的层序遍历的工业级算法模板。',
        summary_data: {},
        metadata: {},
        status: 'completed',
        error_message: null,
        created_at: getRelativeTime(86400000),
        updated_at: null
      },
      {
        id: 43,
        type: 'quiz',
        title: '二叉树遍历性质与递归复杂度分析自测',
        format: 'json',
        content: JSON.stringify({
          questions: [
            {
              type: 'single_choice',
              question_type: 'single_choice',
              question: '某二叉树的先序遍历序列为 ABC，后序遍历序列为 CBA，则该二叉树可能是什么形态？',
              stem: '某二叉树的先序遍历序列为 ABC，后序遍历序列为 CBA，则该二叉树可能是什么形态？',
              difficulty: 'hard',
              options: [
                { label: 'A', content: '该树只能有一个根节点，且所有节点均只有左孩子' },
                { label: 'B', content: '该树的根节点有左、右孩子，结构对称' },
                { label: 'C', content: '该树中任何一个度为2的节点均不存在，是一条退化的链结构' },
                { label: 'D', content: '以上情况都不对' }
              ],
              answer: 'C',
              explanation: '解析：当先序序列与后序序列正好完全相反时，说明每个双亲节点都只有一个孩子（即左子树或右子树为空），树退化为一条单支链，不存在度为2（即拥有左右两个孩子）的节点，故选 C。'
            }
          ]
        }),
        summary: '挑战题：根据前序与后序序列反推二叉树拓扑形态与退化特征。',
        summary_data: {},
        metadata: {},
        status: 'completed',
        error_message: null,
        created_at: getRelativeTime(86400000),
        updated_at: null
      },
      {
        id: 44,
        type: 'mindmap',
        title: '树与二叉树算法知识脑图',
        format: 'mermaid',
        content: `\`\`\`mermaid\nmindmap\n  root((二叉树遍历))\n    深度优先 DFS\n      前序遍历\n        根-左-右\n      中序遍历\n        左-根-右\n        BST升序特征\n      后序遍历\n        左-右-根\n    广度优先 BFS\n      层序遍历\n      使用队列 Queue\n    实现策略\n      递归法\n        简练但防爆栈\n      迭代法\n        双指针+显式栈\n      莫里斯遍历 Morris\n        空间O(1)的巧妙线索化\n\`\`\``,
        summary: '清晰勾勒出 DFS（前中后）与 BFS（层序）以及常用算法优化路径的结构图。',
        summary_data: {},
        metadata: {},
        status: 'completed',
        error_message: null,
        created_at: getRelativeTime(86400000),
        updated_at: null
      }
    ]
    return bundle
  }

  // ID 5: 考研复试英语口语准备 (failed)
  if (numId === 5) {
    const bundle = createDefaultBundle('考研复试英语口语准备', '研究生英语口语：自我介绍与常见问答模块生成')
    bundle.status = 'failed'
    bundle.resources = [
      {
        id: 51,
        type: 'content',
        title: '研究生面试口语指南',
        format: 'markdown',
        content: null,
        summary: '无可用数据。',
        summary_data: {},
        metadata: {},
        status: 'failed',
        error_message: '由于大模型响应超时，智能代理任务中断。请点击重新生成以发起重试。',
        created_at: getRelativeTime(86400000 * 2),
        updated_at: null
      }
    ]
    return bundle
  }

  // ID 6: Transformer 模型解析
  if (numId === 6) {
    const bundle = createDefaultBundle('Transformer 模型解析', '大模型基石：Transformer 架构设计与 Self-Attention 计算细节')
    bundle.resources = [
      {
        id: 61,
        type: 'content',
        title: 'Transformer 骨架设计与注意力机制推导',
        format: 'markdown',
        content: `# Transformer 架构与注意力机制\n\nTransformer 是由 Vaswani 等人在 2017 年发表的论文《Attention Is All You Need》中提出的一种序列转导模型，它彻底摒弃了循环连接（RNN）和卷积结构（CNN）。\n\n## 1. 缩放点积注意力 (Scaled Dot-Product Attention)\n自注意力机制的底层运算逻辑是将查询向量（Query）与键向量（Key）做点积，以评估相关性分值，通过 Softmax 归一化后作为权重与值向量（Value）相乘输出：\n\n$$\\text{Attention}(Q, K, V) = \\text{softmax}\\left(\\frac{QK^T}{\\sqrt{d_k}}\\right)V$$\n\n- **为什么需要缩放因子 $\\sqrt{d_k}$？** 当维度 $d_k$ 很大时，点积的值在量级上会非常大，导致 Softmax 函数进入梯度极小的饱和区。除以 $\\sqrt{d_k}$ 能将点积值方差控制在1左右，确保梯度传导顺畅。\n\n## 2. 多头注意力 (Multi-Head Attention)\n多头注意力机制将 $Q, K, V$ 投影到多个不同的低维空间，并行进行自注意力计算，最后将多个头的输出拼接（Concat）并经线性投影后输出。它允许模型在不同的子空间内联合关注不同位置的表征信息。`,
        summary: '详细解析 Transformer 多头注意力计算公式、缩放因子推导背景及 Encoder-Decoder 结构。',
        summary_data: {},
        metadata: {},
        status: 'completed',
        error_message: null,
        created_at: getRelativeTime(86400000 * 3),
        updated_at: null
      },
      {
        id: 62,
        type: 'mindmap',
        title: 'Transformer 模型全景架构思维导图',
        format: 'mermaid',
        content: `\`\`\`mermaid\nmindmap\n  root((Transformer 架构))\n    核心输入层\n      词嵌入 Embedding\n      位置编码 Positional\n    编码器块 Encoder\n      多头自注意力 MHA\n      残差连接与层归一化 Add&Norm\n      前馈神经网络 FFN\n    解码器块 Decoder\n      掩码多头注意力 Masked MHA\n      交叉注意力 Cross-Attention\n      Add & Norm 层\n    输出层\n      线性映射 Linear\n      归一化 Softmax\n\`\`\``,
        summary: '全方位剖析 Transformer 输入端、Encoder 块、Decoder 块以及最终输出层的流转全景。',
        summary_data: {},
        metadata: {},
        status: 'completed',
        error_message: null,
        created_at: getRelativeTime(86400000 * 3),
        updated_at: null
      },
      {
        id: 63,
        type: 'code',
        title: 'PyTorch 手写实现 Self-Attention 模块',
        format: 'markdown',
        content: `### 手写 Self-Attention 核心计算流程 (PyTorch)\n\n以下是使用 PyTorch 实现的 Scaled Dot-Product Self-Attention 的极简模块，可以直观地看到张量形状的变化。\n\n\`\`\`python\nimport math\nimport torch\nimport torch.nn as nn\nimport torch.nn.functional as F\n\nclass ScaledDotProductAttention(nn.Module):\n    def __init__(self, d_k):\n        super(ScaledDotProductAttention, self).__init__()\n        self.scale = 1.0 / math.sqrt(d_k)\n\n    def forward(self, Q, K, V, mask=None):\n        # Q: [batch_size, seq_len, d_k]\n        # K: [batch_size, seq_len, d_k]\n        # V: [batch_size, seq_len, d_v]\n        \n        # 1. 计算 Q 与 K 相似度得分: [batch_size, seq_len, seq_len]\n        scores = torch.matmul(Q, K.transpose(-2, -1)) * self.scale\n        \n        # 2. 如果存在掩码（针对解码器或 Padding 填充机制），将对应位置分值置为极小值\n        if mask is not None:\n            scores = scores.masked_fill(mask == 0, -1e9)\n            \n        # 3. 归一化概率分布: [batch_size, seq_len, seq_len]\n        attn_weights = F.softmax(scores, dim=-1)\n        \n        # 4. 加权求和输出: [batch_size, seq_len, d_v]\n        output = torch.matmul(attn_weights, V)\n        \n        return output, attn_weights\n\n# 快速自测\nbatch_size, seq_len, d_k, d_v = 2, 5, 8, 8\nQ_dummy = torch.randn(batch_size, seq_len, d_k)\nK_dummy = torch.randn(batch_size, seq_len, d_k)\nV_dummy = torch.randn(batch_size, seq_len, d_v)\n\nattention_layer = ScaledDotProductAttention(d_k)\noutput, weights = attention_layer(Q_dummy, K_dummy, V_dummy)\nprint("输出形状:", output.shape)\nprint("权重矩阵形状:", weights.shape)\n\`\`\``,
        summary: '用 PyTorch 纯张量运算手写实现的缩放点积自注意力层 model，附带形状变化注释与自测用例。',
        summary_data: {},
        metadata: {},
        status: 'completed',
        error_message: null,
        created_at: getRelativeTime(86400000 * 3),
        updated_at: null
      },
      {
        id: 64,
        type: 'quiz',
        title: 'Transformer 结构性关键问题评测',
        format: 'json',
        content: JSON.stringify({
          questions: [
            {
              type: 'single_choice',
              question_type: 'single_choice',
              question: '在 Transformer 的 Decoder 模块中，Masked Multi-Head Attention 层使用掩码的目的是什么？',
              stem: '在 Transformer 的 Decoder 模块中，Masked Multi-Head Attention 层使用掩码的目的是什么？',
              difficulty: 'medium',
              options: [
                { label: 'A', content: '加快模型的前向计算与推理速度' },
                { label: 'B', content: '使得解码时当前位置不能看到序列中当前位置后面的未来信息，防止信息泄漏' },
                { label: 'C', content: '过滤掉输入序列中的常用虚词和标点符号' },
                { label: 'D', content: '强制让模型只关注左侧最靠近的相邻节点' }
              ],
              answer: 'B',
              explanation: '解析：在生成任务（自回归预测）中，Decoder 预测第 t 个词时，不能提前获知第 t 之后的未来词。Masked 自注意力使用下三角掩码矩阵把未来位置的得分设为极小值，从而遮蔽未来信息，确保自回归推理的逻辑正确，故选 B。'
            }
          ]
        }),
        summary: '考察 Decoder 掩码注意力防止未来数据泄漏的核心设计原理测验。',
        summary_data: {},
        metadata: {},
        status: 'completed',
        error_message: null,
        created_at: getRelativeTime(86400000 * 3),
        updated_at: null
      }
    ]
    return bundle
  }

  return createDefaultBundle(
    numId === 7 ? '操作系统：进程与线程' :
    numId === 8 ? '微服务架构与 Docker 部署' :
    numId === 9 ? '计算机网络中的 TCP 三次握手' : '机器学习：线性回归与梯度下降',
    numId === 7 ? '计算机系统基础：进程控制、线程同步与上下文切换' :
    numId === 8 ? '微服务与云原生：Docker 镜像构建与容器集群部署' :
    numId === 9 ? '计算机网络核心：TCP 握手机制与可靠数据传输' : '传统机器学习：线性回归方程、损失函数及梯度下降求解'
  )
}
