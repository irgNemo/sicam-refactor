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
                {{ overlayLabelDisplayName(label.label) }}
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
  methods: {
    overlayLabelDisplayName(label) {
      const displayNames = {
        membrana: "Membranas",
        nucleo: "Núcleos",
        micronucleo: "Micronúcleos",
      };

      return displayNames[label] || label;
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
  padding: 12px;
  text-align: center;
  text-transform: uppercase;
}

.obj-table tbody td {
  border-bottom: 1px solid #f0f0f0;
  padding: 12px;
  text-align: center;
}

.obj-row {
  transition: background 0.2s ease;
}

.obj-row:hover {
  background: #f8f9fa;
}

.checkbox-custom {
  accent-color: #667eea;
  cursor: pointer;
  height: 18px;
  width: 18px;
}

.obj-type {
  align-items: center;
  display: flex;
  font-weight: 500;
  gap: 8px;
  justify-content: center;
}

.obj-icon {
  font-size: 16px;
}

.empty-normalized {
  color: #777;
  font-size: 11px;
}

@media (max-width: 1439px) and (min-width: 1024px) {
  .card-header-simple {
    padding: 10px 14px;
  }

  .objects-card {
    min-height: 150px;
  }

  .objects-table-wrapper {
    padding: 12px;
  }
}

@media (max-width: 1023px) {
  .objects-table-wrapper {
    padding: 12px;
  }
}
</style>
