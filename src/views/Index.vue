<template>
    <div class="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
        <nav class="bg-white border-b border-slate-200 sticky top-0 z-50 shadow-sm">
            <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div class="flex justify-between items-center h-16">
                    <!-- Logo 和品牌 -->
                    <div class="flex items-center space-x-3">
                        <div class="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                            <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                            </svg>
                        </div>
                        <span class="text-xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                            AI Agent Hub
                        </span>
                    </div>

                    <!-- 右侧操作区 -->
                    <div class="flex items-center space-x-4">
                        <!-- Login 链接 -->
                        <a href="#" class="text-sm font-medium text-slate-700 hover:text-slate-900 transition-colors">
                            Log in
                        </a>

                        <!-- GitHub 图标 -->
                        <a href="https://github.com/yourusername/yourrepo" target="_blank" rel="noopener noreferrer" class="text-slate-600 hover:text-slate-900 transition-colors">
                            <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                                <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
                            </svg>
                        </a>
                    </div>
                </div>
            </div>
        </nav>

        <main class="flex items-center justify-center h-[calc(100vh-4rem)] -mt-32">
            <div class="text-center max-w-3xl px-4">
                <!-- 主标题 - 从左滑入 -->
                <h1 class="text-5xl font-bold text-slate-800 mb-6 animate-slide-in-left">
                    智能 AI Agent 服务平台
                </h1>
                
                <!-- 介绍文字 - 从左滑入，延迟 -->
                <p class="text-xl text-slate-600 mb-8 leading-relaxed animate-slide-in-left-delay">
                    汇聚前沿 AI 算法，提供一站式智能代理服务。<br>
                    让 AI 技术触手可及，助力您的业务创新与发展。
                </p>
                
                <!-- 按钮组 - 从左滑入，更长延迟 -->
                <div class="flex items-center justify-center gap-4 animate-slide-in-left-delay-2">
                    <button class="px-8 py-3 text-base font-medium text-white bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg hover:from-blue-700 hover:to-purple-700 transition-all shadow-lg hover:shadow-xl transform hover:-translate-y-0.5">
                        Get Started
                    </button>
                    <button class="px-8 py-3 text-base font-medium text-slate-700 bg-white border-2 border-slate-300 rounded-lg hover:border-blue-500 hover:text-blue-600 transition-all shadow-md hover:shadow-lg">
                        Learn More
                    </button>
                </div>
            </div>
        </main>

        <!-- AI 功能卡片区域 -->
        <section class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-20 -mt-32">
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                <!-- 人脸识别卡片 -->
                <router-link to="/face-recognition" class="bg-white rounded-xl p-6 shadow-md hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1 animate-card-1 cursor-pointer block">
                    <div class="w-12 h-12 bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg flex items-center justify-center mb-4">
                        <svg class="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                        </svg>
                    </div>
                    <h3 class="text-lg font-bold text-slate-800 mb-2">人脸识别</h3>
                    <p class="text-sm text-slate-600">高精度人脸检测与识别，支持活体检测、人脸比对等多种场景应用</p>
                </router-link>

                <!-- 表情分析卡片 -->
                <router-link to="/emotion-analysis" class="bg-white rounded-xl p-6 shadow-md hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1 animate-card-2 cursor-pointer block">
                    <div class="w-12 h-12 bg-gradient-to-br from-purple-500 to-purple-600 rounded-lg flex items-center justify-center mb-4">
                        <svg class="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.828 14.828a4 4 0 01-5.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                    </div>
                    <h3 class="text-lg font-bold text-slate-800 mb-2">表情分析</h3>
                    <p class="text-sm text-slate-600">实时识别喜怒哀乐等多种情绪，为用户体验研究提供数据支持</p>
                </router-link>

                <!-- 肢体分析卡片 -->
                <router-link to="/body-analysis" class="bg-white rounded-xl p-6 shadow-md hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1 animate-card-3 cursor-pointer block">
                    <div class="w-12 h-12 bg-gradient-to-br from-pink-500 to-pink-600 rounded-lg flex items-center justify-center mb-4">
                        <svg class="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                        </svg>
                    </div>
                    <h3 class="text-lg font-bold text-slate-800 mb-2">肢体分析</h3>
                    <p class="text-sm text-slate-600">精准捕捉人体姿态与动作，适用于运动分析、健康监测等领域</p>
                </router-link>

                <!-- OCR 扫描卡片 -->
                <router-link to="/ocr-scan" class="bg-white rounded-xl p-6 shadow-md hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1 animate-card-4 cursor-pointer block">
                    <div class="w-12 h-12 bg-gradient-to-br from-green-500 to-green-600 rounded-lg flex items-center justify-center mb-4">
                        <svg class="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                    </div>
                    <h3 class="text-lg font-bold text-slate-800 mb-2">OCR 扫描</h3>
                    <p class="text-sm text-slate-600">智能文字识别，支持多语言、手写体、印刷体等多种文档类型</p>
                </router-link>

                <!-- 大模型对话卡片 -->
                <router-link to="/llm-chat" class="bg-white rounded-xl p-6 shadow-md hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1 animate-card-5 cursor-pointer block">
                    <div class="w-12 h-12 bg-gradient-to-br from-orange-500 to-orange-600 rounded-lg flex items-center justify-center mb-4">
                        <svg class="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                        </svg>
                    </div>
                    <h3 class="text-lg font-bold text-slate-800 mb-2">大模型对话</h3>
                    <p class="text-sm text-slate-600">接入主流大语言模型，提供智能问答、内容生成等强大能力</p>
                </router-link>

                <!-- RAG 检索增强卡片 -->
                <router-link to="/rag" class="bg-white rounded-xl p-6 shadow-md hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1 animate-card-6 cursor-pointer block">
                    <div class="w-12 h-12 bg-gradient-to-br from-indigo-500 to-indigo-600 rounded-lg flex items-center justify-center mb-4">
                        <svg class="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                        </svg>
                    </div>
                    <h3 class="text-lg font-bold text-slate-800 mb-2">RAG 检索增强</h3>
                    <p class="text-sm text-slate-600">结合知识库检索与生成，让 AI 回答更准确、更具专业性</p>
                </router-link>
            </div>
        </section>

        <!-- Footer 页脚 -->
        <footer class="bg-slate-900 text-slate-300">
            <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
                <div class="flex flex-col md:flex-row justify-between items-center space-y-3 md:space-y-0">
                    <!-- 品牌信息 -->
                    <div class="flex items-center space-x-3">
                        <div class="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                            <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                            </svg>
                        </div>
                        <span class="text-lg font-semibold text-white">AI Agent Hub</span>
                    </div>

                    <!-- 版权信息 -->
                    <p class="text-sm text-slate-400">
                        © 2026 AI Agent Hub. All rights reserved.
                    </p>

                    <!-- 社交媒体图标 -->
                    <div class="flex space-x-4">
                        <a href="#" class="text-slate-400 hover:text-blue-400 transition-colors">
                            <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                                <path d="M24 4.557c-.883.392-1.832.656-2.828.775 1.017-.609 1.798-1.574 2.165-2.724-.951.564-2.005.974-3.127 1.195-.897-.957-2.178-1.555-3.594-1.555-3.179 0-5.515 2.966-4.797 6.045-4.091-.205-7.719-2.165-10.148-5.144-1.29 2.213-.669 5.108 1.523 6.574-.806-.026-1.566-.247-2.229-.616-.054 2.281 1.581 4.415 3.949 4.89-.693.188-1.452.232-2.224.084.626 1.956 2.444 3.379 4.6 3.419-2.07 1.623-4.678 2.348-7.29 2.04 2.179 1.397 4.768 2.212 7.548 2.212 9.142 0 14.307-7.721 13.995-14.646.962-.695 1.797-1.562 2.457-2.549z"/>
                            </svg>
                        </a>
                        <a href="#" class="text-slate-400 hover:text-blue-400 transition-colors">
                            <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                                <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
                            </svg>
                        </a>
                        <a href="#" class="text-slate-400 hover:text-blue-400 transition-colors">
                            <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                                <path d="M19 0h-14c-2.761 0-5 2.239-5 5v14c0 2.761 2.239 5 5 5h14c2.762 0 5-2.239 5-5v-14c0-2.761-2.238-5-5-5zm-11 19h-3v-11h3v11zm-1.5-12.268c-.966 0-1.75-.79-1.75-1.764s.784-1.764 1.75-1.764 1.75.79 1.75 1.764-.783 1.764-1.75 1.764zm13.5 12.268h-3v-5.604c0-3.368-4-3.113-4 0v5.604h-3v-11h3v1.765c1.396-2.586 7-2.777 7 2.476v6.759z"/>
                            </svg>
                        </a>
                    </div>
                </div>
            </div>
        </footer>
    </div>
