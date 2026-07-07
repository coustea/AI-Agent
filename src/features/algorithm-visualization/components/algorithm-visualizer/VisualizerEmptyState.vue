<template>
  <div class="visualizer-empty-state">
    <div class="empty-copy">
      <span class="empty-kicker">算法可视化</span>
      <h2>在右侧输入代码并点击“运行可视化”</h2>
      <p>系统会在这里展示算法执行过程，帮助你按步骤理解每一次比较、交换和状态变化。</p>
    </div>

    <ul class="empty-tips">
      <li>支持数组排序</li>
      <li>支持图结构遍历</li>
      <li>支持栈、队列、链表等数据结构</li>
    </ul>
  </div>
</template>

<style scoped>
.visualizer-empty-state {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 20px;
  padding: 24px;
  text-align: center;
  background: #ffffff;
}

.empty-copy {
  max-width: 480px;
}

.empty-kicker {
  display: inline-flex;
  align-items: center;
  height: 22px;
  padding: 0 8px;
  border-radius: 4px;
  background: #eff6ff;
  color: #2563eb;
  font-size: 11px;
  font-weight: 600;
  border: 1px solid #bfdbfe;
}

.empty-copy h2 {
  margin: 12px 0 6px;
  font-size: 18px;
  line-height: 1.3;
  color: #0f172a;
  font-weight: 600;
}

.empty-copy p {
  margin: 0;
  font-size: 12px;
  line-height: 1.6;
  color: #64748b;
}

.empty-tips {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  width: min(600px, 100%);
  margin: 0;
  padding: 0;
  list-style: none;
}

.empty-tips li {
  padding: 8px 10px;
  border-radius: 4px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  color: #475569;
  font-size: 11px;
  font-weight: 500;
}

@media (max-width: 900px) {
  .empty-tips {
    grid-template-columns: 1fr;
  }

  .empty-copy h2 {
    font-size: 16px;
  }
}
</style>
