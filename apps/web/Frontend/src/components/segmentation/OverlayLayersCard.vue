<template>
  <div class="card objects-card">
    <div class="card-header-simple">
      <h3>Capas visibles</h3>
      <span class="objects-count">{{ labels.length }} tipos</span>
    </div>

    <div class="objects-layout">
      <div class="objects-table-wrapper">
        <table class="obj-table">
          <thead>
            <tr>
              <th>Visible</th>
              <th>Capa</th>
            </tr>
          </thead>
          <tbody v-if="labels.length">
            <tr
              v-for="label in labels"
              :key="label.label"
              class="obj-row"
            >
              <td>
                <input
                  type="checkbox"
                  class="checkbox-custom"
                  :checked="label.visible"
                  @change="$emit('change-visibility', label.label, $event.target.checked)"
                />
              </td>
              <td class="obj-type">
                <span
                  class="obj-icon"
                  :style="{ color: label.stroke }"
                >●</span>
                {{ label.displayName || label.label }}
              </td>
            </tr>
          </tbody>
          <tbody v-else>
            <tr class="obj-row">
              <td colspan="2" class="empty-normalized">
                Sin objetos dibujables
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
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
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  height: auto;
  min-height: 170px;
}

.card-header-simple {
  align-items: center;
  background: linear-gradient(to right, #fafbfc, #ffffff);
  border-bottom: 2px solid #f0f0f0;
  display: flex;
  flex-shrink: 0;
  justify-content: space-between;
  padding: 10px 20px;
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

.objects-layout {
  display: block;
  flex: 1;
  min-height: 0;
  min-width: 0;
  overflow: visible;
}

.objects-table-wrapper {
  min-height: 0;
  min-width: 0;
  overflow-y: auto;
  padding: 16px;
}

.obj-table {
  border-collapse: separate;
  border-spacing: 0;
  font-size: 13px;
  width: 100%;
}

.obj-table thead th {
  background: #f8f9fa;
  border-bottom: 2px solid #e0e0e0;
  color: #666;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.5px;
  padding: 8px 12px;
  position: sticky;
  text-align: left;
  text-transform: uppercase;
  top: 0;
}

.obj-row {
  transition: background 0.2s ease;
}

.obj-row:hover {
  background: #f8f9fa;
}

.obj-table td {
  border-bottom: 1px solid #f0f0f0;
  padding: 10px 12px;
}

.checkbox-custom {
  cursor: pointer;
  height: 16px;
  width: 16px;
}

.obj-type {
  color: #2c3e50;
  font-weight: 500;
}

.obj-icon {
  display: inline-block;
  font-size: 14px;
  line-height: 1;
  margin-right: 6px;
  text-align: center;
  width: 14px;
}

.empty-normalized {
  color: #64748b;
  font-size: 13px;
  padding: 16px !important;
  text-align: center;
}

@media (max-width: 1439px) {
  .card-header-simple {
    padding: 8px 14px;
  }

  .objects-table-wrapper {
    padding: 12px;
  }
}
</style>
