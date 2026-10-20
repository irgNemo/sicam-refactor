<template>
  <div class="segmentation-panel">
    <section class="panel-section segmentation-actions" aria-label="Segmentación">
      <h4>Segmentación</h4>
      <SalivaSegmentationControl
        v-if="isSalivaSampleType"
        :loading="segmentacionLoading"
        :button-text="segmentacionButtonText"
        @run-segmentation="$emit('run-segmentation', $event)"
      />
      <button v-else class="btn-segment full-width" :disabled="segmentacionLoading" @click="$emit('run-segmentation')">
        {{ segmentacionButtonText }}
      </button>
      <div v-if="showLongRunningNotice" class="segmentation-status neutral">
        Segmentando muestra de sangre... Este proceso puede tardar varios minutos.
      </div>
      <div v-if="segmentacionError" class="segmentation-status error">{{ segmentacionError }}</div>
    </section>

    <section class="panel-section current-result" aria-label="Resultado actual">
      <h4>Resultado actual</h4>
      <div v-if="displayedBase" class="result-details">
        <strong>Resultado #{{ displayedBase.id }} · {{ displayedBase.estado }}</strong>
        <span>{{ formatearFechaResultado(displayedBase.creado_en) }}</span>
        <span v-if="segmentacionMetadata && segmentacionMetadata.id === displayedBase.id">
          {{ segmentacionMetadata.tipo_muestra }} · {{ segmentacionObjetosCount }} objetos en la base
        </span>
        <span v-else-if="latestIsSelected">{{ displayedBase.tipo_muestra }} · {{ ultimoHistorialObjetosCount }} objetos en la base</span>
      </div>

      <div v-if="effectiveSegmentationLoading" class="segmentation-status neutral">Cargando resultado mostrado...</div>
      <div v-else-if="effectiveSegmentationError" class="segmentation-status error">{{ effectiveSegmentationError }}</div>
      <div v-else-if="effectiveSegmentation" class="result-details">
        <template v-if="isEditMode">
          <strong>Borrador en edición<span v-if="activeRevision"> · Revisión #{{ activeRevision.numero_revision }}</span></strong>
          <span class="state-badge draft">BORRADOR · No efectivo</span>
          <span>Resultado efectivo: {{ effectiveSegmentationDisplay }}</span>
          <span v-if="isSalivaSampleType">Origen de la base: {{ strategyLabel(effectiveSegmentation) }}</span>
        </template>
        <template v-else>
          <span class="state-badge" :class="{ validated: effectiveSegmentation.fuente === 'VALIDADA' }">{{ effectiveSegmentationDisplay }}</span>
          <span>Resultado mostrado = resultado efectivo</span>
        </template>
        <span v-if="validationDate">Validada el {{ formatearFechaResultado(validationDate) }}</span>
        <span v-if="isSalivaSampleType && !isEditMode && effectiveSegmentation.fuente !== 'MANUAL'">
          {{ effectiveSegmentation.base_origin === 'MANUAL' ? 'Origen de la base:' : 'Método de segmentación:' }} {{ strategyLabel(effectiveSegmentation) }}
        </span>
      </div>
      <span v-else-if="displayedBase && isSalivaSampleType">Método: {{ strategyLabel(displayedBase) }}</span>

      <div v-if="!effectiveSegmentation && showValidatedRevisionNotice" class="result-details">
        <span>Revisión #{{ latestValidatedRevision.numero_revision }} · VALIDADA</span>
        <span v-if="latestValidatedRevision.validado_en">Validada el {{ formatearFechaResultado(latestValidatedRevision.validado_en) }}</span>
      </div>

      <div v-if="showPendingDraftNotice" class="pending-draft-card">
        <div class="pending-draft-copy">
          <strong>Revisión #{{ pendingDraftRevision.numero_revision }} · BORRADOR</strong>
          <span>Cambios guardados, aún no validados. No es el resultado efectivo.</span>
        </div>
        <button class="control-btn" @click="$emit('continue-edit')">Continuar edición</button>
      </div>
      <div v-else-if="pendingDraftError && !isEditMode" class="segmentation-status neutral">
        No fue posible consultar revisiones pendientes.
      </div>

      <div v-if="segmentacionMetadata && displayedBase && segmentacionMetadata.id !== displayedBase.id" class="segmentation-status success">
        <strong>Última ejecución: resultado #{{ segmentacionMetadata.id }} · {{ segmentacionMetadata.estado }}</strong>
        <span>{{ segmentacionMetadata.tipo_muestra }} · {{ segmentacionObjetosCount }} objetos</span>
        <span v-if="isSalivaSampleType">Método: {{ strategyLabel(segmentacionMetadata) }}</span>
      </div>
    </section>

    <section class="panel-section segmentation-history" aria-label="Historial">
      <h4>Historial <span v-if="historialSegmentacion.length" class="history-count">{{ historialSegmentacion.length }} resultados</span></h4>
      <div v-if="historialLoading" class="segmentation-status neutral">Cargando historial...</div>
      <template v-else>
        <div v-if="historialError" class="segmentation-status error">{{ historialError }}</div>
        <label v-if="completedSegmentationResults.length > 1" class="result-selector">
          <span>Segmentacion seleccionada</span>
          <select :value="selectedSegmentationResultId || ''" :disabled="historialLoading || segmentacionLoading" @change="$emit('change-segmentation-result', $event.target.value)">
            <option v-for="result in completedSegmentationResults" :key="resultKey(result)" :value="result.id">
              {{ formatearFechaResultado(result.creado_en) }} · Resultado #{{ result.id }}{{ isSalivaSampleType ? ` · ${strategyLabel(result)}` : '' }}
            </option>
          </select>
        </label>
        <span v-else-if="!completedSegmentationResults.length">Sin segmentaciones completadas</span>
        <span v-if="!ultimoResultadoSegmentacion">Sin resultados historicos</span>
        <span v-else-if="latestIsSelected">La última segmentación es el resultado seleccionado.</span>
        <div v-else class="result-details">
          <strong>Última segmentación · Resultado #{{ ultimoResultadoSegmentacion.id }}</strong>
          <span>{{ formatearFechaResultado(ultimoResultadoSegmentacion.creado_en) }}</span>
          <span>{{ ultimoHistorialObjetosCount }} objetos · {{ ultimoResultadoSegmentacion.estado }}</span>
          <span v-if="isSalivaSampleType">Método: {{ strategyLabel(ultimoResultadoSegmentacion) }}</span>
        </div>
      </template>
    </section>
  </div>
