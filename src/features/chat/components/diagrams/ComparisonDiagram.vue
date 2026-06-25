<template>
  <div class="comparison-diagram">
    <!-- Header Entities -->
    <div class="entities-container">
      <div class="entity-card left">
        <div class="entity-glow"></div>
        <div class="entity-content">
          <span class="entity-core">{{ payload.left_entity.core_label }}</span>
          <h4 class="entity-name">{{ payload.left_entity.name }}</h4>
          <p class="entity-desc">{{ payload.left_entity.short_desc }}</p>
        </div>
      </div>
      
      <div class="vs-badge-container">
        <div class="vs-pulse"></div>
        <div class="vs-badge">VS</div>
      </div>
      
      <div class="entity-card right">
        <div class="entity-glow"></div>
        <div class="entity-content">
          <span class="entity-core">{{ payload.right_entity.core_label }}</span>
          <h4 class="entity-name">{{ payload.right_entity.name }}</h4>
          <p class="entity-desc">{{ payload.right_entity.short_desc }}</p>
        </div>
      </div>
    </div>

    <!-- Dimensions Comparison -->
    <div class="dimensions-list">
      <div v-for="dim in payload.dimensions" :key="dim.name" class="dimension-row">
        <div class="dim-label">{{ dim.name }}</div>
        <div class="dim-bars">
          <div class="dim-side left-side">
            <div class="dim-value-box left-val">{{ dim.left }}</div>
          </div>
          <div class="dim-divider"></div>
          <div class="dim-side right-side">
            <div class="dim-value-box right-val">{{ dim.right }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Visual Summary Ribbon -->
    <div class="summary-ribbon">
      <div class="ribbon-endpoint left-endpoint">
        <span class="keyword">{{ payload.visual_summary.left_keyword }}</span>
      </div>
      <div class="ribbon-line">
        <svg preserveAspectRatio="none" viewBox="0 0 100 20" class="ribbon-svg">
          <path d="M0,10 Q50,20 100,10" fill="none" stroke="url(#ribbon-grad)" stroke-width="2" stroke-dasharray="4 4" />
          <defs>
            <linearGradient id="ribbon-grad" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stop-color="#3b82f6" />
              <stop offset="50%" stop-color="#8b5cf6" />
              <stop offset="100%" stop-color="#10b981" />
            </linearGradient>
          </defs>
        </svg>
        <span class="center-conclusion">{{ payload.visual_summary.center_conclusion }}</span>
      </div>
      <div class="ribbon-endpoint right-endpoint">
        <span class="keyword">{{ payload.visual_summary.right_keyword }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { ComparisonPayload } from '@/features/chat/types/chat'

defineProps<{
  payload: ComparisonPayload
}>()
</script>

<style scoped>
.comparison-diagram {
  display: flex;
  flex-direction: column;
  gap: 24px;
  padding: 8px;
  background: linear-gradient(180deg, rgba(255,255,255,0) 0%, rgba(248,250,252,0.5) 100%);
  border-radius: 16px;
}

/* Entities Section */
.entities-container {
  display: flex;
  align-items: center;
  justify-content: space-between;
  position: relative;
  gap: 16px;
}

.entity-card {
  flex: 1;
  position: relative;
  border-radius: 16px;
  padding: 20px 16px;
  text-align: center;
  overflow: hidden;
  box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05);
  transition: transform 0.3s ease;
  z-index: 1;
}

.entity-card:hover {
  transform: translateY(-4px);
}

.entity-glow {
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: radial-gradient(circle at center, rgba(255,255,255,0.8) 0%, rgba(255,255,255,0) 60%);
  z-index: 0;
  pointer-events: none;
}

.entity-content {
  position: relative;
  z-index: 1;
}

.entity-card.left {
  background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
  border: 1px solid #bfdbfe;
}
.entity-card.left .entity-core { color: var(--color-info); background: #bfdbfe; }
.entity-card.left .entity-name { color: #1e3a8a; }

.entity-card.right {
  background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
  border: 1px solid #bbf7d0;
}
.entity-card.right .entity-core { color: #16a34a; background: #bbf7d0; }
.entity-card.right .entity-name { color: #14532d; }

.entity-core {
  display: inline-block;
  font-size: 11px;
  font-weight: 800;
  padding: 4px 10px;
  border-radius: 999px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 8px;
}

.entity-name {
  margin: 0 0 8px 0;
  font-size: 20px;
  font-weight: 800;
}

.entity-desc {
  margin: 0;
  font-size: 13px;
  color: var(--color-text-secondary);
  line-height: 1.5;
}

/* VS Badge */
.vs-badge-container {
  position: relative;
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  z-index: 2;
}

.vs-pulse {
  position: absolute;
  inset: -8px;
  border-radius: 50%;
  background: radial-gradient(circle, #fde68a 0%, rgba(253, 230, 138, 0) 70%);
  animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(1.1); }
}

.vs-badge {
  position: relative;
  width: 40px;
  height: 40px;
  background: linear-gradient(135deg, var(--color-warning) 0%, #d97706 100%);
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 900;
  font-style: italic;
  box-shadow: 0 4px 10px rgba(217, 119, 6, 0.3), inset 0 2px 4px rgba(255, 255, 255, 0.3);
  border: 2px solid #fff;
  text-shadow: 0 1px 2px rgba(0,0,0,0.2);
}

/* Dimensions Section */
.dimensions-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.dimension-row {
  background: #fff;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  padding: 12px 16px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.02);
  transition: box-shadow 0.2s ease, border-color 0.2s ease;
}

.dimension-row:hover {
  box-shadow: 0 6px 12px rgba(0,0,0,0.05);
  border-color: var(--color-border-hover);
}

.dim-label {
  font-size: 13px;
  font-weight: 700;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 10px;
  text-align: center;
}

.dim-bars {
  display: flex;
  align-items: stretch;
  gap: 16px;
}

.dim-side {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.dim-value-box {
  padding: 10px 14px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  line-height: 1.4;
  height: 100%;
  display: flex;
  align-items: center;
}

.left-val {
  background: rgba(239, 246, 255, 0.5);
  color: #1e40af;
  border-left: 4px solid #3b82f6;
}

.right-val {
  background: rgba(240, 253, 244, 0.5);
  color: #166534;
  border-left: 4px solid var(--color-success);
}

.dim-divider {
  width: 1px;
  background: var(--color-border);
  align-self: stretch;
}

/* Visual Summary Ribbon */
.summary-ribbon {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 8px;
  position: relative;
  padding: 0 10px;
}

.ribbon-endpoint {
  z-index: 2;
}

.keyword {
  display: inline-block;
  padding: 6px 16px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 800;
  box-shadow: 0 4px 6px rgba(0,0,0,0.05);
}

.left-endpoint .keyword {
  background: #3b82f6;
  color: white;
}

.right-endpoint .keyword {
  background: var(--color-success);
  color: white;
}

.ribbon-line {
  flex: 1;
  position: relative;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.ribbon-svg {
  position: absolute;
  top: 0;
  left: -10px;
  width: calc(100% + 20px);
  height: 100%;
  z-index: 0;
}

.center-conclusion {
  position: relative;
  z-index: 2;
  background: white;
  padding: 6px 16px;
  border-radius: 999px;
  font-size: 14px;
  font-weight: 700;
  color: var(--color-text);
  border: 1px solid var(--color-border);
  box-shadow: 0 4px 10px rgba(0,0,0,0.05);
}

@media (max-width: 640px) {
  .entities-container {
    flex-direction: column;
  }
  .dim-bars {
    flex-direction: column;
    gap: 8px;
  }
  .dim-divider {
    height: 1px;
    width: 100%;
  }
  .summary-ribbon {
    flex-direction: column;
    gap: 16px;
  }
  .ribbon-svg { display: none; }
}
</style>
