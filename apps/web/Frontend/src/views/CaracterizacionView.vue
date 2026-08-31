<template>
  <main class="characterization-view">
    <header class="page-header">
      <div>
        <h2>Caracterizacion</h2>
        <p>
          Caracterizacion cientifica sobre resultados de segmentacion efectivos.
        </p>
      </div>
      <div class="context-badges">
        <span>Paciente: {{ patientId || "sin seleccionar" }}</span>
        <span>Caso: {{ caseId || "sin seleccionar" }}</span>
      </div>
    </header>

    <section
      v-if="!caseId"
      class="empty-case"
    >
      <h3>Selecciona un caso</h3>
      <p>
        Usa el panel lateral para elegir paciente y caso antes de consultar
        caracterizaciones.
      </p>
    </section>

    <template v-else>
      <div class="sample-type-tabs">
        <button
          v-for="tab in sampleTypeTabs"
          :key="tab.sampleType"
          type="button"
          class="sample-type-tab"
          :class="{ active: activeSampleType === tab.sampleType }"
          @click="setActiveSampleType(tab.sampleType)"
        >
          {{ tab.displayName }}
        </button>
      </div>

      <section class="characterization-layout">
        <aside class="samples-panel">
          <div class="panel-title">
            <h3>Muestras de {{ activeSampleTypeDisplayName }}</h3>
            <span>{{ samples.length }}</span>
          </div>

          <div
            v-if="loading"
            class="status-card neutral"
          >
            Cargando muestras...
          </div>

          <div
            v-else-if="loadError"
            class="status-card error"
          >
            {{ loadError }}
          </div>

          <div
            v-else-if="!samples.length"
            class="status-card neutral"
          >
            No hay muestras disponibles para este caso y tipo.
          </div>

          <div
            v-else
            ref="sampleList"
            class="sample-list"
          >
            <button
              v-for="sample in samples"
              :key="sampleKey(sample)"
              :ref="el => setSampleItemRef(sample.id_muestra, el)"
              type="button"
              class="sample-item"
              :class="{ active: selectedSample?.id_muestra === sample.id_muestra }"
              @click="selectSample(sample, { source: 'user' })"
            >
              <img
                v-if="sample.imagen"
                :src="sample.imagen"
                alt=""
              />
              <div
                v-else
                class="sample-placeholder"
              >
                Sin imagen
              </div>
              <span class="sample-item-text">
                <strong>{{ sampleName(sample) }}</strong>
                <small>Muestra #{{ sample.id_muestra }}</small>
              </span>
            </button>
          </div>
        </aside>

        <section class="work-panel">
          <div class="sample-preview-card">
            <div class="panel-title">
              <h3>Muestra seleccionada</h3>
              <span v-if="selectedSample">#{{ selectedSample.id_muestra }}</span>
            </div>

            <div
              v-if="!selectedSample"
              class="status-card neutral"
            >
              Selecciona una muestra para revisar sus resultados.
            </div>

            <template v-else>
              <div class="preview-row">
                <img
                  v-if="selectedSample.imagen"
                  class="sample-preview"
                  :src="selectedSample.imagen"
                  alt=""
                />
                <div class="preview-meta">
                  <strong>{{ sampleName(selectedSample) }}</strong>
                  <span>Tipo: {{ activeSampleTypeDisplayName }}</span>
                  <span>Imagen: {{ selectedSample.imagen ? "disponible" : "sin archivo" }}</span>
                </div>
              </div>

              <div
                v-if="completedSegmentationResults.length === 1"
                class="single-result-card"
              >
                <span>Segmentacion a caracterizar</span>
                <strong>{{ formatDate(completedSegmentationResults[0].creado_en) }}</strong>
                <small>Resultado #{{ completedSegmentationResults[0].id }}</small>
              </div>

              <label
                v-else-if="completedSegmentationResults.length > 1"
                class="result-selector"
              >
                Segmentacion a caracterizar
                <select
                  :disabled="resultsLoading"
                  :value="localSelectedSegmentationResultId || ''"
                  @change="setSelectedSegmentationResult($event.target.value)"
                >
                  <option value="">
                    {{ resultSelectorPlaceholder }}
                  </option>
                  <option
                    v-for="result in completedSegmentationResults"
                    :key="resultKey(result)"
                    :value="result.id"
                  >
                    {{ formatDate(result.creado_en) }} · Resultado #{{ result.id }}
                  </option>
                </select>
              </label>

              <div
                v-if="resultsLoading"
                class="status-card neutral"
              >
                Cargando resultados de segmentacion...
              </div>

              <div
                v-else-if="resultsError"
                class="status-card error"
              >
                {{ resultsError }}
              </div>

              <div
                v-else-if="!completedSegmentationResults.length"
                class="status-card warning"
              >
                No hay una segmentacion completada disponible para caracterizar.
              </div>
            </template>
          </div>

          <CharacterizationResultPanel
            :sample-type="activeSampleType"
            :selected-segmentation-result="selectedSegmentationResult"
            :characterizations="characterizations"
            :current-characterization="currentCharacterization"
            :characterizations-loading="characterizationsLoading"
            :characterizations-error="characterizationsError"
            :characterize-loading="characterizeLoading"
            :characterize-error="characterizeError"
            :characterize-message="characterizeMessage"
            @characterize="runCharacterization"
          />
        </section>
      </section>
    </template>
  </main>
