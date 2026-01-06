<template>
  <div class="page-container">
    <header class="main-header">
      <div class="header-content">
        <div class="logo">
          <span class="logo-icon">🤖</span>
          <span class="logo-text">AI Agent Platform</span>
        </div>

        <div class="nav-actions">
          <button class="btn-login">
            Login
          </button>

          <a href="https://github.com/coustea/AI-Agent.git" target="_blank" class="github-link" aria-label="Visit GitHub">
            <svg class="github-icon" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
            </svg>
          </a>
        </div>
      </div>
    </header>
    <main class="hero-section">
      <div class="hero-content">
        <h1 class="hero-title animate-slide-in">
          智能 AI Agent 服务平台
        </h1>
        
        <p class="hero-desc animate-slide-in delay-1">
          汇聚前沿 AI 算法，提供一站式智能代理服务。<br>
          让 AI 技术触手可及，助力您的业务创新与发展。
        </p>
        
        <div class="hero-actions animate-slide-in delay-2">
          <button class="btn btn-primary">
            Get Started
          </button>
          <button class="btn btn-outline">
            Learn More
          </button>
        </div>
      </div>
    </main>

    <section class="features-section" id="features">
      <div class="features-grid">
        <router-link to="/face-recognition" class="feature-card">
          <div class="icon-wrapper bg-blue">
            <svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
            </svg>
          </div>
          <h3 class="card-title">人脸识别</h3>
          <p class="card-desc">高精度人脸检测与识别，支持活体检测、人脸比对等多种场景应用</p>
        </router-link>

        <router-link to="/emotion-analysis" class="feature-card">
          <div class="icon-wrapper bg-purple">
            <svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.828 14.828a4 4 0 01-5.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h3 class="card-title">表情分析</h3>
          <p class="card-desc">实时识别喜怒哀乐等多种情绪，为用户体验研究提供数据支持</p>
        </router-link>

        <router-link to="/body-analysis" class="feature-card">
          <div class="icon-wrapper bg-pink">
            <svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <h3 class="card-title">肢体分析</h3>
          <p class="card-desc">精准捕捉人体姿态与动作，适用于运动分析、健康监测等领域</p>
        </router-link>

        <router-link to="/ocr-scan" class="feature-card">
          <div class="icon-wrapper bg-green">
            <svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <h3 class="card-title">OCR 扫描</h3>
          <p class="card-desc">智能文字识别，支持多语言、手写体、印刷体等多种文档类型</p>
        </router-link>

        <router-link to="/llm-chat" class="feature-card">
          <div class="icon-wrapper bg-orange">
            <svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
            </svg>
          </div>
          <h3 class="card-title">大模型对话</h3>
          <p class="card-desc">接入主流大语言模型，提供智能问答、内容生成等强大能力</p>
        </router-link>

        <router-link to="/rag" class="feature-card">
          <div class="icon-wrapper bg-indigo">
            <svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
            </svg>
          </div>
          <h3 class="card-title">RAG 检索增强</h3>
          <p class="card-desc">结合知识库检索与生成，让 AI 回答更准确、更具专业性</p>
        </router-link>
      </div>
    </section>
  </div>
</template>

<style scoped>
/* ================= 导航栏样式 ================= */
.main-header {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 70px;
  background-color: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(0,0,0,0.06);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
}

