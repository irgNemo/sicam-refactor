<template>
  <TopBar
    :seccion="seccion"
    @change-section="requestSectionChange"
  />

  <div class="app">
    <SideBar
      v-if="showSharedSidebar"
      ref="sideBar"
      :active-sample-type="activeSampleType"
      :selected-patient-id="selectedPatientId"
      :selected-case-id="selectedCaseId"
      :show-analysis-button="seccion === 'segmentacion'"
      @select-patient="onSelectPatient"
      @select-case="onSelectCase"
      @context-invalid="onContextInvalid"
    />

    <MainContent
      v-if="seccion === 'segmentacion'"
      ref="mainContent"
      :patientId="selectedPatientId"
      :caseId="selectedCaseId"
      :active-sample-type="activeSampleType"
      :selected-sample-id="activeSelectedSampleId"
      :selected-segmentation-result-id="activeSelectedSegmentationResultId"
      @sample-type-changed="onSampleTypeChanged"
      @segmentation-completed="onSegmentationCompleted"
      @sample-selected="onSampleSelected"
      @segmentation-result-selected="onSegmentationResultSelected"
    />

    <CaracterizacionView
      v-if="seccion === 'caracterizacion'"
      :patient-id="selectedPatientId"
      :case-id="selectedCaseId"
      :active-sample-type="activeSampleType"
      :selected-sample-id="activeSelectedSampleId"
      :selected-segmentation-result-id="activeSelectedSegmentationResultId"
      @sample-type-changed="onSampleTypeChanged"
      @sample-selected="onSampleSelected"
      @segmentation-result-selected="onSegmentationResultSelected"
    />

    <div v-if="seccion === 'analisis'" class="placeholder-view">
      <div class="placeholder-content">
        <div class="placeholder-icon">🔍</div>
        <h2>Análisis</h2>
        <p>Este módulo está en desarrollo</p>
        <div class="placeholder-badge">Próximamente</div>
      </div>
    </div>

    <RegistroView v-if="seccion === 'registro'" />
  </div>
</template>

<script>
import TopBar from "./components/TopBar.vue";
import SideBar from "./components/SideBar.vue";
import MainContent from "./components/MainContent.vue";
import RegistroView from "./views/RegistroView.vue";
import CaracterizacionView from "./views/CaracterizacionView.vue";
import { SAMPLE_TYPES } from "./domain/segmentationTypes";

const UI_CONTEXT_STORAGE_KEY = "sicam.uiContext.v1";
const UI_CONTEXT_VERSION = 1;
const VALID_SECTIONS = ["segmentacion", "caracterizacion", "analisis", "registro"];
const VALID_SAMPLE_TYPES = Object.values(SAMPLE_TYPES);

