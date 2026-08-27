<template>
  <div class="segmentation-panel">
    <button
      class="btn-segment full-width"
      :disabled="segmentacionLoading"
      @click="$emit('run-segmentation')"
    >
      {{ segmentacionButtonText }}
    </button>

    <div
      v-if="showLongRunningNotice"
      class="segmentation-status neutral"
    >
      Segmentando muestra de sangre... Este proceso puede tardar varios minutos.
    </div>

    <div v-if="segmentacionError" class="segmentation-status error">
      {{ segmentacionError }}
    </div>

    <div v-if="segmentacionMetadata" class="segmentation-status success">
      <div class="status-title">
        Segmentacion {{ segmentacionMetadata.estado }}
      </div>
      <div class="status-grid">
        <span>ID resultado</span>
        <strong>#{{ segmentacionMetadata.id }}</strong>
        <span>Tipo</span>
        <strong>{{ segmentacionMetadata.tipo_muestra }}</strong>
        <span>Objetos</span>
        <strong>{{ segmentacionObjetosCount }}</strong>
      </div>
    </div>

    <div
      v-if="effectiveSegmentationLoading"
      class="segmentation-status neutral"
    >
      Cargando resultado mostrado...
    </div>

    <div
      v-else-if="effectiveSegmentationError"
      class="segmentation-status error"
    >
      {{ effectiveSegmentationError }}
    </div>

    <div
      v-else-if="effectiveSegmentation"
      class="effective-result-card"
    >
      <strong>Resultado mostrado</strong>
      <span>{{ effectiveSegmentationDisplay }}</span>
    </div>

    <div
      v-if="showPendingDraftNotice"
      class="pending-draft-card"
    >
      <div class="pending-draft-copy">
        <strong>Revisión pendiente</strong>
        <span>
          Revisión #{{ pendingDraftRevision.numero_revision }} ·
          Cambios guardados, aún no validados.
        </span>
      </div>
      <button
        class="control-btn"
        @click="$emit('continue-edit')"
      >
        Continuar edición
      </button>
    </div>

    <div
      v-else-if="showValidatedRevisionNotice"
      class="validated-revision-card"
    >
      <strong>Revisión validada</strong>
      <span>
        Revisión #{{ latestValidatedRevision.numero_revision }} · VALIDADA
        <template v-if="latestValidatedRevision.validado_en">
          · {{ formatearFechaResultado(latestValidatedRevision.validado_en) }}
        </template>
      </span>
    </div>

    <div
      v-else-if="pendingDraftError && !isEditMode"
      class="segmentation-status neutral"
    >
      No fue posible consultar revisiones pendientes.
    </div>

    <div class="segmentation-history">
      <div class="history-title">
        Ultima segmentacion
        <span v-if="historialSegmentacion.length">
          {{ historialSegmentacion.length }} resultados
        </span>
      </div>

      <div v-if="historialLoading" class="segmentation-status neutral">
        Cargando historial...
      </div>

      <div v-else-if="historialError" class="segmentation-status error">
        {{ historialError }}
      </div>

      <div v-else-if="!ultimoResultadoSegmentacion" class="segmentation-status neutral">
        Sin resultados historicos
      </div>

      <div v-else class="history-compact-card">
        <strong>{{ formatearFechaResultado(ultimoResultadoSegmentacion.creado_en) }}</strong>
        <span>
          {{ ultimoHistorialObjetosCount }} objetos · {{ ultimoResultadoSegmentacion.estado }}
        </span>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: "SegmentationResultPanel",
  emits: ["run-segmentation", "continue-edit"],
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
  },
  computed: {
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
  grid-template-columns: minmax(0, 1fr) auto;
  padding: 10px 12px;
}

.validated-revision-card {
  background: #edf7ed;
  border: 1px solid #c8e6c9;
  border-radius: 10px;
  color: #256029;
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: 10px 12px;
}

.effective-result-card {
  background: #eef5ff;
  border: 1px solid #c8dcf5;
  border-radius: 10px;
  color: #1f4f82;
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: 10px 12px;
}

.validated-revision-card strong,
.effective-result-card strong {
  font-size: 12px;
}

.validated-revision-card span,
.effective-result-card span {
  font-size: 11px;
  line-height: 1.4;
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

.history-title {
  align-items: center;
  color: #2c3e50;
  display: flex;
  font-size: 12px;
  font-weight: 700;
  justify-content: space-between;
}

.history-title span {
  background: #f0f4f8;
  border-radius: 10px;
  color: #666;
  font-size: 11px;
  padding: 2px 8px;
}

.status-title {
  font-weight: 700;
  margin-bottom: 8px;
}

.status-grid {
  display: grid;
  gap: 6px 10px;
  grid-template-columns: 1fr auto;
}

.history-compact-card {
  background: #f8f9fa;
  border: 1px solid #d9e2ec;
  border-radius: 8px;
  color: #2c3e50;
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: 8px 10px;
}

.history-compact-card strong {
  font-size: 12px;
}

.history-compact-card span {
  color: #666;
  font-size: 11px;
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
</style>
