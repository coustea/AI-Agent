<template>
  <div class="logic-blue-slide logic-blue-grid">
    <h2 class="slide-title">{{ data.title }}</h2>
    <div class="cards-container">
      <div class="card" v-for="(card, index) in data.cards" :key="index">
        <h3 class="card-title">{{ card.title }}</h3>
        <p class="card-desc">{{ card.desc }}</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { GridCardsData } from '../../../types/ppt';

defineProps<{
  data: GridCardsData
}>();
</script>

<style scoped>
.logic-blue-slide {
  width: 100%;
  height: 100%;
  padding: 80px 100px;
  background-color: #F8FAFC;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
}

.slide-title {
  font-size: 56px;
  color: #1E293B;
  margin-bottom: 60px;
  border-left: 10px solid #2563EB;
  padding-left: 24px;
  font-weight: 700;
}

.cards-container {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 40px;
  flex: 1;
}

.card {
  background: #FFFFFF;
  border-radius: 16px;
  padding: 40px;
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05);
  border-top: 6px solid #3B82F6;
}

.card-title {
  font-size: 32px;
  color: #0F172A;
  margin-bottom: 20px;
  font-weight: 600;
}

.card-desc {
  font-size: 24px;
  color: #475569;
  line-height: 1.6;
}
</style>