function normalizeOptionalId(value) {
  if (value === null || value === undefined || value === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function readStoredUiContext() {
  if (typeof window === "undefined") return null;

  try {
    const rawValue = window.sessionStorage.getItem(UI_CONTEXT_STORAGE_KEY);
    if (!rawValue) return null;

    const parsed = JSON.parse(rawValue);
    if (!parsed || parsed.version !== UI_CONTEXT_VERSION) {
      window.sessionStorage.removeItem(UI_CONTEXT_STORAGE_KEY);
      return null;
    }

    const activeTab = VALID_SECTIONS.includes(parsed.activeTab)
      ? parsed.activeTab
      : "segmentacion";
    const sampleType = VALID_SAMPLE_TYPES.includes(parsed.sampleType)
      ? parsed.sampleType
      : SAMPLE_TYPES.SALIVA;

    return {
      activeTab,
      patientId: normalizeOptionalId(parsed.patientId),
      caseId: normalizeOptionalId(parsed.caseId),
      sampleType,
      sampleId: normalizeOptionalId(parsed.sampleId),
      segmentationResultId: normalizeOptionalId(parsed.segmentationResultId),
    };
  } catch {
    window.sessionStorage.removeItem(UI_CONTEXT_STORAGE_KEY);
    return null;
  }
}

export default {
  name: "App",

  components: {
    TopBar,
    SideBar,
    MainContent,
    RegistroView,
    CaracterizacionView,
  },

  data() {
    const storedContext = readStoredUiContext();

    return {
      seccion: storedContext?.activeTab || "segmentacion",
      selectedPatientId: storedContext?.patientId || null,
      selectedCaseId: storedContext?.caseId || null,
      activeSampleType: storedContext?.sampleType || SAMPLE_TYPES.SALIVA,
      selectedSampleRef: {
        sampleType: storedContext?.sampleId ? storedContext.sampleType : null,
        sampleId: storedContext?.sampleId || null,
      },
      selectedSegmentationResultRef: {
        sampleType: storedContext?.segmentationResultId
          ? storedContext.sampleType
          : null,
        sampleId: storedContext?.segmentationResultId
          ? storedContext.sampleId
          : null,
        resultadoId: storedContext?.segmentationResultId || null,
      },
    };
  },

  computed: {
    showSharedSidebar() {
      return ["segmentacion", "caracterizacion"].includes(this.seccion);
    },

    activeSelectedSampleId() {
      return this.selectedSampleRef.sampleType === this.activeSampleType
        ? this.selectedSampleRef.sampleId
        : null;
    },

    activeSelectedSegmentationResultId() {
      return (
        this.selectedSegmentationResultRef.sampleType === this.activeSampleType &&
        this.selectedSegmentationResultRef.sampleId === this.activeSelectedSampleId
      )
        ? this.selectedSegmentationResultRef.resultadoId
        : null;
    },
  },

  methods: {
    confirmPendingDraftNavigation() {
      if (
        this.seccion === "segmentacion" &&
        this.$refs.mainContent?.hasPendingDraftWork &&
        !this.$refs.mainContent.confirmDiscardDraftChanges()
      ) {
        return false;
      }

      return true;
    },

    requestSectionChange(nextSection) {
      if (nextSection === this.seccion) return;
      if (!VALID_SECTIONS.includes(nextSection)) return;

      if (!this.confirmPendingDraftNavigation()) return;

      this.seccion = nextSection;
    },

    onSelectPatient(patientId) {
      if (patientId === this.selectedPatientId) return;
      if (!this.confirmPendingDraftNavigation()) return;

      this.selectedPatientId = patientId;
      this.selectedCaseId = null;
      this.clearSelectedSample();
    },

    onSelectCase(caseId) {
      if (caseId === this.selectedCaseId) return;
      if (!this.confirmPendingDraftNavigation()) return;

      this.selectedCaseId = caseId;
      this.clearSelectedSample();
    },

    onSampleTypeChanged(sampleType) {
      if (sampleType === this.activeSampleType) return;
      if (!this.confirmPendingDraftNavigation()) return;

      this.activeSampleType = sampleType;
      this.clearSelectedSample();
    },

    onSegmentationCompleted(payload) {
      if (payload?.caseId !== this.selectedCaseId) return;

      if (
        payload?.resultadoId &&
        payload?.sampleType === this.activeSampleType &&
        payload?.muestraId === this.activeSelectedSampleId
      ) {
        this.onSegmentationResultSelected({
          sampleType: payload.sampleType,
          sampleId: payload.muestraId,
          resultadoId: payload.resultadoId,
        });
      }

      this.$refs.sideBar?.refrescarResumenCaso?.(payload.caseId);
    },

    onSampleSelected(payload) {
      const nextSampleType = payload?.sampleType || null;
      const nextSampleId = payload?.sampleId || null;
      const sampleChanged =
        this.selectedSampleRef.sampleType !== nextSampleType ||
        this.selectedSampleRef.sampleId !== nextSampleId;

      this.selectedSampleRef = {
        sampleType: nextSampleType,
        sampleId: nextSampleId,
      };

      if (sampleChanged) {
        this.clearSelectedSegmentationResult();
      }
    },

    onSegmentationResultSelected(payload) {
      const sampleType = payload?.sampleType || null;
      const sampleId = payload?.sampleId || null;

      if (
        sampleType !== this.activeSampleType ||
        sampleId !== this.activeSelectedSampleId
      ) {
        return;
      }

      this.selectedSegmentationResultRef = {
        sampleType,
        sampleId,
        resultadoId: payload?.resultadoId || null,
      };
    },

    clearSelectedSample() {
      this.selectedSampleRef = {
        sampleType: null,
        sampleId: null,
      };
      this.clearSelectedSegmentationResult();
    },

    clearSelectedSegmentationResult() {
      this.selectedSegmentationResultRef = {
        sampleType: null,
        sampleId: null,
        resultadoId: null,
      };
    },

    onContextInvalid(payload) {
      const level = payload?.level;

      if (level === "patient") {
        this.selectedPatientId = null;
        this.selectedCaseId = null;
        this.clearSelectedSample();
        return;
      }

      if (level === "case") {
        this.selectedCaseId = null;
        this.clearSelectedSample();
        return;
      }

      if (level === "sample") {
        this.clearSelectedSample();
        return;
      }

      if (level === "result") {
        this.clearSelectedSegmentationResult();
      }
    },

    persistUiContext() {
      if (typeof window === "undefined") return;

      const context = {
        version: UI_CONTEXT_VERSION,
        activeTab: this.seccion,
        patientId: this.selectedPatientId,
        caseId: this.selectedCaseId,
        sampleType: this.activeSampleType,
        sampleId: this.activeSelectedSampleId,
        segmentationResultId: this.activeSelectedSegmentationResultId,
      };

      window.sessionStorage.setItem(
        UI_CONTEXT_STORAGE_KEY,
        JSON.stringify(context)
      );
    },
  },

  watch: {
    seccion: "persistUiContext",
    selectedPatientId: "persistUiContext",
    selectedCaseId: "persistUiContext",
    activeSampleType: "persistUiContext",
    selectedSampleRef: {
      handler: "persistUiContext",
      deep: true,
    },
    selectedSegmentationResultRef: {
      handler: "persistUiContext",
      deep: true,
    },
  },

  mounted() {
    this.persistUiContext();
  },
};
</script>

<style>
* {
    box-sizing: border-box;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
}

html {
    min-height: 100%;
}

body {
    margin: 0;
    background: #f0f2f5;
    color: #2c3e50;
    min-height: 100vh;
    overflow: auto;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}

.app {
    display: flex;
    align-items: stretch;
    background: #f0f2f5;
    min-height: calc(100vh - 60px);
    min-width: 0;
    width: 100%;
}

@media (max-width: 1023px) {
    .app {
        flex-direction: column;
    }
}

.placeholder-view {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    padding: 40px;
}

.placeholder-content {
    text-align: center;
    background: white;
    padding: 60px 80px;
    border-radius: 20px;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
    max-width: 500px;
    animation: fadeInUp 0.6s ease;
}

@keyframes fadeInUp {
    from {
        opacity: 0;
        transform: translateY(30px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.placeholder-icon {
    font-size: 80px;
    margin-bottom: 20px;
    animation: float 3s ease-in-out infinite;
}

@keyframes float {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-10px); }
}

.placeholder-content h2 {
    margin: 0 0 12px 0;
    font-size: 32px;
    font-weight: 700;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.placeholder-content p {
    margin: 0 0 24px 0;
    color: #666;
    font-size: 16px;
    line-height: 1.6;
}

.placeholder-badge {
    display: inline-block;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 10px 24px;
    border-radius: 20px;
    font-size: 14px;
    font-weight: 600;
    letter-spacing: 0.5px;
    box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
}

::-webkit-scrollbar {
    width: 8px;
    height: 8px;
}

::-webkit-scrollbar-track {
    background: #f1f1f1;
    border-radius: 10px;
}

::-webkit-scrollbar-thumb {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 10px;
}

::-webkit-scrollbar-thumb:hover {
    background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
}

.text-center {
    text-align: center;
}

.mt-auto {
    margin-top: auto;
}

.full-width {
    width: 100%;
}

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}

.loading {
    animation: pulse 1.5s ease-in-out infinite;
}

.skeleton {
    background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
    background-size: 200% 100%;
    animation: loading 1.5s ease-in-out infinite;
}

@keyframes loading {
    0% { background-position: 200% 0; }
    100% { background-position: -200% 0; }
}

*:focus-visible {
    outline: 3px solid #667eea;
    outline-offset: 2px;
}

::selection {
    background: #667eea;
    color: white;
}

::-moz-selection {
    background: #667eea;
    color: white;
}
</style>
