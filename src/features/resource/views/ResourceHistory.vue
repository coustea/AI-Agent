<template>
  <main class="resource-history-page">
    <div class="history-shell">
      <header class="history-header">
        <div class="header-main">
          <button
              type="button"
              class="back-button"
              aria-label="返回资源生成"
              @click="router.push('/resource-generator')"
          >
            <span class="direction-icon direction-left direction-icon-large" aria-hidden="true"></span>
          </button>

          <div class="header-copy">
            <div class="header-title-row">
              <h1>资源生成历史</h1>

              <span
                  v-if="total > 0"
                  class="history-total"
              >
                {{ total }} 条记录
              </span>
            </div>

            <p>
              查看多智能体协同生成的学习资源，并继续之前的学习任务。
            </p>
          </div>
        </div>

        <button
            type="button"
            class="create-resource-button"
            @click="router.push('/resource-generator')"
        >
          <Plus :size="16" weight="bold" />
          生成新资源
        </button>
      </header>

      <section
          v-if="total > 0 || loading"
          class="history-toolbar"
      >
        <div class="toolbar-summary">
          <span
              class="summary-dot"
              :class="{ loading }"
          ></span>

          <p>
            <template v-if="loading">
              正在同步资源生成记录
            </template>

            <template v-else>
              当前第 {{ currentPage }} 页，共
              {{ totalPages }} 页
            </template>
          </p>
        </div>

        <label class="page-size-control">
          <span>每页显示</span>

          <select
              v-model.number="pageSize"
              aria-label="每页显示数量"
              :disabled="loading"
              @change="handleSizeChange"
          >
            <option :value="12">12 条</option>
            <option :value="24">24 条</option>
            <option :value="48">48 条</option>
          </select>
        </label>
      </section>

      <!-- 加载骨架 -->
      <section
          v-if="loading"
          class="history-loading"
          aria-label="正在加载历史记录"
      >
        <div
            v-for="index in 6"
            :key="index"
            class="history-skeleton"
        >
          <div class="skeleton-agent"></div>

          <div class="skeleton-content">
            <div class="skeleton-title"></div>
            <div class="skeleton-meta"></div>

            <div class="skeleton-tags">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>

          <div class="skeleton-action"></div>
        </div>
      </section>

      <!-- 加载失败 -->
      <section
          v-else-if="loadError"
          class="history-state error-state"
      >
        <div class="state-icon error-icon">
          <WarningCircle :size="25" weight="duotone" />
        </div>

        <h2>历史记录加载失败</h2>
        <p>{{ loadError }}</p>

        <button
            type="button"
            class="state-primary-button"
            @click="fetchHistory"
        >
          <ArrowClockwise :size="16" weight="bold" />
          重新加载
        </button>
      </section>

      <!-- 空状态 -->
      <section
          v-else-if="historyList.length === 0"
          class="history-state empty-state"
      >
        <div class="state-icon">
          <Files :size="25" weight="duotone" />
        </div>

        <h2>还没有资源生成记录</h2>

        <p>
          输入学习目标后，系统会调度多个智能体协同生成讲解、题目、导图、代码和课件。
        </p>

        <button
            type="button"
            class="state-primary-button"
            @click="router.push('/resource-generator')"
        >
          <Plus :size="16" weight="bold" />
          开始生成资源
        </button>
      </section>

      <!-- 历史记录列表 -->
      <section
          v-else
          class="history-content"
      >
        <section
            v-for="group in groupedHistory"
            :key="group.key"
            class="history-group"
        >
          <header class="group-header">
            <div class="group-title">
              <CalendarBlank :size="18" weight="fill" class="group-calendar-icon" />

              <div>
                <h2>{{ group.label }}</h2>
                <p>{{ group.fullDate }}</p>
              </div>
            </div>

            <span>{{ group.items.length }} 条</span>
          </header>

          <div class="history-list">
            <article
                v-for="item in group.items"
                :key="item.id"
                class="history-item"
                :class="[
                `status-${normalizeStatus(item.status)}`,
              ]"
                tabindex="0"
                role="button"
                :aria-label="`${item.topic || '资源生成任务'}，${getStatusText(item.status)}`"
                @click="goToDetail(item.id)"
                @keydown.enter="goToDetail(item.id)"
                @keydown.space.prevent="goToDetail(item.id)"
            >
              <!-- 多智能体状态标识 -->
              <div class="agent-output-column">
                <div
                    class="agent-cluster"
                    :class="`cluster-${normalizeStatus(item.status)}`"
                >
                  <span class="agent-dot dot-primary"></span>
                  <span class="agent-dot dot-secondary"></span>
                  <span class="agent-dot dot-tertiary"></span>

                  <i class="cluster-status-dot"></i>
                </div>

                <div
                    v-if="normalizeStatus(item.status) === 'running'"
                    class="agent-running-line"
                    aria-hidden="true"
                ></div>
              </div>

              <!-- 记录主体 -->
              <div class="history-item-main">
                <div class="item-heading">
                  <div class="item-title-block">
                    <span class="item-category">
                      MULTI-AGENT RESOURCE
                    </span>

                    <h3>
                      {{
                        item.topic ||
                        "未提供学习需求"
                      }}
                    </h3>
                  </div>

                  <span
                      class="status-badge"
                      :class="`badge-${normalizeStatus(item.status)}`"
                  >
                    <i></i>
                    {{ getStatusText(item.status) }}
                  </span>
                </div>

                <div class="resource-summary">
                  <div
                      v-if="item.resource_types?.length"
                      class="resource-type-list"
                  >
                    <span
                        v-for="type in getVisibleResourceTypes(item)"
                        :key="type"
                        class="resource-type-tag"
                    >
                      {{ getResourceTypeLabel(type) }}
                    </span>

                    <span
                        v-if="getHiddenResourceCount(item) > 0"
                        class="resource-type-tag more-tag"
                    >
                      +{{ getHiddenResourceCount(item) }}
                    </span>
                  </div>

                  <span
                      v-else
                      class="resource-type-empty"
                  >
                    {{
                      normalizeStatus(item.status) === "running"
                          ? "资源仍在生成中"
                          : normalizeStatus(item.status) === "failed"
                              ? "本次任务未生成资源"
                              : "暂无资源产物"
                    }}
                  </span>
                </div>

                <footer class="item-meta">
                  <span>
                    <Clock :size="13" weight="fill" class="meta-icon" />
                    {{ formatClock(item.created_at) }}
                  </span>

                  <i></i>

                  <span>
                    <Stack :size="13" weight="fill" class="meta-icon" />
                    {{ item.resource_types?.length || 0 }}
                    类资源
                  </span>

                  <i></i>

                  <span>
                    {{ getStatusDescription(item.status) }}
                  </span>
                </footer>
              </div>

              <!-- 操作入口 -->
              <div class="item-action-column">
                <button
                    type="button"
                    class="item-action-button"
                    :class="`action-${normalizeStatus(item.status)}`"
                    @click.stop="goToDetail(item.id)"
                >
                  {{ getActionText(item.status) }}
                  <span class="direction-icon direction-right action-arrow" aria-hidden="true"></span>
                </button>
              </div>
            </article>
          </div>
        </section>
      </section>

      <!-- 分页 -->
      <footer
          v-if="!loading && total > 0"
          class="history-pagination"
      >
        <div class="pagination-info">
          <strong>{{ total }}</strong>
          <span>条生成记录</span>
        </div>

        <div class="pagination-controls">
          <button
              type="button"
              class="pagination-button"
              :disabled="currentPage <= 1"
              @click="handleCurrentChange(currentPage - 1)"
          >
            <span class="direction-icon direction-left pagination-icon" aria-hidden="true"></span>
            上一页
          </button>

          <div class="page-indicator">
            <span>第</span>
            <strong>{{ currentPage }}</strong>
            <span>/ {{ totalPages }} 页</span>
          </div>

          <button
              type="button"
              class="pagination-button"
              :disabled="currentPage >= totalPages"
              @click="handleCurrentChange(currentPage + 1)"
          >
            下一页
            <span class="direction-icon direction-right pagination-icon" aria-hidden="true"></span>
          </button>
        </div>
      </footer>
    </div>
  </main>
