<template>
  <div class="count-summary">
    <div class="data-header">
      <h4>Resumen de Conteo</h4>
    </div>

    <table class="data-table">
      <thead>
        <tr>
          <th>Estructura</th>
          <th>Cantidad</th>
        </tr>
      </thead>

      <tbody v-if="summary">
        <tr class="data-row membranas">
          <td>
            <span
              class="structure-dot"
              :style="{ color: colorForLabel('membrana').stroke }"
            >●</span>
            Membranas
          </td>
          <td class="count">{{ summary.membranas }}</td>
        </tr>
        <tr class="data-row nucleos">
          <td>
            <span
              class="structure-dot"
              :style="{ color: colorForLabel('nucleo').stroke }"
            >●</span>
            Núcleos
          </td>
          <td class="count">{{ summary.nucleos }}</td>
        </tr>
        <tr class="data-row micronucleos highlight">
          <td>
            <span
              class="structure-dot"
              :style="{ color: colorForLabel('micronucleo').stroke }"
            >●</span>
            Micronúcleos
          </td>
          <td class="count">{{ summary.micronucleos }}</td>
        </tr>
        <tr class="data-row total">
          <td>
            <span class="structure-total-symbol">Σ</span>
            Total
          </td>
          <td class="count">{{ summary.total }}</td>
        </tr>
      </tbody>

      <tbody v-else>
        <tr>
          <td colspan="2" class="no-data">
            <div class="no-data-icon">📊</div>
            <span>Sin resultados disponibles</span>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script>
export default {
  name: "SegmentationCountSummary",
  props: {
    summary: {
      type: Object,
      default: null,
    },
    palette: {
      type: Object,
      required: true,
    },
  },
  methods: {
    colorForLabel(label) {
      return this.palette[label] || { stroke: "#64748b" };
    },
  },
};
</script>

<style scoped>
.data-header {
  border-bottom: 2px solid #f0f0f0;
  padding-bottom: 8px;
}

.data-header h4 {
  color: #2c3e50;
  font-size: 14px;
  font-weight: 600;
  margin: 0;
}

.data-table {
  border-collapse: separate;
  border-spacing: 0;
  font-size: 13px;
  width: 100%;
}

.data-table thead th {
  background: #f8f9fa;
  border-bottom: 2px solid #e0e0e0;
  color: #666;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.5px;
  padding: 12px;
  text-align: left;
  text-transform: uppercase;
}

.data-table tbody td {
  border-bottom: 1px solid #f0f0f0;
  padding: 14px 12px;
}

.data-row {
  transition: background 0.2s ease;
}

.data-row:hover {
  background: #f8f9fa;
}

.data-row.highlight {
  background: #fff3e0;
}

.data-row.highlight:hover {
  background: #ffe0b2;
}

.structure-dot,
.structure-total-symbol {
  display: inline-block;
  margin-right: 8px;
  text-align: center;
  width: 14px;
}

.structure-dot {
  font-size: 16px;
  line-height: 1;
}

.structure-total-symbol {
  color: #2c3e50;
  font-size: 13px;
  font-weight: 700;
}

.count {
  color: #2c3e50;
  font-size: 16px;
  font-weight: 700;
  text-align: right;
}

.no-data {
  color: #999;
  padding: 40px 20px !important;
  text-align: center;
}

.no-data-icon {
  font-size: 48px;
  margin-bottom: 12px;
  opacity: 0.3;
}
</style>
