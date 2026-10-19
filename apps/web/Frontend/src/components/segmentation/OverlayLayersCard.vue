<template>
  <div class="card objects-card">
    <div class="card-header-simple">
      <h3>Capas visibles</h3>
      <span class="objects-count">{{ labels.length }} tipos</span>
    </div>

    <div v-if="labels.length" class="layer-options">
      <label
        v-for="label in labels"
        :key="label.label"
        class="layer-option"
      >
        <input
          type="checkbox"
          class="checkbox-custom"
          :checked="label.visible"
          @change="$emit('change-visibility', label.label, $event.target.checked)"
        />
        <span class="obj-icon" :style="{ color: label.stroke }" aria-hidden="true">●</span>
        <span>{{ label.displayName || label.label }}</span>
      </label>
    </div>
    <div v-else class="empty-normalized">Sin objetos dibujables</div>
  </div>
</template>

<script>
export default {
  name: "OverlayLayersCard",
  emits: ["change-visibility"],
  props: {
    labels: {
      type: Array,
      required: true,
    },
  },
};
</script>

<style scoped>
.card {
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.objects-card {
  flex-shrink: 0;
  min-width: 0;
}

.card-header-simple {
  align-items: center;
  background: linear-gradient(to right, #fafbfc, #ffffff);
  border-bottom: 2px solid #f0f0f0;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: space-between;
  padding: 8px 14px;
}

.card-header-simple h3 {
  color: #2c3e50;
  font-size: 16px;
  font-weight: 600;
  margin: 0;
}

.objects-count {
  background: #f0f4f8;
  border-radius: 12px;
  color: #999;
  font-size: 12px;
  padding: 4px 12px;
}

.layer-options {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 12px;
  padding: 8px 14px;
}

.layer-option {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  max-width: 100%;
  padding: 6px 0;
  color: #2c3e50;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  overflow-wrap: anywhere;
}

.layer-option:hover {
  background: #f8f9fa;
}

.checkbox-custom {
  cursor: pointer;
  flex-shrink: 0;
  height: 16px;
  width: 16px;
  margin: 0;
}

.checkbox-custom:focus-visible {
  outline: 2px solid #2c3e50;
  outline-offset: 2px;
}

.obj-icon {
  flex-shrink: 0;
  font-size: 14px;
  line-height: 1;
  text-align: center;
  width: 14px;
}

.empty-normalized {
  color: #64748b;
  font-size: 13px;
  padding: 12px 14px;
  text-align: center;
}
</style>
