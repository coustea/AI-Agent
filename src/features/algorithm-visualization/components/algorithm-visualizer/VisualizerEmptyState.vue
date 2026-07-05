<template>
  <div class="visualizer-empty-state">
    <div class="empty-copy">
      <span class="empty-kicker">算法可视化</span>
      <h2>在右侧输入代码并点击“生成可视化”</h2>
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
  display: grid;
  place-items: center;
  gap: 26px;
  padding: 32px;
  text-align: center;
  background:
    radial-gradient(circle at top left, rgba(37, 99, 235, 0.08), transparent 30%),
    linear-gradient(180deg, rgba(248, 250, 252, 0.7), rgba(255, 255, 255, 0.96));
}

.empty-copy {
  max-width: 560px;
}

.empty-kicker {
  display: inline-flex;
  align-items: center;
  height: 28px;
  padding: 0 12px;
  border-radius: 999px;
  background: rgba(37, 99, 235, 0.1);
  color: #1d4ed8;
  font-size: 12px;
  font-weight: 700;
}

.empty-copy h2 {
  margin: 18px 0 10px;
  font-size: 28px;
  line-height: 1.2;
  color: #0f172a;
}

.empty-copy p {
  margin: 0;
  font-size: 14px;
  line-height: 1.7;
  color: #64748b;
}

.empty-tips {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  width: min(720px, 100%);
  margin: 0;
  padding: 0;
  list-style: none;
}

.empty-tips li {
  padding: 14px 16px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(219, 227, 239, 0.95);
  color: #334155;
  font-size: 13px;
  font-weight: 650;
}

@media (max-width: 900px) {
  .empty-tips {
    grid-template-columns: 1fr;
  }

  .empty-copy h2 {
    font-size: 24px;
  }
}
</style>