.header-content {
  width: 100%;
  max-width: 80rem;
  padding: 0 1.5rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.logo {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 700;
  font-size: 1.25rem;
  color: #0f172a; /* Slate 900 */
}

/* ===== 右侧操作区域样式 (Login左，GitHub右) ===== */
.nav-actions {
  display: flex;
  gap: 1.5rem;
  align-items: center;
  flex-direction: row; 
}

/* ======================================================== */
/* 2026/01/06 修改：Login 按钮改为白色背景、深色字、更小尺寸 */
/* ======================================================== */
.btn-login {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  
  /* 尺寸改小 */
  padding: 0.4rem 0.85rem;
  font-size: 0.85rem;
  font-weight: 500;
  
  /* 颜色改为白色风格 */
  color: #334155;           /* 文字改为深灰色 (Slate 700) */
  background-color: #ffffff;/* 背景改为纯白 */
  border: 1px solid #cbd5e1;/* 添加浅灰边框 (Slate 300) */
  
  border-radius: 6px; 
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.btn-login:hover {
  background-color: #f8fafc; /* 悬停时变为极浅的灰色 */
  border-color: #94a3b8;     /* 边框颜色加深 */
  color: #0f172a;            /* 文字变黑 */
  transform: translateY(-1px);
  box-shadow: 0 2px 4px -1px rgba(0, 0, 0, 0.06);
}

.btn-login:active {
  transform: translateY(0);
  background-color: #f1f5f9; /* 点击时的背景色 */
  border-color: #cbd5e1;
}
/* ======================================================== */

/* GitHub 图标样式 */
.github-link {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #64748b; /* Slate 500 - 默认灰色 */
  transition: all 0.2s;
  padding: 0.25rem; 
  border-radius: 4px;
}

.github-icon {
  width: 1.6rem;
  height: 1.6rem;
}

.github-link:hover {
  color: #0f172a; /* 悬停变为深色 */
  background-color: rgba(15, 23, 42, 0.05);
}

/* ================= 布局与基础样式 ================= */
.page-container {
  font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  color: #1e293b;
  padding-top: 70px; 
}

.hero-section {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: calc(100vh - 70px - 4rem); 
  margin-top: 0;
  padding: 2rem 1rem;
}

.hero-content {
  text-align: center;
  max-width: 48rem;
}

.hero-title {
  font-size: 3rem;
  font-weight: 700;
  margin-bottom: 1.5rem;
  color: #1e293b;
}

.hero-desc {
  font-size: 1.25rem;
  color: #475569;
  margin-bottom: 2rem;
  line-height: 1.625;
}

.hero-actions {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
}

/* Hero 区域的大按钮 */
.btn {
  padding: 0.75rem 2rem;
  font-size: 1rem;
  font-weight: 500;
  border-radius: 0.5rem;
  cursor: pointer;
  transition: all 0.2s;
}

.btn:active {
  transform: translateY(0);
}

.btn-primary {
  color: white;
  border: none;
  background: linear-gradient(to right, #2563eb, #9333ea);
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
}

.btn-primary:hover {
  background: linear-gradient(to right, #1d4ed8, #7e22ce);
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}

.btn-outline {
  color: #334155;
  background-color: white;
  border: 2px solid #cbd5e1;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}

.btn-outline:hover {
  border-color: #3b82f6;
  color: #2563eb;
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
}

/* ================= 卡片区域样式 ================= */
.features-section {
  
  max-width: 80rem;
  margin: -5rem auto 0;
  padding: 2rem 1rem 5rem;
}

.features-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1.5rem;
}

@media (min-width: 768px) {
  .features-grid { grid-template-columns: repeat(2, 1fr); }
}

@media (min-width: 1024px) {
  .features-grid { grid-template-columns: repeat(3, 1fr); }
}

.feature-card {
  display: block;
  background-color: white;
  border-radius: 0.75rem;
  padding: 1.5rem;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
  text-decoration: none;
  color: inherit;
  opacity: 0;
}

.feature-card:hover {
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
  transform: translateY(-4px);
}

.icon-wrapper {
  width: 3rem;
  height: 3rem;
  border-radius: 0.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 1rem;
}

.icon {
  width: 1.75rem;
  height: 1.75rem;
  color: white;
}

.bg-blue { background: linear-gradient(135deg, #3b82f6, #2563eb); }
.bg-purple { background: linear-gradient(135deg, #a855f7, #9333ea); }
.bg-pink { background: linear-gradient(135deg, #ec4899, #db2777); }
.bg-green { background: linear-gradient(135deg, #22c55e, #16a34a); }
.bg-orange { background: linear-gradient(135deg, #f97316, #ea580c); }
.bg-indigo { background: linear-gradient(135deg, #6366f1, #4f46e5); }

.card-title {
  font-size: 1.125rem;
  font-weight: 700;
  margin-bottom: 0.5rem;
  color: #1e293b;
}

.card-desc {
  font-size: 0.875rem;
  color: #475569;
}

/* ================= 动画定义 ================= */

@keyframes slideInLeft {
  from { opacity: 0; transform: translateX(-50px); }
  to { opacity: 1; transform: translateX(0); }
}

@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(30px); }
  to { opacity: 1; transform: translateY(0); }
}

.animate-slide-in {
  opacity: 0;
  animation: slideInLeft 0.8s ease-out forwards;
}

.animate-slide-in.delay-1 { animation-delay: 0.2s; }
.animate-slide-in.delay-2 { animation-delay: 0.4s; }

.feature-card {
  animation: fadeInUp 0.6s ease-out forwards;
}

.feature-card:nth-child(1) { animation-delay: 0.8s; }
.feature-card:nth-child(2) { animation-delay: 0.9s; }
.feature-card:nth-child(3) { animation-delay: 1.0s; }
.feature-card:nth-child(4) { animation-delay: 1.1s; }
.feature-card:nth-child(5) { animation-delay: 1.2s; }
.feature-card:nth-child(6) { animation-delay: 1.3s; }
</style>