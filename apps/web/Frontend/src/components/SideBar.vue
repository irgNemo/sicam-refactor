<template>
  <aside class="sidebar">
    <h2>Búsqueda de Casos</h2>

    <!-- BUSCADOR DE PACIENTE -->
    <div class="search-section">
      <label>Buscar Paciente</label>
      <div class="search-input-wrapper">
        <input
          type="text"
          v-model="busquedaPaciente"
          placeholder="Nombre, apellido o ID..."
          @input="filtrarPacientes"
        />
        <span class="search-icon">🔍</span>
      </div>

      <!-- LISTA DE PACIENTES FILTRADOS -->
      <div v-if="busquedaPaciente && pacientesFiltrados.length > 0" class="pacientes-dropdown">
        <div 
          v-for="paciente in pacientesFiltrados.slice(0, 5)" 
          :key="paciente.id_paciente"
          class="paciente-item"
          @click="seleccionarPaciente(paciente)"
        >
          <div class="paciente-info">
            <strong>{{ paciente.nombre }} {{ paciente.apellido }}</strong>
            <span class="paciente-id">ID: {{ paciente.identificacion }}</span>
          </div>
        </div>
      </div>

      <div v-if="busquedaPaciente && pacientesFiltrados.length === 0 && !loading" class="no-results">
        No se encontraron pacientes
      </div>
    </div>

    <!-- PACIENTE SELECCIONADO -->
    <div v-if="pacienteSeleccionado" class="paciente-card">
      <div class="paciente-header">
        <div class="paciente-avatar">{{ iniciales }}</div>
        <div class="paciente-datos">
          <h3>{{ pacienteSeleccionado.nombre }} {{ pacienteSeleccionado.apellido }}</h3>
          <p>ID: {{ pacienteSeleccionado.identificacion }}</p>
          <p class="edad">{{ calcularEdad(pacienteSeleccionado.fecha_nacimiento) }} años</p>
        </div>
      </div>
      <button class="btn-cambiar" @click="cambiarPaciente">
        Cambiar paciente
      </button>
    </div>

    <!-- CASOS DEL PACIENTE -->
    <div v-if="pacienteSeleccionado" class="casos-section">
      <label>Casos Disponibles ({{ casosDelPaciente.length }})</label>
      
      <div v-if="casosDelPaciente.length === 0" class="empty-state">
        <p>Este paciente no tiene casos registrados</p>
      </div>

      <div v-else class="casos-list">
        <div 
          v-for="caso in casosDelPaciente" 
          :key="caso.id_caso"
          class="caso-item"
          :class="{ active: casoSeleccionado === caso.id_caso }"
          @click="seleccionarCaso(caso)"
        >
          <div class="caso-header">
            <h4>{{ caso.titulo }}</h4>
            <span class="caso-badge" :class="'estado-' + caso.analisis[0]?.estado">
              {{ getEstadoTexto(caso.analisis[0]?.estado) }}
            </span>
          </div>
          <div class="caso-meta">
            <span class="caso-fecha">📅 {{ formatearFecha(caso.fecha_creacion) }}</span>
            <span class="caso-imagenes">🖼️ {{ caso.analisis[0]?.muestras_saliva?.length || 0 }} saliva</span>
          </div>
        </div>
      </div>
    </div>

    <!-- BOTÓN VER ANÁLISIS -->
    <button
      v-if="casoSeleccionado"
      class="btn-primary"
      @click="verAnalisis"
    >
      📊 Ver Análisis Completo
    </button>

    <!-- RESUMEN GLOBAL -->
    <div v-if="casoSeleccionado && showSalivaCaseSummary" class="summary-panel">
      <h3>Resumen del Caso</h3>

      <div v-if="resumenLoading" class="summary-status">
        Cargando resumen...
      </div>

      <div v-else-if="resumenError" class="summary-status error">
        {{ resumenError }}
      </div>

      <div class="summary-grid">
        <div class="summary-card images">
          <b>{{ resumen.imagenes }}</b>
          <span>Imágenes</span>
        </div>

        <div class="summary-card segmented">
          <b>{{ resumen.segmentadas }}</b>
          <span>Segmentadas</span>
        </div>

        <div class="summary-card pending">
          <b>{{ resumen.pendientes }}</b>
          <span>Pendientes</span>
        </div>

        <div class="summary-card membranes">
          <b>{{ resumen.membranas }}</b>
          <span>Membranas</span>
        </div>

        <div class="summary-card nuclei">
          <b>{{ resumen.nucleos }}</b>
          <span>Núcleos</span>
        </div>

        <div class="summary-card micro">
          <b>{{ resumen.micronucleos }}</b>
          <span>Micronúcleos</span>
        </div>
      </div>

      <div
        v-if="resumen.resultadoInvalido > 0"
        class="summary-invalid"
      >
        {{ resumen.resultadoInvalido }} con resultado no utilizable
      </div>
    </div>

    <div v-else-if="casoSeleccionado" class="summary-panel sample-type-note">
      <h3>Resumen del Caso</h3>
      <p>
        El resumen agregado actual corresponde a muestras de saliva. Las métricas
        de sangre se revisan desde la muestra seleccionada.
      </p>
    </div>
  </aside>