</template>

<script setup lang="ts">
import {
  computed,
  onMounted,
  ref,
} from "vue";
import { useRouter } from "vue-router";
import {
  PhArrowClockwise as ArrowClockwise,
  PhCalendarBlank as CalendarBlank,
  PhClock as Clock,
  PhFiles as Files,
  PhPlus as Plus,
  PhStack as Stack,
  PhWarningCircle as WarningCircle,
} from "@phosphor-icons/vue";

import {
  getGeneratedResources,
} from "@/features/resource/api/resource";
import type {
  GeneratedResourceHistoryItem,
} from "@/features/resource/model/resource";
import {
  getArtifactLabel as getResourceTypeLabel,
} from "@/shared/content/kind";

type HistoryStatus =
    | "success"
    | "running"
    | "failed"
    | "waiting";

interface HistoryGroup {
  key: string;
  label: string;
  fullDate: string;
  items: GeneratedResourceHistoryItem[];
}

const router = useRouter();

const loading = ref(false);
const loadError = ref("");
const historyList = ref<GeneratedResourceHistoryItem[]>([]);
const currentPage = ref(1);
const pageSize = ref(12);
const total = ref(0);

const totalPages = computed(() => {
  return Math.max(
      1,
      Math.ceil(total.value / pageSize.value),
  );
});

