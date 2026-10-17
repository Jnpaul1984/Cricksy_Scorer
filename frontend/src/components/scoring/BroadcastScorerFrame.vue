<template>
  <div class="broadcast-layout" data-testid="broadcast-scorer-frame">
    <slot />
  </div>
</template>

<style scoped>
.broadcast-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--color-bg, #121212);
  color: var(--color-text, #e0e0e0);
}
</style>
