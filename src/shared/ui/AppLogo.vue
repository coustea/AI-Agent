<template>
  <svg 
    viewBox="0 0 100 100" 
    class="app-logo-svg" 
    xmlns="http://www.w3.org/2000/svg"
  >
    <!-- Geometric Orbit Lines -->
    <circle cx="50" cy="50" r="32" fill="none" stroke="currentColor" stroke-width="1.5" stroke-dasharray="2 3" opacity="0.4" />
    <ellipse cx="50" cy="50" rx="42" ry="18" fill="none" stroke="currentColor" stroke-width="1.2" transform="rotate(-30 50 50)" opacity="0.6" />
    <ellipse cx="50" cy="50" rx="42" ry="18" fill="none" stroke="currentColor" stroke-width="1.2" transform="rotate(30 50 50)" opacity="0.6" />
    
    <!-- Outer crossing scaffold lines -->
    <line x1="28" y1="20" x2="72" y2="80" stroke="currentColor" stroke-width="1.5" opacity="0.3" />
    <line x1="72" y1="20" x2="28" y2="80" stroke="currentColor" stroke-width="1.5" opacity="0.3" />

    <!-- Main geometric X shape -->
    <path 
      d="M26 24 H36 L50 45 L64 24 H74 L55 50 L74 76 H64 L50 55 L36 76 H26 L45 50 Z" 
      fill="currentColor" 
    />
    
    <!-- Accent node dots on orbits -->
    <circle cx="50" cy="18" r="3.5" fill="var(--color-primary, #46B8B4)" />
    <circle cx="14" cy="50" r="2.5" fill="currentColor" />
    <circle cx="86" cy="50" r="2.5" fill="currentColor" />
    <circle cx="73" cy="37" r="3" fill="var(--color-primary, #46B8B4)" />
    <circle cx="27" cy="63" r="3" fill="currentColor" />
  </svg>
</template>

<style scoped>
.app-logo-svg {
  width: 100%;
  height: 100%;
  display: block;
}
</style>
