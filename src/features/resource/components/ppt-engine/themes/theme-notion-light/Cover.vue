<template>
  <div class="notion-light-slide notion-cover">
    <div class="notion-page">
      <div class="page-icon">📄</div>
      <h1 class="main-title">{{ data.main_title }}</h1>
      <h2 class="sub-title" v-if="data.sub_title">{{ data.sub_title }}</h2>
      
      <div class="meta-section">
        <div class="property-row" v-if="data.lecturer">
          <div class="prop-name">👤 Author</div>
          <div class="prop-value user-tag">{{ data.lecturer }}</div>
        </div>
        <div class="property-row" v-if="data.date">
          <div class="prop-name">📅 Date</div>
          <div class="prop-value">{{ data.date }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { CoverData } from '../../types/ppt';

defineProps<{
  data: CoverData
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
  padding-top: 100px;
}

.page-icon {
  font-size: 78px;
  margin-bottom: 24px;
}

.main-title {
  font-size: 54px;
  font-weight: 700;
  margin: 0 0 16px 0;
  line-height: 1.2;
}

.sub-title {
  font-size: 24px;
  color: rgba(55, 53, 47, 0.65);
  font-weight: 500;
  margin: 0 0 40px 0;
}

.meta-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
  border-top: 1px solid rgba(55, 53, 47, 0.09);
  padding-top: 20px;
}

.property-row {
  display: flex;
  align-items: center;
  gap: 20px;
  font-size: 16px;
}

.prop-name {
  color: rgba(55, 53, 47, 0.65);
  width: 120px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.prop-value {
  color: #37352f;
}

.user-tag {
  background: rgba(235, 236, 237, 1);
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 14px;
  font-weight: 500;
}
</style>