</template>

<script>
import apiClient from "../services/apiClient";
import {
  obtenerCaracterizaciones,
  caracterizarResultado,
} from "../services/characterizationService";
import {
  listarMuestras,
  obtenerResultadosSegmentacion,
} from "../services/segmentationService";
import {
  getSegmentationTypeConfig,
  SEGMENTATION_TYPE_CONFIG,
  SAMPLE_TYPES,
} from "../domain/segmentationTypes";
import CharacterizationResultPanel from "../components/characterization/CharacterizationResultPanel.vue";

export default {
  name: "CaracterizacionView",
  components: {
    CharacterizationResultPanel,
  },
  emits: [
    "sample-type-changed",
    "sample-selected",
    "segmentation-result-selected",
  ],
  props: {
    patientId: {
      type: Number,
      default: null,
    },
    caseId: {
      type: Number,
      default: null,
    },
    activeSampleType: {
      type: String,
      default: SAMPLE_TYPES.SALIVA,
    },
    selectedSampleId: {
      type: Number,
      default: null,
    },
    selectedSegmentationResultId: {
      type: Number,
      default: null,
    },
  },

  data() {
    return {
      analisis: [],
      muestrasSangre: [],
      loading: false,
      loadError: "",
      selectedSample: null,
      segmentationResults: [],
      localSelectedSegmentationResultId: null,
      resultsLoading: false,
      resultsError: "",
      characterizations: [],
      characterizationsLoading: false,
      characterizationsError: "",
      characterizeLoading: false,
      characterizeError: "",
      characterizeMessage: "",
      contextRequestId: 0,
      resultsRequestId: 0,
      characterizationsRequestId: 0,
      sampleItemRefs: {},
    };
  },

  computed: {
    sampleTypeTabs() {
      return Object.values(SEGMENTATION_TYPE_CONFIG).map(config => ({
        sampleType: config.sampleType,
        displayName: config.displayName,
      }));
    },

    activeSampleTypeDisplayName() {
      return getSegmentationTypeConfig(this.activeSampleType).displayName;
    },

    analisisActual() {
      if (!this.patientId || !this.caseId) return null;
      return this.analisis.find(item => (
        item.id_paciente_fk === this.patientId &&
        item.id_caso_fk === this.caseId
      )) || null;
    },

    samples() {
      if (!this.analisisActual) return [];

      if (this.activeSampleType === SAMPLE_TYPES.BLOOD) {
        return this.muestrasSangre.filter(
          muestra => muestra.analisis === this.analisisActual.id_analisis
        );
      }

      return this.analisisActual.muestras_saliva || [];
    },

    completedSegmentationResults() {
      return this.segmentationResults
        .filter(result => result.estado === "COMPLETADO")
        .sort((a, b) => {
          const byDate = new Date(b.creado_en || 0) - new Date(a.creado_en || 0);
          if (byDate !== 0) return byDate;
          return Number(b.id || 0) - Number(a.id || 0);
        });
    },

    selectedSegmentationResult() {
      if (!this.localSelectedSegmentationResultId) return null;
      return this.completedSegmentationResults.find(
        result => result.id === this.localSelectedSegmentationResultId
      ) || null;
    },

    currentCharacterization() {
      return this.characterizations.find(
        item => item.vigente === true
      ) || null;
    },

    resultSelectorPlaceholder() {
      if (this.resultsLoading) return "Cargando resultados...";
      if (!this.completedSegmentationResults.length) {
        return "Sin resultados completados";
      }
      return "Selecciona un resultado";
    },
  },

  watch: {
    patientId() {
      this.resetSelection();
      this.loadContext();
    },

    caseId() {
      this.resetSelection();
      this.loadContext();
    },

    activeSampleType() {
      this.resetSelection();
      this.$nextTick(() => {
        this.restoreSelectedSample();
      });
    },

    samples(newSamples) {
      if (
        this.selectedSample &&
        newSamples.some(sample => sample.id_muestra === this.selectedSample.id_muestra)
      ) {
        return;
      }

      this.restoreSelectedSample();
    },

    selectedSampleId() {
      this.restoreSelectedSample();
    },

    selectedSegmentationResultId() {
      if (this.segmentationResults.length) {
        this.restoreSelectedSegmentationResult();
      }
    },
  },

  mounted() {
    this.loadContext();
  },

  methods: {
    setActiveSampleType(sampleType) {
      if (
        sampleType === this.activeSampleType ||
        !this.sampleTypeTabs.some(tab => tab.sampleType === sampleType)
      ) {
        return;
      }

      this.$emit("sample-type-changed", sampleType);
    },

    async loadContext() {
      const requestId = ++this.contextRequestId;
      this.loading = true;
      this.loadError = "";

      try {
        const [analisisResponse, muestrasSangreResponse] = await Promise.all([
          apiClient.get("/api/analisis/"),
          listarMuestras(SAMPLE_TYPES.BLOOD),
        ]);

        if (requestId !== this.contextRequestId) return;

        this.analisis = analisisResponse.data || [];
        this.muestrasSangre = muestrasSangreResponse.data || [];
        this.$nextTick(() => {
          this.restoreSelectedSample();
        });
      } catch (error) {
        if (requestId === this.contextRequestId) {
          this.loadError = "No fue posible cargar los datos de caracterizacion.";
        }
      } finally {
        if (requestId === this.contextRequestId) {
          this.loading = false;
        }
      }
    },

    selectSample(sample, options = {}) {
      const shouldEmit = options.emit !== false;

      if (
        sample &&
        this.selectedSample?.id_muestra === sample.id_muestra &&
        this.selectedSampleId === sample.id_muestra
      ) {
        if (options.scroll) this.scrollSelectedSampleIntoView(sample.id_muestra);
        return;
      }

      this.selectedSample = sample;
      this.segmentationResults = [];
      this.localSelectedSegmentationResultId = null;
      this.resetCharacterizationState();

      if (shouldEmit) {
        this.$emit("sample-selected", {
          sampleType: this.activeSampleType,
          sampleId: sample?.id_muestra || null,
        });
      }

      if (sample?.id_muestra) {
        this.loadSegmentationResults(sample.id_muestra, this.activeSampleType);
      }

      if (options.scroll && sample?.id_muestra) {
        this.$nextTick(() => {
          this.scrollSelectedSampleIntoView(sample.id_muestra);
        });
      }
    },

    async loadSegmentationResults(sampleId, sampleType) {
      const requestId = ++this.resultsRequestId;
      this.resultsLoading = true;
      this.resultsError = "";

      try {
        const response = await obtenerResultadosSegmentacion(sampleId, sampleType);

        if (!this.isCurrentSample(sampleId, sampleType, requestId)) return;

        this.segmentationResults = Array.isArray(response.data)
          ? response.data
          : [];
        this.restoreSelectedSegmentationResult();
      } catch (error) {
        if (this.isCurrentSample(sampleId, sampleType, requestId)) {
          this.resultsError = "No fue posible cargar resultados de segmentacion.";
        }
      } finally {
        if (this.isCurrentSample(sampleId, sampleType, requestId)) {
          this.resultsLoading = false;
        }
      }
    },

    setSelectedSegmentationResult(resultId) {
      const parsedId = Number(resultId);
      const selected = Number.isFinite(parsedId)
        ? this.completedSegmentationResults.find(result => result.id === parsedId)
        : null;
      const nextId = selected?.id || null;

      this.localSelectedSegmentationResultId = nextId;
      this.emitSegmentationResultSelected(nextId);
      this.resetCharacterizationState();

      if (this.localSelectedSegmentationResultId) {
        this.loadCharacterizations(this.localSelectedSegmentationResultId);
      }
    },

    async loadCharacterizations(resultadoId) {
      const requestId = ++this.characterizationsRequestId;
      this.characterizationsLoading = true;
      this.characterizationsError = "";

      try {
        const response = await obtenerCaracterizaciones(resultadoId);

        if (!this.isCurrentResult(resultadoId, requestId)) return;

        this.characterizations = Array.isArray(response.data)
          ? response.data
          : [];
      } catch (error) {
        if (this.isCurrentResult(resultadoId, requestId)) {
          this.characterizationsError = "No fue posible cargar la caracterizacion.";
        }
      } finally {
        if (this.isCurrentResult(resultadoId, requestId)) {
          this.characterizationsLoading = false;
        }
      }
    },

    async runCharacterization() {
      if (!this.selectedSegmentationResult || this.characterizeLoading) return;

      const resultadoId = this.selectedSegmentationResult.id;
      this.characterizeLoading = true;
      this.characterizeError = "";
      this.characterizeMessage = "";

      try {
        const response = await caracterizarResultado(resultadoId);

        if (this.localSelectedSegmentationResultId !== resultadoId) return;

        this.characterizeMessage = response.status === 201
          ? "Caracterizacion generada."
          : "Caracterizacion vigente reutilizada.";
        await this.loadCharacterizations(resultadoId);
      } catch (error) {
        if (this.localSelectedSegmentationResultId === resultadoId) {
          this.characterizeError = "No fue posible caracterizar el resultado.";
        }
      } finally {
        if (this.localSelectedSegmentationResultId === resultadoId) {
          this.characterizeLoading = false;
        }
      }
    },

    resetSelection() {
      this.selectedSample = null;
      this.segmentationResults = [];
      this.localSelectedSegmentationResultId = null;
      this.resetCharacterizationState();
    },

    resetCharacterizationState() {
      this.characterizations = [];
      this.characterizationsLoading = false;
      this.characterizationsError = "";
      this.characterizeLoading = false;
      this.characterizeError = "";
      this.characterizeMessage = "";
    },

    restoreSelectedSample() {
      if (!this.selectedSampleId) {
        this.selectSample(null, { emit: false });
        return;
      }

      const sample = this.samples.find(
        item => item.id_muestra === this.selectedSampleId
      );

      if (!sample) {
        this.selectSample(null, { emit: false });
        return;
      }

      this.selectSample(sample, { scroll: true, emit: false });
    },

    restoreSelectedSegmentationResult() {
      const selected = this.selectedSegmentationResultId
        ? this.completedSegmentationResults.find(
          result => result.id === this.selectedSegmentationResultId
        )
        : null;
      const nextResult = selected || this.completedSegmentationResults[0] || null;
      const nextId = nextResult?.id || null;

      if (this.localSelectedSegmentationResultId === nextId) {
        return;
      }

      this.localSelectedSegmentationResultId = nextId;
      this.emitSegmentationResultSelected(nextId);
      this.resetCharacterizationState();

      if (nextId) {
        this.loadCharacterizations(nextId);
      }
    },

    emitSegmentationResultSelected(resultadoId) {
      this.$emit("segmentation-result-selected", {
        sampleType: this.activeSampleType,
        sampleId: this.selectedSample?.id_muestra || null,
        resultadoId: resultadoId || null,
      });
    },

    setSampleItemRef(sampleId, element) {
      if (element) {
        this.sampleItemRefs[sampleId] = element;
      } else {
        delete this.sampleItemRefs[sampleId];
      }
    },

    scrollSelectedSampleIntoView(sampleId) {
      const element = this.sampleItemRefs[sampleId];
      const container = this.$refs.sampleList;
      if (!element || !container) return;

      const elementRect = element.getBoundingClientRect();
      const containerRect = container.getBoundingClientRect();
      const above = elementRect.top < containerRect.top;
      const below = elementRect.bottom > containerRect.bottom;

      if (!above && !below) return;

      element.scrollIntoView({
        block: "nearest",
        inline: "nearest",
        behavior: "smooth",
      });
    },

    isCurrentSample(sampleId, sampleType, requestId) {
      return Boolean(
        requestId === this.resultsRequestId &&
        this.selectedSample?.id_muestra === sampleId &&
        this.activeSampleType === sampleType
      );
    },

    isCurrentResult(resultadoId, requestId) {
      return Boolean(
        requestId === this.characterizationsRequestId &&
        this.localSelectedSegmentationResultId === resultadoId
      );
    },

    sampleKey(sample) {
      return `${this.activeSampleType}-${sample?.id_muestra || "sin-id"}`;
    },

    resultKey(result) {
      return `${result.tipo_muestra || this.activeSampleType}-${result.id}`;
    },

    sampleName(sample) {
      if (!sample) return "Sin muestra";
      if (sample.imagen) {
        const pieces = String(sample.imagen).split("/");
        return pieces[pieces.length - 1] || `Muestra ${sample.id_muestra}`;
      }
      return `Muestra ${sample.id_muestra}`;
    },

    formatDate(value) {
      if (!value) return "sin fecha";
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) return "sin fecha";
      return date.toLocaleString("es-MX", {
        dateStyle: "short",
        timeStyle: "short",
      });
    },
  },
};
</script>

