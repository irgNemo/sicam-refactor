<template>
  <section class="characterization-panel">
    <div class="panel-header">
      <div>
        <h3>Resultado de caracterizacion</h3>
        <p>{{ panelSubtitle }}</p>
      </div>
      <span
        v-if="statusBadge"
        class="status-badge"
        :class="statusBadge.className"
      >
        {{ statusBadge.text }}
      </span>
    </div>

    <div
      v-if="!selectedSegmentationResult"
      class="empty-state"
    >
      <strong>No hay una segmentacion completada disponible para caracterizar.</strong>
      <span>Primero segmenta la muestra.</span>
      <button
        class="btn-primary"
        disabled
      >
        Primero segmenta la muestra
      </button>
    </div>

    <template v-else>
      <div
        v-if="characterizationsLoading"
        class="status-card neutral"
      >
        Cargando caracterizacion...
      </div>

      <div
        v-else-if="characterizationsError"
        class="status-card error"
      >
        {{ characterizationsError }}
      </div>

      <div
        v-if="characterizeError"
        class="status-card error"
      >
        {{ characterizeError }}
      </div>

      <div
        v-if="characterizeMessage"
        class="status-card success"
      >
        {{ characterizeMessage }}
      </div>

      <div
        v-if="showStaleNotice"
        class="status-card warning"
      >
        Caracterizacion desactualizada.
      </div>

      <div
        v-else-if="showNoCurrentNotice"
        class="status-card neutral"
      >
        Sin caracterizacion vigente.
      </div>

      <button
        class="btn-primary"
        :disabled="characterizeLoading || characterizationsLoading"
        @click="$emit('characterize')"
      >
        {{ characterizeLoading ? "Caracterizando..." : actionLabel }}
      </button>

      <div
        v-if="currentCharacterization"
        class="metrics-grid"
      >
        <div class="metric-card">
          <span>Fuente</span>
          <strong>{{ sourceDisplay }}</strong>
        </div>
        <div class="metric-card">
          <span>Tipo</span>
          <strong>{{ resultJson.sample_type || sampleType }}</strong>
        </div>
        <div class="metric-card">
          <span>Version</span>
          <strong>{{ resultJson.version || currentCharacterization.algorithm_version }}</strong>
        </div>
        <div class="metric-card">
          <span>Caracterizaciones</span>
          <strong>{{ characterizations.length }}</strong>
        </div>
      </div>

      <div
        v-if="currentCharacterization"
        class="section-block"
      >
        <h4>Conteos</h4>
        <div class="count-list">
          <div
            v-for="item in countRows"
            :key="item.label"
            class="count-row"
          >
            <span>{{ item.displayName }}</span>
            <strong>{{ item.value }}</strong>
          </div>
        </div>
      </div>

      <div
        v-if="currentCharacterization"
        class="section-block"
      >
        <h4>Indices</h4>
        <div class="count-list">
          <div
            v-if="isSaliva"
            class="count-row"
          >
            <span>Indice de genotoxicidad</span>
            <strong>{{ genotoxicityDisplay }}</strong>
          </div>
          <div class="count-row muted">
            <span>Indice de citotoxicidad</span>
            <strong>No disponible</strong>
          </div>
        </div>
        <p
          v-if="isSaliva"
          class="helper-text"
        >
          La citotoxicidad requiere reglas cientificas adicionales de asociacion celular.
        </p>
        <p
          v-else
          class="helper-text"
        >
          Para SANGRE se reportan conteos; los indices cientificos estan pendientes.
        </p>
      </div>

      <div
        v-if="warnings.length"
        class="section-block"
      >
        <h4>Advertencias</h4>
        <ul class="warning-list">
          <li
            v-for="warning in warnings"
            :key="warning"
          >
            {{ warning }}
          </li>
        </ul>
      </div>
    </template>
  </section>
</template>

<script>
import {
  getSegmentationTypeConfig,
  SAMPLE_TYPES,
} from "../../domain/segmentationTypes";

