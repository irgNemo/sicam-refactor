<template>
  <!-- BARRA SUPERIOR -->
  <TopBar
    :seccion="seccion"
    @change-section="seccion = $event"
  />

  <!-- CONTENIDO PRINCIPAL -->
  <div class="app">

    <!-- SIDEBAR (solo en segmentación) -->
    <SideBar
      v-if="seccion === 'segmentacion'"
      ref="sideBar"
      @select-patient="onSelectPatient"
      @select-case="onSelectCase"
    />

    <!-- CONTENIDO CENTRAL -->
    <MainContent
      v-if="seccion === 'segmentacion'"
      :patientId="selectedPatientId"
      :caseId="selectedCaseId"
      @segmentation-completed="onSegmentationCompleted"
    />

    <div v-if="seccion === 'analisis'" class="placeholder-view">
      <div class="placeholder-content">
        <div class="placeholder-icon">🔍</div>
        <h2>Análisis</h2>
        <p>Este módulo está en desarrollo</p>
        <div class="placeholder-badge">Próximamente</div>
      </div>
    </div>

    <div v-if="seccion === 'caracterizacion'" class="placeholder-view">
      <div class="placeholder-content">
        <div class="placeholder-icon">📊</div>
        <h2>Caracterización</h2>
        <p>Este módulo está en desarrollo</p>
        <div class="placeholder-badge">Próximamente</div>
      </div>
    </div>

    <!-- NUEVA SECCIÓN DE REGISTRO -->
    <RegistroView v-if="seccion === 'registro'" />

  </div>
</template>

<script>
import TopBar from "./components/TopBar.vue";
import SideBar from "./components/SideBar.vue";
import MainContent from "./components/MainContent.vue";
import RegistroView from "./views/RegistroView.vue";

export default {
  name: "App",

  components: {
    TopBar,
    SideBar,
    MainContent,
    RegistroView,
  },

  data() {
    return {
      // Sección activa
      seccion: "segmentacion",

      // Estado global de selección
      selectedPatientId: null,
      selectedCaseId: null,
    };
  },

  methods: {
    // Recibe paciente desde SideBar
    onSelectPatient(patientId) {
      this.selectedPatientId = patientId;
      this.selectedCaseId = null;
    },

    // Recibe caso desde SideBar
    onSelectCase(caseId) {
      this.selectedCaseId = caseId;
    },

    onSegmentationCompleted(payload) {
      if (payload?.caseId !== this.selectedCaseId) return;

      this.$refs.sideBar?.refrescarResumenCaso?.(payload.caseId);
    },
  },

  watch: {
    // Limpieza de estado al cambiar de sección
    seccion(nueva) {
      if (nueva !== "segmentacion") {
        this.selectedPatientId = null;
        this.selectedCaseId = null;
      }
    },
  },
};
</script>


<style>
/* =========================================
   CONFIGURACIÓN BASE
   ========================================= */
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

/* =========================================
   LAYOUT GENERAL
   ========================================= */
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

/* =========================================
   PLACEHOLDER VIEWS (Módulos en desarrollo)
   ========================================= */
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

/* =========================================
   SCROLLBAR PERSONALIZADA
   ========================================= */
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

/* =========================================
   UTILIDADES GLOBALES
   ========================================= */
.text-center {
    text-align: center;
}

.mt-auto {
    margin-top: auto;
}

.full-width {
    width: 100%;
}

/* Animaciones globales */
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}

.loading {
    animation: pulse 1.5s ease-in-out infinite;
}

/* Estados de carga */
.skeleton {
    background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
    background-size: 200% 100%;
    animation: loading 1.5s ease-in-out infinite;
}

@keyframes loading {
    0% { background-position: 200% 0; }
    100% { background-position: -200% 0; }
}

/* Focus visible para accesibilidad */
*:focus-visible {
    outline: 3px solid #667eea;
    outline-offset: 2px;
}

/* Selección de texto */
::selection {
    background: #667eea;
    color: white;
}

::-moz-selection {
    background: #667eea;
    color: white;
}
</style>