const groupedHistory = computed<HistoryGroup[]>(() => {
  const groups = new Map<
      string,
      GeneratedResourceHistoryItem[]
  >();

  historyList.value.forEach((item) => {
    const key = getDateKey(item.created_at);

    if (!groups.has(key)) {
      groups.set(key, []);
    }

    groups.get(key)?.push(item);
  });

  return Array.from(groups.entries()).map(
      ([key, items]) => ({
        key,
        label: getDateGroupLabel(key),
        fullDate: getFullDateLabel(key),
        items,
      }),
  );
});

async function fetchHistory(): Promise<void> {
  loading.value = true;
  loadError.value = "";

  try {
    const response = await getGeneratedResources(
        currentPage.value,
        pageSize.value,
    );

    if (response.data?.code !== 200) {
      throw new Error(
          response.data?.message ||
          "服务返回了异常结果",
      );
    }

    const responseItems =
        response.data.data?.items || [];
    const responseTotal =
        response.data.data?.total || 0;

    historyList.value = responseItems;
    total.value = responseTotal;

    const resolvedTotalPages = Math.max(
        1,
        Math.ceil(
            responseTotal / pageSize.value,
        ),
    );

    if (
        responseTotal > 0 &&
        currentPage.value > resolvedTotalPages
    ) {
      currentPage.value = resolvedTotalPages;
      await fetchHistory();
    }
  } catch (error) {
    console.error(
        "Failed to load resource history",
        error,
    );

    historyList.value = [];
    total.value = 0;
    loadError.value =
        "暂时无法获取资源生成记录，请稍后重新加载。";
  } finally {
    loading.value = false;
  }
}

function handleSizeChange(): void {
  currentPage.value = 1;
  void fetchHistory();
}

function handleCurrentChange(page: number): void {
  if (
      page < 1 ||
      page > totalPages.value ||
      page === currentPage.value
  ) {
    return;
  }

  currentPage.value = page;
  void fetchHistory();

  window.scrollTo({
    top: 0,
    behavior: "smooth",
  });
}

function normalizeStatus(
    status?: string | null,
): HistoryStatus {
  const normalized =
      status?.trim().toLowerCase() || "";

  if (
      normalized === "success" ||
      normalized === "completed"
  ) {
    return "success";
  }

  if (
      normalized === "running" ||
      normalized === "processing"
  ) {
    return "running";
  }

  if (
      normalized === "failed" ||
      normalized === "error"
  ) {
    return "failed";
  }

  return "waiting";
}

function getStatusText(
    status?: string | null,
): string {
  const normalized = normalizeStatus(status);

  if (normalized === "success") {
    return "已完成";
  }

  if (normalized === "running") {
    return "生成中";
  }

  if (normalized === "failed") {
    return "生成失败";
  }

  return "等待处理";
}

function getStatusDescription(
    status?: string | null,
): string {
  const normalized = normalizeStatus(status);

  if (normalized === "success") {
    return "多智能体资源已生成";
  }

  if (normalized === "running") {
    return "多智能体任务正在执行";
  }

  if (normalized === "failed") {
    return "本次生成任务未完成";
  }

  return "任务等待系统处理";
}

function getActionText(
    status?: string | null,
): string {
  const normalized = normalizeStatus(status);

  if (normalized === "success") {
    return "继续学习";
  }

  return "查看详情";
}

function getVisibleResourceTypes(
    item: GeneratedResourceHistoryItem,
): string[] {
  return (item.resource_types || []).slice(0, 5);
}