<style scoped>
.characterization-view {
  background: #f8f9fa;
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  gap: 16px;
  min-height: 0;
  min-width: 0;
  overflow: auto;
  padding: 16px;
}

.page-header {
  align-items: flex-start;
  display: flex;
  gap: 16px;
  justify-content: space-between;
}

.page-header h2 {
  color: #1f2937;
  font-size: 24px;
  margin: 0 0 4px;
}

.page-header p {
  color: #667085;
  font-size: 14px;
  margin: 0;
}

.context-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
}

.context-badges span {
  background: #ffffff;
  border: 1px solid #dde4ee;
  border-radius: 999px;
  color: #475467;
  font-size: 12px;
  font-weight: 700;
  padding: 6px 10px;
}

.empty-case {
  align-items: center;
  background: #ffffff;
  border: 1px solid #dde4ee;
  border-radius: 10px;
  color: #475467;
  display: flex;
  flex: 1;
  flex-direction: column;
  justify-content: center;
  min-height: 320px;
  padding: 24px;
  text-align: center;
}

.empty-case h3 {
  color: #1f2937;
  margin: 0 0 8px;
}

.empty-case p {
  margin: 0;
}

.sample-type-tabs {
  background: #ffffff;
  border: 1px solid #dde4ee;
  border-radius: 10px;
  display: flex;
  gap: 8px;
  padding: 8px;
}