</template>

<script>
import apiClient from "../services/apiClient";
import { obtenerResumenSegmentacionCaso } from "../services/segmentationService";
import { SAMPLE_TYPES } from "../domain/segmentationTypes";

export default {
  name: "SideBar",

  props: {
    activeSampleType: {
      type: String,
      default: SAMPLE_TYPES.SALIVA,
    },
  },

  data() {
    return {
      // Datos API
      pacientes: [],
      casos: [],
      analisis: [],
      loading: true,

      // Estado UI
      busquedaPaciente: "",
      pacientesFiltrados: [],
      pacienteSeleccionado: null,
      casoSeleccionado: null,
      resumenLoading: false,
      resumenError: "",

      // Resumen
      resumen: {
        imagenes: 0,
        segmentadas: 0,
        pendientes: 0,
        resultadoInvalido: 0,
        membranas: 0,
        nucleos: 0,
        micronucleos: 0,
      },
    };
  },

  computed: {
    iniciales() {
      if (!this.pacienteSeleccionado) return "";
      const nombre = this.pacienteSeleccionado.nombre.charAt(0);
      const apellido = this.pacienteSeleccionado.apellido.charAt(0);
      return (nombre + apellido).toUpperCase();
    },

    casosDelPaciente() {
      if (!this.pacienteSeleccionado) return [];
      
      return this.casos
        .filter(c => c.paciente === this.pacienteSeleccionado.id_paciente)
        .map(caso => {
          const analisisDelCaso = this.analisis.filter(a => a.id_caso_fk === caso.id_caso);
          return {
            ...caso,
            analisis: analisisDelCaso
          };
        });
    },

    showSalivaCaseSummary() {
      return this.activeSampleType === SAMPLE_TYPES.SALIVA;
    },
  },

  methods: {
    async cargarDatos() {
      try {
        const [resPacientes, resCasos, resAnalisis] = await Promise.all([
          apiClient.get("/api/pacientes/"),
          apiClient.get("/api/casos/"),
          apiClient.get("/api/analisis/")
        ]);

        this.pacientes = resPacientes.data;
        this.casos = resCasos.data;
        this.analisis = resAnalisis.data;
      } catch (error) {
        console.error("Error al cargar datos:", error);
      } finally {
        this.loading = false;
      }
    },

    filtrarPacientes() {
      if (!this.busquedaPaciente.trim()) {
        this.pacientesFiltrados = [];
        return;
      }

      const busqueda = this.busquedaPaciente.toLowerCase();
      this.pacientesFiltrados = this.pacientes.filter(p => 
        p.nombre.toLowerCase().includes(busqueda) ||
        p.apellido.toLowerCase().includes(busqueda) ||
        p.identificacion.toLowerCase().includes(busqueda)
      );
    },

    seleccionarPaciente(paciente) {
      this.pacienteSeleccionado = paciente;
      this.busquedaPaciente = "";
      this.pacientesFiltrados = [];
      this.casoSeleccionado = null;
      this.resetResumen();
      
      this.$emit("select-patient", paciente.id_paciente);
    },

    cambiarPaciente() {
      this.pacienteSeleccionado = null;
      this.casoSeleccionado = null;
      this.busquedaPaciente = "";
      this.resetResumen();
    },

    seleccionarCaso(caso) {
      this.casoSeleccionado = caso.id_caso;
      this.resetResumen();
      this.refrescarResumenCaso(caso.id_caso);
      this.$emit("select-case", caso.id_caso);
    },

    verAnalisis() {
      // Aquí podrías agregar lógica adicional si necesitas
      console.log("Ver análisis del caso:", this.casoSeleccionado);
    },

    resetResumen() {
      this.resumenLoading = false;
      this.resumenError = "";
      this.resumen = {
        imagenes: 0,
        segmentadas: 0,
        pendientes: 0,
        resultadoInvalido: 0,
        membranas: 0,
        nucleos: 0,
        micronucleos: 0,
      };
    },

    async refrescarResumenCaso(casoId = this.casoSeleccionado) {
      if (!casoId) return;

      this.resumenLoading = true;
      this.resumenError = "";

      try {
        const response = await obtenerResumenSegmentacionCaso(casoId);
        const data = response.data || {};
        const counts = data.counts_by_label || {};

        if (this.casoSeleccionado !== casoId) return;

        this.resumen = {
          imagenes: data.total_muestras || 0,
          segmentadas: data.muestras_segmentadas || 0,
          pendientes: data.muestras_pendientes || 0,
          resultadoInvalido: data.muestras_resultado_invalido || 0,
          membranas: counts.membrana || 0,
          nucleos: counts.nucleo || 0,
          micronucleos: counts.micronucleo || 0,
        };
      } catch (error) {
        console.error("Error al cargar resumen de segmentacion:", error);

        if (this.casoSeleccionado === casoId) {
          this.resumenError = "No fue posible cargar el resumen del caso";
        }
      } finally {
        if (this.casoSeleccionado === casoId) {
          this.resumenLoading = false;
        }
      }
    },

    calcularEdad(fechaNacimiento) {
      const hoy = new Date();
      const nacimiento = new Date(fechaNacimiento);
      let edad = hoy.getFullYear() - nacimiento.getFullYear();
      const mes = hoy.getMonth() - nacimiento.getMonth();
      
      if (mes < 0 || (mes === 0 && hoy.getDate() < nacimiento.getDate())) {
        edad--;
      }
      
      return edad;
    },

    formatearFecha(fecha) {
      const date = new Date(fecha);
      return date.toLocaleDateString('es-MX', { 
        day: '2-digit', 
        month: 'short', 
        year: 'numeric' 
      });
    },

    getEstadoTexto(estado) {
      const estados = { 0: 'Abierto', 1: 'En Proceso', 2: 'Cerrado' };
      return estados[estado] || 'Desconocido';
    }
  },

  mounted() {
    this.cargarDatos();
  }
};
</script>