</template>

<script>
import SalivaSegmentationControl from "./SalivaSegmentationControl.vue";
import { SAMPLE_TYPES } from "../../domain/segmentationTypes";
import { segmentationStrategyLabel } from "../../domain/segmentationStrategies";

export default {
  name: "SegmentationResultPanel",
  components: { SalivaSegmentationControl },
  emits: ["run-segmentation", "continue-edit", "change-segmentation-result"],
  props: {
    segmentacionLoading: {
      type: Boolean,
      required: true,
    },
    segmentacionError: {
      type: String,
      default: "",
    },
    segmentacionMetadata: {
      type: Object,
      default: null,
    },
    segmentacionObjetosCount: {
      type: Number,
      required: true,
    },
    activeSampleType: {
      type: String,
      required: true,
    },
    activeSampleTypeDisplayName: {
      type: String,
      required: true,
    },
    isBloodSampleType: {
      type: Boolean,
      required: true,
    },
    effectiveSegmentationLoading: {
      type: Boolean,
      required: true,
    },
    effectiveSegmentationError: {
      type: String,
      default: "",
    },
    effectiveSegmentation: {
      type: Object,
      default: null,
    },
    effectiveSegmentationDisplay: {
      type: String,
      default: "",
    },
    showPendingDraftNotice: {
      type: Boolean,
      required: true,
    },
    pendingDraftRevision: {
      type: Object,
      default: null,
    },
    showValidatedRevisionNotice: {
      type: Boolean,
      required: true,
    },
    latestValidatedRevision: {
      type: Object,
      default: null,
    },
    pendingDraftError: {
      type: String,
      default: "",
    },
    activeRevision: {
      type: Object,
      default: null,
    },
    isEditMode: {
      type: Boolean,
      required: true,
    },
    historialSegmentacion: {
      type: Array,
      required: true,
    },
    historialLoading: {
      type: Boolean,
      required: true,
    },
    historialError: {
      type: String,
      default: "",
    },
    ultimoResultadoSegmentacion: {
      type: Object,
      default: null,
    },
    ultimoHistorialObjetosCount: {
      type: Number,
      required: true,
    },
    completedSegmentationResults: {
      type: Array,
      required: true,
    },
    selectedSegmentationResultId: {
      type: Number,
      default: null,
    },
  },
  computed: {
    selectedResult() {
      return this.completedSegmentationResults.find(result => result.id === this.selectedSegmentationResultId)
        || (this.completedSegmentationResults.length === 1 ? this.completedSegmentationResults[0] : null);
    },

    displayedBase() {
      return this.selectedResult || this.segmentacionMetadata;
    },

    latestIsSelected() {
      return Boolean(this.ultimoResultadoSegmentacion && this.displayedBase
        && this.ultimoResultadoSegmentacion.id === this.displayedBase.id);
    },

    validationDate() {
      return this.effectiveSegmentation?.revision?.validado_en
        || (this.showValidatedRevisionNotice ? this.latestValidatedRevision?.validado_en : null);
    },

    isSalivaSampleType() {
      return this.activeSampleType === SAMPLE_TYPES.SALIVA;
    },

    segmentacionButtonText() {
      if (this.segmentacionLoading) {
        return this.isBloodSampleType
          ? "Segmentando sangre..."
          : "Segmentando...";
      }

      return `Ejecutar segmentacion ${this.activeSampleTypeDisplayName.toLowerCase()}`;
    },

    showLongRunningNotice() {
      return this.segmentacionLoading && this.isBloodSampleType;
    },
  },
  methods: {
    strategyLabel(result) {
      return segmentationStrategyLabel(this.activeSampleType, result?.segmentation_strategy, result?.base_origin);
    },

    resultKey(result) {
      return `${result.tipo_muestra || this.activeSampleType}-${result.id}`;
    },

    formatearFechaResultado(fecha) {
      if (!fecha) return "Fecha no disponible";

      try {
        return new Intl.DateTimeFormat("es-MX", {
          dateStyle: "short",
          timeStyle: "short",
        }).format(new Date(fecha));
      } catch {
        return fecha;
      }
    },
  },
};
</script>