export default {
  name: "CharacterizationResultPanel",
  emits: ["characterize"],
  props: {
    sampleType: {
      type: String,
      default: SAMPLE_TYPES.SALIVA,
    },
    selectedSegmentationResult: {
      type: Object,
      default: null,
    },
    characterizations: {
      type: Array,
      default: () => [],
    },
    currentCharacterization: {
      type: Object,
      default: null,
    },
    characterizationsLoading: {
      type: Boolean,
      default: false,
    },
    characterizationsError: {
      type: String,
      default: "",
    },
    characterizeLoading: {
      type: Boolean,
      default: false,
    },
    characterizeError: {
      type: String,
      default: "",
    },
    characterizeMessage: {
      type: String,
      default: "",
    },
  },

  computed: {
    resultJson() {
      return this.currentCharacterization?.resultado_json || {};
    },

    counts() {
      return this.resultJson.counts || {};
    },

    indices() {
      return this.resultJson.indices || {};
    },

    warnings() {
      return Array.isArray(this.resultJson.warnings)
        ? this.resultJson.warnings
        : [];
    },

    isSaliva() {
      return this.sampleType === SAMPLE_TYPES.SALIVA;
    },

    labelConfig() {
      return getSegmentationTypeConfig(this.sampleType).labels;
    },

    countRows() {
      return this.labelConfig.map(item => ({
        label: item.label,
        displayName: item.displayName,
        value: this.counts[item.label] || 0,
      }));
    },

    sourceDisplay() {
      const source = this.resultJson.source || {};
      if (source.type === "VALIDADA") {
        const revision = source.numero_revision
          ? ` #${source.numero_revision}`
          : "";
        return `Revision validada${revision}`;
      }
      if (source.type === "AUTOMATICO") {
        return "Segmentacion automatica";
      }
      return this.currentCharacterization?.source_type || "No definido";
    },

    genotoxicityDisplay() {
      const value = this.indices.genotoxicity_index;
      if (value === null || value === undefined) return "No calculable";
      const numberValue = Number(value);
      if (!Number.isFinite(numberValue)) return "No calculable";
      return numberValue.toFixed(4);
    },

    showStaleNotice() {
      return (
        this.selectedSegmentationResult &&
        !this.characterizationsLoading &&
        !this.currentCharacterization &&
        this.characterizations.length > 0
      );
    },

    showNoCurrentNotice() {
      return (
        this.selectedSegmentationResult &&
        !this.characterizationsLoading &&
        !this.currentCharacterization &&
        this.characterizations.length === 0 &&
        !this.characterizationsError
      );
    },

    actionLabel() {
      return this.showStaleNotice
        ? "Actualizar caracterizacion"
        : "Caracterizar";
    },

    panelSubtitle() {
      if (!this.selectedSegmentationResult) {
        return "Selecciona un resultado de segmentacion completado.";
      }
      return `Resultado #${this.selectedSegmentationResult.id}`;
    },

    statusBadge() {
      if (!this.selectedSegmentationResult) return null;
      if (this.currentCharacterization) {
        return { text: "Vigente", className: "success" };
      }
      if (this.showStaleNotice) {
        return { text: "Desactualizada", className: "warning" };
      }
      return { text: "Pendiente", className: "neutral" };
    },
  },
};
</script>

<style scoped>
.characterization-panel {
  background: #ffffff;
  border: 1px solid #dde4ee;
  border-radius: 10px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-width: 0;
  padding: 18px;
}

.panel-header {
  align-items: flex-start;
  display: flex;
  gap: 12px;
  justify-content: space-between;
}

.panel-header h3 {
  color: #1f2937;
  font-size: 18px;
  margin: 0 0 4px;
}

.panel-header p,
.helper-text {
  color: #667085;
  font-size: 13px;
  line-height: 1.4;
  margin: 0;
}

.status-badge {
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  padding: 5px 10px;
  white-space: nowrap;
}

.status-badge.success {
  background: #e8f5e9;
  color: #2e7d32;
}

.status-badge.warning {
  background: #fff8e1;
  color: #8a6d1d;
}

.status-badge.neutral {
  background: #eef4ff;
  color: #3b5b8a;
}

.empty-state,
.status-card {
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 14px;
}

.empty-state {
  background: #f8fafc;
  color: #475467;
}

.status-card.neutral {
  background: #eef4ff;
  color: #3b5b8a;
}

.status-card.success {
  background: #e8f5e9;
  color: #2e7d32;
}

.status-card.warning {
  background: #fff8e1;
  color: #8a6d1d;
}

.status-card.error {
  background: #ffebee;
  color: #c62828;
}

.btn-primary {
  align-self: flex-start;
  background: #1e88e5;
  border: 0;
  border-radius: 8px;
  color: #ffffff;
  cursor: pointer;
  font-size: 14px;
  font-weight: 700;
  padding: 11px 16px;
}

.btn-primary:disabled {
  background: #b8c2cc;
  cursor: not-allowed;
}

.metrics-grid {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.metric-card {
  background: #f8fafc;
  border: 1px solid #e4e7ec;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
  padding: 12px;
}

.metric-card span,
.count-row span {
  color: #667085;
  font-size: 12px;
}

.metric-card strong,
.count-row strong {
  color: #1f2937;
  font-size: 15px;
}

.section-block {
  border-top: 1px solid #eef2f6;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding-top: 14px;
}

.section-block h4 {
  color: #344054;
  font-size: 14px;
  margin: 0;
}

.count-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.count-row {
  align-items: center;
  background: #f8fafc;
  border-radius: 8px;
  display: flex;
  justify-content: space-between;
  padding: 10px 12px;
}

.count-row.muted {
  opacity: 0.8;
}

.warning-list {
  color: #8a6d1d;
  font-size: 13px;
  line-height: 1.4;
  margin: 0;
  padding-left: 18px;
}

@media (max-width: 1023px) {
  .metrics-grid {
    grid-template-columns: 1fr;
  }
}
</style>