function getHiddenResourceCount(
    item: GeneratedResourceHistoryItem,
): number {
  return Math.max(
      0,
      (item.resource_types?.length || 0) - 5,
  );
}

function getDateKey(
    time?: string | null,
): string {
  if (!time) {
    return "unknown";
  }

  const date = new Date(time);

  if (Number.isNaN(date.getTime())) {
    return "unknown";
  }

  return [
    date.getFullYear(),
    String(date.getMonth() + 1).padStart(2, "0"),
    String(date.getDate()).padStart(2, "0"),
  ].join("-");
}

function getDateGroupLabel(
    dateKey: string,
): string {
  if (dateKey === "unknown") {
    return "日期未知";
  }

  const current = new Date();
  const target = new Date(`${dateKey}T00:00:00`);

  const today = new Date(
      current.getFullYear(),
      current.getMonth(),
      current.getDate(),
  );

  const difference = Math.round(
      (today.getTime() - target.getTime()) /
      (24 * 60 * 60 * 1000),
  );

  if (difference === 0) {
    return "今天";
  }

  if (difference === 1) {
    return "昨天";
  }

  if (difference >= 2 && difference <= 6) {
    return `${difference} 天前`;
  }

  return `${target.getMonth() + 1}月${target.getDate()}日`;
}

function getFullDateLabel(
    dateKey: string,
): string {
  if (dateKey === "unknown") {
    return "未记录生成日期";
  }

  const date = new Date(`${dateKey}T00:00:00`);

  return `${date.getFullYear()}年${
      date.getMonth() + 1
  }月${date.getDate()}日`;
}

function formatClock(
    time?: string | null,
): string {
  if (!time) {
    return "时间未知";
  }

  const date = new Date(time);

  if (Number.isNaN(date.getTime())) {
    return "时间未知";
  }

  return date.toLocaleTimeString("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

function goToDetail(id: number): void {
  router.push(`/resource-detail/${id}`);
}

onMounted(() => {
  void fetchHistory();
});
</script>

<style scoped>
.resource-history-page,
.resource-history-page * {
  box-sizing: border-box;
}

.resource-history-page {
  min-height: calc(100vh - 64px);
  color: #172033;
  background:
      linear-gradient(
          180deg,
          #f8fafc 0,
          #ffffff 260px
      );
}

.history-shell {
  width: min(1120px, 100%);
  margin: 0 auto;
  padding: 26px 28px 56px;
}

/* 页面标题 */

.history-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding-bottom: 20px;
  border-bottom: 1px solid #e1e7ef;
}

.header-main {
  display: flex;
  min-width: 0;
  align-items: flex-start;
  gap: 13px;
}

.back-button {
  display: grid;
  width: 36px;
  height: 36px;
  flex: 0 0 36px;
  place-items: center;
  margin-top: 1px;
  padding: 0;
  border: 1px solid #d7e0ea;
  border-radius: 8px;
  color: #65748a;
  background: #ffffff;
  cursor: pointer;
  transition:
      border-color 180ms ease,
      color 180ms ease,
      background-color 180ms ease;
}

.back-button:hover {
  border-color: #9eb0c6;
  color: #315c8a;
  background: #f6f9fc;
}

/*
 * 方向图标使用纯 CSS 绘制，避免项目中的全局 svg/path 样式
 * 覆盖 Phosphor 箭头图标，导致按钮中只剩一个小点。
 */
.direction-icon {
  position: relative;
  display: inline-block;
  width: 14px;
  height: 14px;
  flex: 0 0 14px;
  color: inherit;
}

.direction-icon::before {
  position: absolute;
  top: 50%;
  left: 2px;
  width: 10px;
  height: 2px;
  border-radius: 999px;
  background: currentColor;
  content: "";
  transform: translateY(-50%);
}

.direction-icon::after {
  position: absolute;
  top: 50%;
  width: 7px;
  height: 7px;
  content: "";
}

.direction-left::after {
  left: 2px;
  border-top: 2px solid currentColor;
  border-left: 2px solid currentColor;
  transform: translateY(-50%) rotate(-45deg);
}

.direction-right::after {
  right: 2px;
  border-top: 2px solid currentColor;
  border-right: 2px solid currentColor;
  transform: translateY(-50%) rotate(45deg);
}

.direction-icon-large {
  width: 17px;
  height: 17px;
  flex-basis: 17px;
}

.direction-icon-large::before {
  left: 2px;
  width: 13px;
}

.direction-icon-large::after {
  width: 8px;
  height: 8px;
}

.header-copy {
  min-width: 0;
}

.header-title-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 9px;
}