</template>

<style scoped>
/* 从左往右滑入动画 */
@keyframes slideInLeft {
    from {
        opacity: 0;
        transform: translateX(-50px);
    }
    to {
        opacity: 1;
        transform: translateX(0);
    }
}

/* 标题动画 - 立即开始 */
.animate-slide-in-left {
    animation: slideInLeft 0.8s ease-out forwards;
}

/* 介绍文字动画 - 延迟 0.2 秒 */
.animate-slide-in-left-delay {
    opacity: 0;
    animation: slideInLeft 0.8s ease-out 0.2s forwards;
}

/* 按钮组动画 - 延迟 0.4 秒 */
.animate-slide-in-left-delay-2 {
    opacity: 0;
    animation: slideInLeft 0.8s ease-out 0.4s forwards;
}

/* 卡片依次淡入动画 */
@keyframes fadeInUp {
    from {
        opacity: 0;
        transform: translateY(30px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.animate-card-1 {
    opacity: 0;
    animation: fadeInUp 0.6s ease-out 0.8s forwards;
}

.animate-card-2 {
    opacity: 0;
    animation: fadeInUp 0.6s ease-out 0.9s forwards;
}

.animate-card-3 {
    opacity: 0;
    animation: fadeInUp 0.6s ease-out 1s forwards;
}

.animate-card-4 {
    opacity: 0;
    animation: fadeInUp 0.6s ease-out 1.1s forwards;
}

.animate-card-5 {
    opacity: 0;
    animation: fadeInUp 0.6s ease-out 1.2s forwards;
}

.animate-card-6 {
    opacity: 0;
    animation: fadeInUp 0.6s ease-out 1.3s forwards;
}
</style>