.sample-type-tab {
  background: transparent;
  border: 0;
  border-radius: 8px;
  color: #52606d;
  cursor: pointer;
  flex: 0 0 auto;
  font-size: 14px;
  font-weight: 700;
  padding: 10px 14px;
}

.sample-type-tab.active {
  background: #1e88e5;
  color: #ffffff;
}

.characterization-layout {
  display: grid;
  flex: 1;
  gap: 16px;
  grid-template-columns: minmax(180px, 220px) minmax(0, 1fr);
  max-height: calc(100vh - 176px);
  min-height: 0;
  min-width: 0;
}

.samples-panel,
.sample-preview-card {
  background: #ffffff;
  border: 1px solid #dde4ee;
  border-radius: 10px;
  min-width: 0;
  padding: 14px;
}

.samples-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: calc(100vh - 176px);
  min-height: 0;
  overflow: hidden;
}

.panel-title {
  align-items: center;
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.panel-title h3 {
  color: #1f2937;
  font-size: 16px;
  margin: 0;
}

.panel-title span {
  color: #667085;
  font-size: 12px;
  font-weight: 700;
}

.sample-list {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  gap: 10px;
  min-height: 0;
  overflow-x: hidden;
  overflow-y: auto;
}

.sample-item {
  align-items: center;
  background: #ffffff;
  border: 2px solid #e4e7ec;
  border-radius: 9px;
  color: #344054;
  cursor: pointer;
  display: grid;
  gap: 10px;
  grid-template-columns: 52px minmax(0, 1fr);
  min-width: 0;
  padding: 8px;
  text-align: left;
}

.sample-item.active {
  background: #e3f2fd;
  border-color: #1e88e5;
}

.sample-item img,
.sample-placeholder {
  aspect-ratio: 1;
  border-radius: 7px;
  height: 52px;
  width: 52px;
}

.sample-item img {
  object-fit: cover;
}

.sample-placeholder {
  align-items: center;
  background: #eef2f6;
  color: #667085;
  display: flex;
  font-size: 10px;
  justify-content: center;
  text-align: center;
}

.sample-item-text {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}

.sample-item-text strong,
.sample-item-text small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sample-item-text strong {
  color: #344054;
  font-size: 13px;
}

.sample-item-text small {
  color: #667085;
  font-size: 11px;
}

.work-panel {
  display: grid;
  gap: 16px;
  grid-template-columns: minmax(0, 0.95fr) minmax(320px, 1.05fr);
  min-height: 0;
  min-width: 0;
}

.sample-preview-card {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.preview-row {
  display: grid;
  gap: 12px;
  grid-template-columns: 140px minmax(0, 1fr);
}

.sample-preview {
  aspect-ratio: 1;
  background: #f2f4f7;
  border-radius: 8px;
  object-fit: contain;
  width: 100%;
}

.preview-meta {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}

.preview-meta strong {
  color: #1f2937;
  overflow-wrap: anywhere;
}

.preview-meta span {
  color: #667085;
  font-size: 13px;
}

.result-selector {
  color: #475467;
  display: flex;
  flex-direction: column;
  font-size: 13px;
  font-weight: 700;
  gap: 6px;
}

.result-selector select {
  border: 2px solid #dde4ee;
  border-radius: 8px;
  color: #344054;
  font-size: 14px;
  padding: 10px;
  width: 100%;
}

.single-result-card {
  background: #f8fafc;
  border: 1px solid #dde4ee;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 12px;
}

.single-result-card span,
.single-result-card small {
  color: #667085;
  font-size: 12px;
}

.single-result-card strong {
  color: #1f2937;
  font-size: 14px;
}

.status-card {
  border-radius: 8px;
  font-size: 13px;
  line-height: 1.4;
  padding: 12px;
}

.status-card.neutral {
  background: #eef4ff;
  color: #3b5b8a;
}

.status-card.warning {
  background: #fff8e1;
  color: #8a6d1d;
}

.status-card.error {
  background: #ffebee;
  color: #c62828;
}

@media (max-width: 1439px) and (min-width: 1024px) {
  .characterization-layout {
    grid-template-columns: minmax(170px, 190px) minmax(0, 1fr);
  }

  .work-panel {
    grid-template-columns: minmax(0, 0.9fr) minmax(300px, 1fr);
  }

  .preview-row {
    grid-template-columns: 110px minmax(0, 1fr);
  }
}

@media (max-width: 1023px) {
  .page-header,
  .context-badges {
    justify-content: flex-start;
  }

  .page-header,
  .characterization-layout,
  .work-panel,
  .preview-row {
    display: flex;
    flex-direction: column;
  }

  .samples-panel {
    max-height: min(360px, calc(100vh - 220px));
  }
}
</style>