<style scoped>
.segmentation-panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.btn-segment {
  background: #1e88e5;
  border: 2px solid #1e88e5;
  border-radius: 10px;
  color: white;
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  padding: 12px;
  transition: all 0.2s ease;
}

.btn-segment:hover:not(:disabled) {
  background: #1976d2;
  border-color: #1976d2;
  box-shadow: 0 4px 12px rgba(30, 136, 229, 0.25);
  transform: translateY(-1px);
}

.btn-segment:disabled {
  cursor: wait;
  opacity: 0.7;
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

.segmentation-status {
  border-radius: 8px;
  font-size: 12px;
  line-height: 1.4;
  padding: 10px 12px;
}

.segmentation-status.error {
  background: #ffebee;
  border: 1px solid #ffcdd2;
  color: #c62828;
}

.segmentation-status.success {
  background: #e8f5e9;
  border: 1px solid #c8e6c9;
  color: #2e7d32;
}

.segmentation-status.neutral {
  background: #f8f9fa;
  border: 1px solid #d9e2ec;
  color: #2c3e50;
}

.pending-draft-card {
  align-items: center;
  background: #fff8e1;
  border: 1px solid #ffe082;
  border-radius: 10px;
  color: #5f4b12;
  display: grid;
  gap: 10px;
  grid-template-columns: minmax(0, 1fr);
  padding: 10px 12px;
}

.pending-draft-copy {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}

.pending-draft-copy strong {
  color: #5f4b12;
  font-size: 13px;
}

.pending-draft-copy span {
  color: #7a651a;
  font-size: 12px;
  line-height: 1.35;
}

.segmentation-history {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.result-selector {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.result-selector select {
  background: #ffffff;
  border: 2px solid #d9e2ec;
  border-radius: 8px;
  color: #2c3e50;
  font-size: 12px;
  min-width: 0;
  padding: 8px 10px;
  width: 100%;
}

.full-width {
  width: 100%;
}

@media (max-width: 1439px) and (min-width: 1024px) {
  .segmentation-panel {
    gap: 10px;
  }

  .segmentation-status {
    padding: 8px 10px;
  }
}

.panel-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px;
  border: 1px solid #d9e2ec;
  border-radius: 10px;
  min-width: 0;
  overflow-wrap: anywhere;
  color: #2c3e50;
  font-size: 12px;
}
.panel-section h4 {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  font-size: 13px;
  margin: 0;
}
.result-details, .segmentation-status.success {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.state-badge, .history-count {
  align-self: flex-start;
  border-radius: 8px;
  padding: 4px 8px;
  background: #eef5ff;
  color: #1f4f82;
  max-width: 100%;
}
.state-badge.validated { background: #edf7ed; color: #256029; }
.state-badge.draft { background: #fff8e1; color: #5f4b12; }
.history-count { background: #f0f4f8; color: #666; font-size: 11px; }
</style>
