<template>
  <div class="image-controls">
    <button
      class="control-btn"
      title="Aumentar zoom"
      aria-label="Aumentar zoom"
      @click="$emit('zoom-in')"
    >
      <span>＋</span> Zoom {{ Math.round(imageZoom * 100) }}%
    </button>
    <button
      class="control-btn"
      title="Reducir zoom"
      aria-label="Reducir zoom"
      @click="$emit('zoom-out')"
    >
      <span>－</span> Zoom
    </button>
    <button
      class="control-btn"
      title="Rotar imagen"
      aria-label="Rotar imagen"
      @click="$emit('rotate')"
    >
      <span>↻</span> Rotar
    </button>
    <button
      class="control-btn"
      title="Ajustar vista"
      aria-label="Ajustar vista"
      @click="$emit('reset')"
    >
      <span>⊟</span> Ajustar
    </button>
  </div>
</template>

<script>
export default {
  name: "SegmentationImageControls",
  emits: ["zoom-in", "zoom-out", "rotate", "reset"],
  props: {
    imageZoom: {
      type: Number,
      required: true,
    },
  },
};
</script>

<style scoped>
.image-controls {
  display: flex;
  gap: 8px;
}

.control-btn {
  align-items: center;
  background: white;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  cursor: pointer;
  display: flex;
  flex: 1;
  font-size: 12px;
  font-weight: 500;
  gap: 6px;
  justify-content: center;
  padding: 8px;
  transition: all 0.2s ease;
}

.control-btn:hover {
  background: #e3f2fd;
  border-color: #1e88e5;
}

.control-btn:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}
</style>