.header-title-row h1 {
  margin: 0;
  color: #172033;
  font-size: 22px;
  font-weight: 850;
  line-height: 1.25;
}

.history-total {
  display: inline-flex;
  height: 24px;
  align-items: center;
  padding: 0 8px;
  border: 1px solid #d5e2ef;
  border-radius: 6px;
  color: #53708e;
  background: #f4f8fc;
  font-size: 10px;
  font-weight: 750;
}

.header-copy p {
  margin: 6px 0 0;
  color: #748196;
  font-size: 12px;
  line-height: 1.55;
}

.create-resource-button,
.state-primary-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  border: 0;
  border-radius: 8px;
  color: #ffffff;
  background: #237d78;
  font: inherit;
  font-weight: 800;
  cursor: pointer;
  transition:
      background-color 180ms ease,
      transform 180ms ease,
      box-shadow 180ms ease;
}

.create-resource-button {
  height: 38px;
  flex: 0 0 auto;
  padding: 0 14px;
  font-size: 11px;
}

.create-resource-button:hover,
.state-primary-button:hover {
  background: #176f6a;
  box-shadow: 0 7px 18px rgba(35, 125, 120, 0.17);
  transform: translateY(-1px);
}

/* 工具栏 */

.history-toolbar {
  display: flex;
  min-height: 50px;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  margin-top: 15px;
  padding: 0 2px 14px;
  border-bottom: 1px solid #edf1f5;
}

.toolbar-summary {
  display: flex;
  align-items: center;
  gap: 8px;
}

.summary-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #4f73d9;
  box-shadow: 0 0 0 4px rgba(79, 115, 217, 0.1);
}

.summary-dot.loading {
  animation: status-pulse 1.5s ease-in-out infinite;
}

.toolbar-summary p {
  margin: 0;
  color: #68768b;
  font-size: 10px;
  font-weight: 700;
}

.page-size-control {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #7d899a;
  font-size: 10px;
  font-weight: 700;
}

.page-size-control select {
  height: 31px;
  padding: 0 28px 0 9px;
  border: 1px solid #d9e1ea;
  border-radius: 7px;
  outline: none;
  color: #43536a;
  background: #ffffff;
  font: inherit;
  font-size: 10px;
  font-weight: 700;
  cursor: pointer;
}

.page-size-control select:focus {
  border-color: #77aaa6;
  box-shadow: 0 0 0 3px rgba(35, 125, 120, 0.08);
}

.page-size-control select:disabled {
  cursor: not-allowed;
  opacity: 0.65;
}

/* 日期分组 */

.history-content {
  display: flex;
  flex-direction: column;
  gap: 26px;
  margin-top: 23px;
}

.history-group {
  min-width: 0;
}

.group-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 10px;
  padding: 0 2px;
}

.group-title {
  display: flex;
  align-items: center;
  gap: 9px;
}

.group-calendar-icon {
  width: 18px;
  height: 18px;
  color: #58708e;
}

.group-title h2 {
  margin: 0;
  color: #34445a;
  font-size: 13px;
  font-weight: 850;
}

.group-title p {
  margin: 2px 0 0;
  color: #8b96a6;
  font-size: 9px;
  font-weight: 650;
}

.group-header > span {
  color: #8793a4;
  font-size: 9px;
  font-weight: 700;
}

/* 历史列表 */

.history-list {
  overflow: hidden;
  border: 1px solid #dfe6ee;
  border-radius: 12px;
  background: #ffffff;
}

.history-item {
  position: relative;
  display: grid;
  grid-template-columns:
    54px
    minmax(0, 1fr)
    auto;
  gap: 14px;
  min-height: 132px;
  align-items: center;
  padding: 17px 18px;
  border-bottom: 1px solid #e8edf3;
  outline: none;
  background: #ffffff;
  cursor: pointer;
  transition:
      background-color 180ms ease,
      box-shadow 180ms ease;
}

.history-item:last-child {
  border-bottom: 0;
}

.history-item:hover,
.history-item:focus-visible {
  z-index: 2;
  background: #fafcfe;
  box-shadow: inset 3px 0 0 #5574c7;
}

.history-item.status-success:hover,
.history-item.status-success:focus-visible {
  box-shadow: inset 3px 0 0 #289078;
}

