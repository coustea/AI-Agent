## 1. 独立子组件开发与状态重构

- [x] 1.1 开发引导入口组件 [PathStartHub.vue](file:///Users/apple/Code/software/src/learning/components/PathStartHub.vue)，实现居中玻璃拟态输入面板、多智能体流程图示和卡片推荐模板
- [x] 1.2 开发多智能体动画组件 [PathAgentLoading.vue](file:///Users/apple/Code/software/src/learning/components/PathAgentLoading.vue)，完成 SVG 画像、检索、规划、校验节点及核心图谱的静息与激活 CSS 动效
- [x] 1.3 移除 `LearnPath.vue` 原有的垂直堆叠侧边栏逻辑，重构右侧检查器的状态控制，用 `activeTab` 变量实现单卡片多 Tab（当前推进、学习信号、诊断文献、路线总结）展示

## 2. 双栏布局重构与文献对接

- [x] 2.1 修改 [LearnPath.vue](file:///Users/apple/Code/software/src/learning/views/LearnPath.vue) 为双栏 Grid 结构（左栏 320px 路线图，右栏自适应详情学习台），彻底清除原有左-中-右三栏布局
- [x] 2.2 重构左栏 Timeline 路线图，仅展示阶段标题与节点名称，确保不渲染大段 mastery 描述，选中节点高亮并在 Timeline 上标示活动轨
- [x] 2.3 重构右栏详情页面，使其成为整个页面唯一显示当前选中节点长描述和学习重点的区域，并在右栏底部实现 Tab 切页
- [x] 2.4 在“诊断文献” Tab 内，添加对 `search_evidence` 数据的读取与解析，渲染为带有跳转超链接和检索词的参考文献卡片列表

## 3. 测试与验证

- [x] 3.1 运行前端构建命令 `npm run build` 验证 TypeScript 声明及编译零错误
- [x] 3.2 运行前端并手动检查，对比新旧排版在不同分辨率下的排布表现，验证文字零冗余、内容零挤压
