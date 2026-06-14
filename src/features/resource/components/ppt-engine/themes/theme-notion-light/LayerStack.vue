<template>
  <div class="notion-light-slide notion-layer-stack">
    <div class="notion-page">
      <h2 class="slide-title">{{ data.title }}</h2>
      
      <div class="content-body">
        <div class="blocks-container">
          <div 
            v-for="(layer, index) in data.layers" 
            :key="index"
            class="notion-block"
          >
            <div class="block-drag-handle">⋮⋮</div>
            <div class="block-content">
              <div class="block-header">
                <span class="toggle-triangle">▼</span>
                <span class="layer-name">{{ layer.level_name }}</span>
              </div>
              <div class="block-inner">
                <p class="layer-desc">{{ layer.description }}</p>
                <div class="props-table" v-if="layer.protocols || layer.components">
                  <div class="prop-row" v-if="layer.protocols && layer.protocols.length">
                    <div class="prop-col-name">Protocols</div>
                    <div class="prop-col-val">
                      <span class="inline-tag" v-for="tag in layer.protocols" :key="tag">{{ tag }}</span>
                    </div>
                  </div>
                  <div class="prop-row" v-if="layer.components && layer.components.length">
                    <div class="prop-col-name">Components</div>
                    <div class="prop-col-val">
                      <span class="inline-tag" v-for="tag in layer.components" :key="tag">{{ tag }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { LayerStackData } from '../../types/ppt';

defineProps<{
  data: LayerStackData
}>();
</script>

<style scoped>
.notion-light-slide {
  width: 100%;
  height: 100%;
  background: #FFFFFF;
  display: flex;
  justify-content: center;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, "Apple Color Emoji", Arial, sans-serif, "Segoe UI Emoji", "Segoe UI Symbol";
  color: #37352f;
  padding: 80px;
  box-sizing: border-box;
}

.notion-page {
  width: 100%;
  max-width: 900px;
  display: flex;
  flex-direction: column;
}

.slide-title {
  font-size: 40px;
  font-weight: 700;
  margin: 0 0 30px 0;
}

.content-body {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.blocks-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.notion-block {
  display: flex;
  gap: 4px;
}

.block-drag-handle {
  width: 24px;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding-top: 4px;
  color: rgba(55, 53, 47, 0.3);
  font-size: 14px;
  cursor: grab;
}

.block-content {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.block-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 20px;
  font-weight: 600;
  margin-bottom: 8px;
}

.toggle-triangle {
  font-size: 12px;
  color: rgba(55, 53, 47, 0.4);
}

.layer-name {
  color: #37352f;
}

.block-inner {
  padding-left: 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.layer-desc {
  margin: 0;
  font-size: 16px;
  line-height: 1.6;
  color: rgba(55, 53, 47, 0.8);
}

.props-table {
  display: flex;
  flex-direction: column;
  border: 1px solid rgba(55, 53, 47, 0.09);
  border-radius: 4px;
  overflow: hidden;
}

.prop-row {
  display: flex;
  border-bottom: 1px solid rgba(55, 53, 47, 0.09);
}

.prop-row:last-child {
  border-bottom: none;
}

.prop-col-name {
  width: 150px;
  padding: 8px 12px;
  background: rgba(247, 246, 243, 1);
  color: rgba(55, 53, 47, 0.65);
  font-size: 14px;
  font-weight: 500;
  border-right: 1px solid rgba(55, 53, 47, 0.09);
}

.prop-col-val {
  flex: 1;
  padding: 8px 12px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.inline-tag {
  background: rgba(227, 226, 224, 0.5);
  color: #37352f;
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 13px;
}
</style>