.history-item.status-failed:hover,
.history-item.status-failed:focus-visible {
  box-shadow: inset 3px 0 0 #ce5563;
}

.history-item.status-running:hover,
.history-item.status-running:focus-visible {
  box-shadow: inset 3px 0 0 #4f73d9;
}

/* 多智能体标识 */

.agent-output-column {
  display: flex;
  height: 100%;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.agent-cluster {
  position: relative;
  width: 42px;
  height: 42px;
  border: 1px solid #d6e0ec;
  border-radius: 11px;
  background: #f4f7fb;
}

.agent-dot {
  position: absolute;
  width: 17px;
  height: 17px;
  border: 2px solid #ffffff;
  border-radius: 50%;
}

.dot-primary {
  top: 6px;
  left: 6px;
  z-index: 3;
  background: #5b70c8;
}

.dot-secondary {
  top: 7px;
  right: 5px;
  z-index: 2;
  background: #33a092;
}

.dot-tertiary {
  right: 11px;
  bottom: 5px;
  z-index: 4;
  background: #d8914b;
}

.cluster-status-dot {
  position: absolute;
  right: -3px;
  bottom: -3px;
  z-index: 6;
  width: 11px;
  height: 11px;
  border: 3px solid #ffffff;
  border-radius: 50%;
  background: #a2adbb;
}

.cluster-success {
  border-color: #c9e4dc;
  background: #f1faf7;
}

.cluster-success .cluster-status-dot {
  background: #289078;
}

.cluster-running {
  border-color: #cbd8f4;
  background: #f3f6fd;
}

.cluster-running .cluster-status-dot {
  background: #4f73d9;
  animation: status-pulse 1.5s ease-in-out infinite;
}

.cluster-failed {
  border-color: #eccbd0;
  background: #fff5f6;
}

.cluster-failed .cluster-status-dot {
  background: #ce5563;
}

.agent-running-line {
  width: 1px;
  height: 24px;
  margin-top: 7px;
  overflow: hidden;
  background: #dce4ee;
}

.agent-running-line::after {
  content: "";
  display: block;
  width: 100%;
  height: 11px;
  background: #4f73d9;
  animation: running-line 1.4s linear infinite;
}

/* 记录主体 */

.history-item-main {
  min-width: 0;
}

.item-heading {
  display: flex;
  min-width: 0;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
}

.item-title-block {
  min-width: 0;
}

.item-category {
  display: block;
  color: #8190a3;
  font-size: 8px;
  font-weight: 850;
  letter-spacing: 0.09em;
}

.item-title-block h3 {
  display: -webkit-box;
  margin: 5px 0 0;
  overflow: hidden;
  color: #253449;
  font-size: 14px;
  font-weight: 800;
  line-height: 1.48;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.status-badge {
  display: inline-flex;
  height: 25px;
  flex: 0 0 auto;
  align-items: center;
  gap: 6px;
  padding: 0 8px;
  border: 1px solid #dce3eb;
  border-radius: 6px;
  color: #718096;
  background: #f8fafc;
  font-size: 9px;
  font-weight: 750;
  white-space: nowrap;
}

.status-badge i {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #9ca7b5;
}

.badge-success {
  border-color: #c6e3da;
  color: #18735f;
  background: #f2faf7;
}

.badge-success i {
  background: #289078;
}

.badge-running {
  border-color: #cbd7f2;
  color: #3f5ea8;
  background: #f3f6fd;
}

.badge-running i {
  background: #4f73d9;
  box-shadow: 0 0 0 4px rgba(79, 115, 217, 0.1);
  animation: status-pulse 1.5s ease-in-out infinite;
}

.badge-failed {
  border-color: #ecc9cf;
  color: #a63f4f;
  background: #fff4f5;
}

.badge-failed i {
  background: #ce5563;
}

.resource-summary {
  min-height: 26px;
  margin-top: 11px;
}

.resource-type-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.resource-type-tag {
  display: inline-flex;
  min-height: 24px;
  align-items: center;
  padding: 3px 8px;
  border: 1px solid #d9e0f5;
  border-radius: 6px;
  color: #555fa4;
  background: #f6f6ff;
  font-size: 9px;
  font-weight: 700;
}

.resource-type-tag:nth-child(2n) {
  border-color: #cde5e0;
  color: #187c70;
  background: #f1faf7;
}

.resource-type-tag:nth-child(3n) {
  border-color: #ebdcc8;
  color: #a96b2c;
  background: #fff9f0;
}

.more-tag {
  border-style: dashed;
  color: #718096;
  background: #fafbfc;
}

.resource-type-empty {
  color: #9aa5b4;
  font-size: 9px;
  font-weight: 650;
}

.item-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 7px;
  margin-top: 12px;
  color: #8490a1;
}

.item-meta > span {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 9px;
  font-weight: 650;
}

.item-meta > i {
  width: 3px;
  height: 3px;
  border-radius: 50%;
  background: #c0c8d2;
}

/* 操作入口 */

.item-action-column {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding-left: 12px;
}

.item-action-button {
  display: inline-flex;
  height: 34px;
  min-width: 104px;
  align-items: center;
  justify-content: center;
  gap: 7px;
  border: 1px solid #cfdae6;
  border-radius: 8px;
  color: #526984;
  background: #ffffff;
  font: inherit;
  font-size: 10px;
  font-weight: 800;
  cursor: pointer;
  transition:
      border-color 180ms ease,
      color 180ms ease,
      background-color 180ms ease,
      transform 180ms ease;
}

.item-action-button:hover {
  transform: translateX(2px);
}

.action-success {
  border-color: #b9dcd2;
  color: #18735f;
}

.action-success:hover {
  border-color: #62aa97;
  background: #f1faf7;
}

.action-running {
  border-color: #c3d0ef;
  color: #3f5ea8;
}

.action-running:hover {
  border-color: #8098d5;
  background: #f3f6fd;
}

.action-failed {
  border-color: #e6c0c7;
  color: #aa4555;
}

.action-failed:hover {
  border-color: #d57987;
  background: #fff5f6;
}

.action-waiting:hover {
  border-color: #9fb1c5;
  color: #3c536f;
  background: #f7f9fc;
}

/* 状态页面 */

.history-state {
  display: flex;
  min-height: 380px;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  margin-top: 23px;
  padding: 40px;
  border: 1px dashed #d8e1ea;
  border-radius: 12px;
  background: #ffffff;
  text-align: center;
}

.state-icon {
  display: grid;
  width: 54px;
  height: 54px;
  place-items: center;
  border: 1px solid #cde3df;
  border-radius: 14px;
  color: #237d78;
  background: #eff9f7;
}

.error-icon {
  border-color: #ebcbd1;
  color: #bd4d5e;
  background: #fff3f5;
}

.history-state h2 {
  margin: 16px 0 0;
  color: #2e3d52;
  font-size: 16px;
  font-weight: 850;
}

.history-state p {
  max-width: 470px;
  margin: 8px 0 0;
  color: #7a8798;
  font-size: 11px;
  line-height: 1.6;
}

.state-primary-button {
  height: 38px;
  margin-top: 19px;
  padding: 0 15px;
  font-size: 11px;
}

/* 加载骨架 */

.history-loading {
  display: flex;
  flex-direction: column;
  margin-top: 23px;
  overflow: hidden;
  border: 1px solid #e0e7ef;
  border-radius: 12px;
  background: #ffffff;
}

.history-skeleton {
  display: grid;
  grid-template-columns: 54px minmax(0, 1fr) 104px;
  gap: 14px;
  min-height: 128px;
  align-items: center;
  padding: 17px 18px;
  border-bottom: 1px solid #e9edf3;
}

.history-skeleton:last-child {
  border-bottom: 0;
}

.skeleton-agent,
.skeleton-title,
.skeleton-meta,
.skeleton-tags span,
.skeleton-action {
  overflow: hidden;
  background:
      linear-gradient(
          90deg,
          #edf1f5 20%,
          #f7f9fb 50%,
          #edf1f5 80%
      );
  background-size: 220% 100%;
  animation: skeleton-flow 1.5s linear infinite;
}

.skeleton-agent {
  width: 42px;
  height: 42px;
  border-radius: 11px;
}

.skeleton-content {
  min-width: 0;
}

.skeleton-title {
  width: min(480px, 72%);
  height: 16px;
  border-radius: 5px;
}

.skeleton-meta {
  width: min(290px, 48%);
  height: 10px;
  margin-top: 10px;
  border-radius: 4px;
}

.skeleton-tags {
  display: flex;
  gap: 6px;
  margin-top: 13px;
}

.skeleton-tags span {
  width: 62px;
  height: 23px;
  border-radius: 6px;
}

.skeleton-action {
  width: 104px;
  height: 34px;
  border-radius: 8px;
}

/* 分页 */

.history-pagination {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 22px;
  margin-top: 28px;
  padding-top: 18px;
  border-top: 1px solid #e3e9f0;
}

.pagination-info {
  display: flex;
  align-items: baseline;
  gap: 5px;
  color: #7b8798;
}

.pagination-info strong {
  color: #33445a;
  font-size: 13px;
  font-weight: 850;
}

.pagination-info span {
  font-size: 10px;
  font-weight: 650;
}

.pagination-controls {
  display: flex;
  align-items: center;
  gap: 10px;
}

.pagination-button {
  display: inline-flex;
  height: 33px;
  align-items: center;
  gap: 6px;
  padding: 0 10px;
  border: 1px solid #d7e0e9;
  border-radius: 7px;
  color: #596a80;
  background: #ffffff;
  font: inherit;
  font-size: 10px;
  font-weight: 750;
  cursor: pointer;
  transition:
      border-color 180ms ease,
      color 180ms ease,
      background-color 180ms ease;
}

.pagination-button:hover:not(:disabled) {
  border-color: #9fb2c7;
  color: #345372;
  background: #f7f9fc;
}

.pagination-button:disabled {
  color: #a6afba;
  background: #f7f8fa;
  cursor: not-allowed;
  opacity: 0.7;
}

.page-indicator {
  display: flex;
  min-width: 92px;
  align-items: baseline;
  justify-content: center;
  gap: 4px;
  color: #7e8a9a;
  font-size: 10px;
}

.page-indicator strong {
  color: #34465d;
  font-size: 13px;
  font-weight: 850;
}

/* 动画 */

@keyframes status-pulse {
  0%,
  100% {
    opacity: 0.72;
    transform: scale(0.92);
  }

  50% {
    opacity: 1;
    transform: scale(1.16);
  }
}

@keyframes running-line {
  from {
    transform: translateY(-14px);
  }

  to {
    transform: translateY(30px);
  }
}

@keyframes skeleton-flow {
  to {
    background-position: -220% 0;
  }
}

/* 响应式 */

@media (max-width: 760px) {
  .history-shell {
    padding: 18px 13px 38px;
  }

  .history-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .create-resource-button {
    width: 100%;
  }

  .history-toolbar {
    align-items: flex-start;
    flex-direction: column;
  }

  .history-item {
    grid-template-columns: 45px minmax(0, 1fr);
    min-height: 0;
    padding: 15px 13px;
  }

  .agent-cluster {
    width: 38px;
    height: 38px;
  }

  .agent-dot {
    width: 16px;
    height: 16px;
  }

  .item-heading {
    flex-direction: column;
    gap: 8px;
  }

  .status-badge {
    align-self: flex-start;
  }

  .item-action-column {
    grid-column: 2;
    justify-content: flex-start;
    padding: 2px 0 0;
  }

  .item-action-button {
    min-width: 112px;
  }

  .history-skeleton {
    grid-template-columns: 45px minmax(0, 1fr);
  }

  .skeleton-action {
    grid-column: 2;
  }

  .history-pagination {
    align-items: stretch;
    flex-direction: column;
  }

  .pagination-controls {
    justify-content: space-between;
  }
}

@media (max-width: 480px) {
  .header-title-row h1 {
    font-size: 20px;
  }

  .history-item {
    grid-template-columns: minmax(0, 1fr);
  }

  .agent-output-column {
    display: none;
  }

  .item-action-column {
    grid-column: auto;
  }

  .item-action-button {
    width: 100%;
  }

  .item-meta > i {
    display: none;
  }

  .item-meta {
    align-items: flex-start;
    flex-direction: column;
    gap: 5px;
  }

  .pagination-controls {
    display: grid;
    grid-template-columns:
      minmax(0, 1fr)
      auto
      minmax(0, 1fr);
  }

  .pagination-button {
    justify-content: center;
  }

  .history-skeleton {
    grid-template-columns: minmax(0, 1fr);
  }

  .skeleton-agent {
    display: none;
  }

  .skeleton-action {
    grid-column: auto;
  }
}

@media (prefers-reduced-motion: reduce) {
  .resource-history-page *,
  .resource-history-page *::before,
  .resource-history-page *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    scroll-behavior: auto !important;
    transition-duration: 0.01ms !important;
  }
}
</style>