<style scoped>
.sidebar {
  width: clamp(300px, 24vw, 340px);
  flex: 0 0 clamp(300px, 24vw, 340px);
  background: #ffffff;
  padding: 20px;
  border-right: 1px solid #e0e0e0;
  overflow-y: auto;
  min-height: calc(100vh - 60px);
  min-width: 0;
}

.sidebar h2 {
  font-size: 18px;
  margin-bottom: 20px;
  color: #2c3e50;
}

/* BÚSQUEDA */
.search-section {
  position: relative;
  margin-bottom: 20px;
}

.search-section label {
  display: block;
  font-size: 12px;
  color: #666;
  margin-bottom: 8px;
  font-weight: 500;
}

.search-input-wrapper {
  position: relative;
}

.search-input-wrapper input {
  width: 100%;
  padding: 10px 40px 10px 12px;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  font-size: 14px;
  transition: all 0.2s ease;
}

.search-input-wrapper input:focus {
  outline: none;
  border-color: #1e88e5;
}

.search-icon {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  opacity: 0.5;
}

/* DROPDOWN PACIENTES */
.pacientes-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
  max-height: 300px;
  overflow-y: auto;
  z-index: 100;
  margin-top: 4px;
}

.paciente-item {
  padding: 12px;
  cursor: pointer;
  border-bottom: 1px solid #f0f0f0;
  transition: background 0.2s ease;
}

.paciente-item:hover {
  background: #f8f9fa;
}

.paciente-item:last-child {
  border-bottom: none;
}

.paciente-info strong {
  display: block;
  color: #2c3e50;
  font-size: 14px;
}

.paciente-id {
  display: block;
  color: #999;
  font-size: 12px;
  margin-top: 2px;
}

.no-results {
  padding: 12px;
  text-align: center;
  color: #999;
  font-size: 13px;
  background: #f8f9fa;
  border-radius: 8px;
  margin-top: 8px;
}

/* PACIENTE SELECCIONADO */
.paciente-card {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 16px;
  border-radius: 12px;
  color: white;
  margin-bottom: 20px;
}

.paciente-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.paciente-avatar {
  width: 50px;
  height: 50px;
  background: rgba(255,255,255,0.2);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  font-weight: bold;
  color: white;
}

.paciente-datos h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.paciente-datos p {
  margin: 2px 0;
  font-size: 12px;
  opacity: 0.9;
}

.edad {
  font-size: 11px;
  opacity: 0.8;
}

