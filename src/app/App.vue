<template>
  <router-view />
  <Toast position="top-center" />
  <ConfirmDialog />
</template>

<script setup lang="ts">
import Toast from 'primevue/toast'
import ConfirmDialog from 'primevue/confirmdialog'
</script>

<style>
</style>