.btn-cambiar {
  width: 100%;
  padding: 8px;
  background: rgba(255,255,255,0.2);
  border: 1px solid rgba(255,255,255,0.3);
  color: white;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s ease;
}

.btn-cambiar:hover {
  background: rgba(255,255,255,0.3);
}

/* CASOS */
.casos-section {
  margin-bottom: 20px;
}

.casos-section label {
  display: block;
  font-size: 12px;
  color: #666;
  margin-bottom: 10px;
  font-weight: 500;
}

.empty-state {
  text-align: center;
  padding: 20px;
  color: #999;
  font-size: 13px;
}

.casos-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.caso-item {
  padding: 12px;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.caso-item:hover {
  border-color: #1e88e5;
  background: #f8f9fa;
}

.caso-item.active {
  border-color: #1e88e5;
  background: #e3f2fd;
}

.caso-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 8px;
}

.caso-header h4 {
  margin: 0;
  font-size: 14px;
  color: #2c3e50;
  flex: 1;
}

.caso-badge {
  padding: 3px 8px;
  border-radius: 12px;
  font-size: 10px;
  font-weight: 500;
  white-space: nowrap;
}

.estado-0 {
  background: #e3f2fd;
  color: #1976d2;
}

.estado-1 {
  background: #fff3e0;
  color: #f57c00;
}

.estado-2 {
  background: #e8f5e9;
  color: #388e3c;
}

.caso-meta {
  display: flex;
  gap: 12px;
  font-size: 11px;
  color: #666;
}

/* BOTÓN PRINCIPAL */
.btn-primary {
  width: 100%;
  padding: 14px;
  background: #1e88e5;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s ease;
  margin-bottom: 20px;
}

.btn-primary:hover {
  background: #1976d2;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(30, 136, 229, 0.3);
}

/* RESUMEN */
.summary-panel {
  background: #f8f9fa;
  padding: 16px;
  border-radius: 12px;
  border: 1px solid #e0e0e0;
}

.summary-panel h3 {
  margin: 0 0 12px 0;
  font-size: 14px;
  color: #2c3e50;
  text-align: center;
}

.summary-status {
  background: #eef4ff;
  border-radius: 8px;
  color: #3b5b8a;
  font-size: 12px;
  margin-bottom: 10px;
  padding: 8px;
  text-align: center;
}

.summary-status.error {
  background: #ffebee;
  color: #c62828;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}

.summary-card {
  padding: 14px 10px;
  border-radius: 10px;
  text-align: center;
  color: white;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.summary-card b {
  display: block;
  font-size: 24px;
  font-weight: 600;
  margin-bottom: 4px;
}

.summary-card span {
  font-size: 11px;
  opacity: 0.9;
}

.summary-card.images {
  background: linear-gradient(135deg, #42a5f5, #1e88e5);
}

.summary-card.membranes {
  background: linear-gradient(135deg, #8d6e63, #6d4c41);
}

.summary-card.nuclei {
  background: linear-gradient(135deg, #66bb6a, #43a047);
}

.summary-card.micro {
  background: linear-gradient(135deg, #ef5350, #e53935);
}

.summary-card.segmented {
  background: linear-gradient(135deg, #26a69a, #00897b);
}

.summary-card.pending {
  background: linear-gradient(135deg, #ffb74d, #fb8c00);
}

.summary-invalid {
  background: #fff8e1;
  border: 1px solid #ffe082;
  border-radius: 8px;
  color: #8a6d1d;
  font-size: 12px;
  margin-top: 10px;
  padding: 8px;
  text-align: center;
}

.sample-type-note p {
  color: #52606d;
  font-size: 12px;
  line-height: 1.4;
  margin: 0;
  text-align: center;
}

@media (max-width: 1439px) and (min-width: 1024px) {
  .sidebar {
    width: clamp(260px, 22vw, 280px);
    flex-basis: clamp(260px, 22vw, 280px);
    padding: 16px;
  }

  .sidebar h2 {
    font-size: 16px;
    margin-bottom: 14px;
  }

  .search-section,
  .paciente-card,
  .casos-section,
  .btn-primary {
    margin-bottom: 14px;
  }

  .paciente-card,
  .summary-panel {
    padding: 12px;
  }

  .summary-grid {
    gap: 8px;
  }

  .summary-card {
    padding: 10px 8px;
  }
}

@media (max-width: 1023px) {
  .sidebar {
    border-bottom: 1px solid #e0e0e0;
    border-right: 0;
    flex: 0 0 auto;
    max-height: 45vh;
    min-height: 0;
    padding: 12px;
    width: 100%;
  }

  .summary-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}
</style>
