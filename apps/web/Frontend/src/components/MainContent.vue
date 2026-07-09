<template>
  <main class="content">

    <!-- HEADER -->
    <header class="page-header">
      <div class="header-left">
        <h2 class="page-title">
          Resultados del Análisis
        </h2>
        <div class="breadcrumb">
          <span v-if="patientId" class="breadcrumb-item">
            👤 Paciente {{ patientId }}
          </span>
          <span v-if="caseId" class="breadcrumb-separator">›</span>
          <span v-if="caseId" class="breadcrumb-item active">
            📋 Caso {{ caseId }}
          </span>
          <span v-if="!patientId" class="breadcrumb-placeholder">
            Seleccione un paciente y un caso para comenzar
          </span>
        </div>
      </div>

      <div class="header-actions">
        <button class="btn-action csv">
          <span class="btn-icon">⬇</span>
          Exportar CSV
        </button>
        <button class="btn-action pdf">
          <span class="btn-icon">📄</span>
          Generar PDF
        </button>
      </div>
    </header>

    <div class="layout-grid">

      <!-- GALERÍA -->
      <div class="gallery-column">
        <div class="gallery-header">
          <h3>Galería</h3>
          <span class="gallery-count">{{ imagenes.length }}</span>
        </div>

        <div class="gallery-grid">
          <div
            v-for="muestra in imagenes"
            :key="muestra.id_muestra"
            class="thumb"
            :class="{ active: muestra === imagenSeleccionada }"
            @click="selectImagen(muestra)"
          >
            <img
              :src="muestra.imagen"
              alt="Muestra"
            />
            <div class="thumb-overlay">
              <span class="thumb-id">#{{ muestra.id_muestra }}</span>
            </div>
          </div>

          <div v-if="imagenes.length === 0" class="empty-gallery">
            <div class="empty-icon">🖼️</div>
            <p>No hay imágenes disponibles</p>
            <span>Seleccione un caso válido</span>
          </div>
        </div>
      </div>

      <!-- VISOR -->
      <div class="viewer-column">

        <!-- TARJETA PRINCIPAL -->
        <div class="card main-card">
          <div class="card-header">
            <div class="card-title-section">
              <h3>
                {{ imagenSeleccionada ? 'Muestra #' + imagenSeleccionada.id_muestra : 'Vista previa' }}
              </h3>
              <span v-if="imagenSeleccionada" class="card-subtitle">
                Análisis microscópico
              </span>
            </div>
            <div class="card-tools">
              <button class="tool-btn" title="Editar">
                <span>✏️</span>
              </button>
              <button class="tool-btn" title="Limpiar">
                <span>🧹</span>
              </button>
              <button class="tool-btn danger" title="Eliminar">
                <span>🗑️</span>
              </button>
              <button class="tool-btn success" title="Aprobar">
                <span>✔️</span>
              </button>
            </div>
          </div>

          <div class="card-body split-view">

            <!-- IMAGEN -->
            <div class="image-container">
              <div class="img-placeholder">
                <img
                  v-if="imagenSeleccionada"
                  :src="imagenSeleccionada.imagen"
                  class="main-image"
                  alt="Muestra microscópica"
                />
                <div
                  v-else
                  class="empty-image-state"
                >
                  <div class="empty-image-icon">🔬</div>
                  <p>Seleccione una imagen de la galería</p>
                </div>

                <div v-if="imagenSeleccionada" class="img-overlay">
                  <span class="overlay-badge original">Original</span>
                  <span class="overlay-badge segmented">Segmentación</span>
                </div>
              </div>

              <div v-if="imagenSeleccionada" class="image-controls">
                <button class="control-btn">
                  <span>🔍</span> Zoom
                </button>
                <button class="control-btn">
                  <span>↻</span> Rotar
                </button>
                <button class="control-btn">
                  <span>⊟</span> Ajustar
                </button>
              </div>
            </div>

            <!-- DATOS -->
            <div class="data-container">
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

                <tbody v-if="resultadoImagenSeleccionada">
                  <tr class="data-row nucleos">
                    <td>
                      <span class="structure-icon">🟢</span>
                      Núcleos
                    </td>
                    <td class="count">{{ resultadoImagenSeleccionada.nucleos }}</td>
                  </tr>
                  <tr class="data-row membranas">
                    <td>
                      <span class="structure-icon">🟤</span>
                      Membranas
                    </td>
                    <td class="count">{{ resultadoImagenSeleccionada.membranas }}</td>
                  </tr>
                  <tr class="data-row micronucleos highlight">
                    <td>
                      <span class="structure-icon">🔴</span>
                      Micronúcleos
                    </td>
                    <td class="count critical">{{ resultadoImagenSeleccionada.micronucleos }}</td>
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

              <div v-if="imagenSeleccionada" class="segmentation-panel">
                <button
                  class="btn-segment full-width"
                  :disabled="segmentacionLoading"
                  @click="ejecutarSegmentacion"
                >
                  {{ segmentacionLoading ? 'Segmentando...' : 'Ejecutar segmentacion' }}
                </button>

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

                <div v-if="resultadoSegmentacionActivo" class="normalized-panel">
                  <div class="history-title">
                    Resultado normalizado
                    <span v-if="resultadoNormalizadoActivo">
                      v{{ resultadoNormalizadoActivo.version }}
                    </span>
                  </div>

                  <div v-if="resultadoNormalizadoActivo" class="segmentation-status neutral">
                    <div class="status-grid">
                      <span>Tipo</span>
                      <strong>{{ resultadoNormalizadoActivo.sample_type }}</strong>
                      <span>Total</span>
                      <strong>{{ totalObjetosNormalizados }}</strong>
                    </div>

                    <div class="normalized-section">
                      <div class="normalized-subtitle">Conteo por etiqueta</div>
                      <div v-if="conteosNormalizados.length" class="label-counts">
                        <span
                          v-for="conteo in conteosNormalizados"
                          :key="conteo.label"
                          class="label-count"
                        >
                          {{ conteo.label }}: {{ conteo.count }}
                        </span>
                      </div>
                      <div v-else class="empty-normalized">
                        Sin etiquetas
                      </div>
                    </div>

                    <div class="normalized-section">
                      <div class="normalized-subtitle">Objetos</div>
                      <table v-if="objetosNormalizadosVisibles.length" class="normalized-table">
                        <thead>
                          <tr>
                            <th>ID</th>
                            <th>Etiqueta</th>
                            <th>Geometria</th>
                            <th>Puntos</th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr
                            v-for="objeto in objetosNormalizadosVisibles"
                            :key="objeto.id"
                          >
                            <td>{{ objeto.id }}</td>
                            <td>{{ objeto.label }}</td>
                            <td>{{ geometryType(objeto) }}</td>
                            <td>{{ geometryPointsCount(objeto) }}</td>
                          </tr>
                        </tbody>
                      </table>
                      <div v-else class="empty-normalized">
                        Sin objetos normalizados
                      </div>
                    </div>
                  </div>

                  <div v-else class="segmentation-status neutral">
                    Este resultado no tiene representacion normalizada.
                    <div class="status-grid legacy-count">
                      <span>Objetos heredados</span>
                      <strong>{{ conteoObjetosHeredadoActivo }}</strong>
                    </div>
                  </div>
                </div>

                <div class="segmentation-history">
                  <div class="history-title">
                    Historial persistido
                    <span v-if="historialSegmentacion.length">
                      {{ historialSegmentacion.length }}
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

                  <div v-else class="segmentation-status neutral">
                    <div class="status-title">
                      Ultimo resultado #{{ ultimoResultadoSegmentacion.id }}
                    </div>
                    <div class="status-grid">
                      <span>Estado</span>
                      <strong>{{ ultimoResultadoSegmentacion.estado }}</strong>
                      <span>Tipo</span>
                      <strong>{{ ultimoResultadoSegmentacion.tipo_muestra }}</strong>
                      <span>Fecha</span>
                      <strong>{{ formatearFechaResultado(ultimoResultadoSegmentacion.creado_en) }}</strong>
                      <span>Objetos</span>
                      <strong>{{ ultimoHistorialObjetosCount }}</strong>
                    </div>
                  </div>
                </div>
              </div>

              <button class="btn-review full-width">
                <span class="btn-icon">⚠️</span>
                Marcar para revisión manual
              </button>
            </div>

          </div>
        </div>

        <!-- TARJETA OBJETOS -->
        <div class="card objects-card">
          <div class="card-header-simple">
            <h3>Objetos Detectados</h3>
            <span class="objects-count">3 tipos</span>
          </div>

          <div class="objects-layout">

            <div class="objects-table-wrapper">
              <table class="obj-table">
                <thead>
                  <tr>
                    <th>Visible</th>
                    <th>Tipo de Objeto</th>
                    <th>Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  <tr class="obj-row">
                    <td>
                      <input type="checkbox" class="checkbox-custom" checked />
                    </td>
                    <td class="obj-type">
                      <span class="obj-icon nucleos">●</span>
                      Núcleos
                    </td>
                    <td>
                      <div class="obj-actions">
                        <button class="obj-btn" title="Editar">✏️</button>
                        <button class="obj-btn" title="Limpiar">🧹</button>
                      </div>
                    </td>
                  </tr>
                  <tr class="obj-row">
                    <td>
                      <input type="checkbox" class="checkbox-custom" checked />
                    </td>
                    <td class="obj-type">
                      <span class="obj-icon micronucleos">●</span>
                      Micronúcleos
                    </td>
                    <td>
                      <div class="obj-actions">
                        <button class="obj-btn" title="Editar">✏️</button>
                        <button class="obj-btn" title="Limpiar">🧹</button>
                      </div>
                    </td>
                  </tr>
                  <tr class="obj-row">
                    <td>
                      <input type="checkbox" class="checkbox-custom" checked />
                    </td>
                    <td class="obj-type">
                      <span class="obj-icon membranas">●</span>
                      Membranas
                    </td>
                    <td>
                      <div class="obj-actions">
                        <button class="obj-btn" title="Editar">✏️</button>
                        <button class="obj-btn" title="Limpiar">🧹</button>
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div class="objects-tools-panel">
              <div class="info-box">
                <div class="info-icon">💡</div>
                <p>Seleccione un objeto de la lista para editarlo o modificar su visibilidad</p>
              </div>
              <button class="btn-tool-large review">
                <span>✏️</span>
                Marcar revisión
              </button>
              <button class="btn-tool-large export">
                <span>⬆</span>
                Exportar Datos
              </button>
            </div>

          </div>
        </div>

      </div>
    </div>
  </main>
</template>

<script>
import apiClient from "../services/apiClient";
import {
  obtenerResultadosSegmentacion,
  segmentarMuestra,
} from "../services/segmentationService";

export default {
  name: "MainContent",

  props: {
    patientId: String,
    caseId: String,
  },

  data() {
    return {
      analisis: [],
      loading: true,
      imagenSeleccionada: null,
      segmentacionLoading: false,
      segmentacionResultado: null,
      segmentacionError: "",
      historialSegmentacion: [],
      historialLoading: false,
      historialError: "",
    };
  },

  computed: {
    analisisActual() {
      if (!this.patientId || !this.caseId) return null;

      return this.analisis.find(
        a =>
          String(a.id_paciente_fk) === String(this.patientId) &&
          String(a.id_caso_fk) === String(this.caseId)
      );
    },

    imagenes() {
      return this.analisisActual?.muestras_saliva || [];
    },

    resultadoImagenSeleccionada() {
      if (!this.imagenSeleccionada) return null;
      return this.imagenSeleccionada.resultados?.[0] || null;
    },

    segmentacionMetadata() {
      return this.segmentacionResultado?.resultado_segmentacion || null;
    },

    segmentacionObjetosCount() {
      const objetos = this.segmentacionResultado?.objetos;
      return Array.isArray(objetos) ? objetos.length : 0;
    },

    ultimoResultadoSegmentacion() {
      return this.historialSegmentacion[0] || null;
    },

    ultimoHistorialObjetosCount() {
      const objetos = this.ultimoResultadoSegmentacion?.respuesta_json?.objetos;
      return Array.isArray(objetos) ? objetos.length : 0;
    },

    resultadoSegmentacionActivo() {
      return this.ultimoResultadoSegmentacion || this.segmentacionResultado || null;
    },

    resultadoNormalizadoActivo() {
      return this.resultadoSegmentacionActivo?.resultado_normalizado || null;
    },

    totalObjetosNormalizados() {
      return this.resultadoNormalizadoActivo?.summary?.total_objects || 0;
    },

    conteosNormalizados() {
      const counts = this.resultadoNormalizadoActivo?.summary?.counts_by_label || {};
      return Object.entries(counts).map(([label, count]) => ({ label, count }));
    },

    objetosNormalizadosVisibles() {
      const objects = this.resultadoNormalizadoActivo?.objects;
      return Array.isArray(objects) ? objects.slice(0, 5) : [];
    },

    conteoObjetosHeredadoActivo() {
      const historicalObjects = this.resultadoSegmentacionActivo
        ?.respuesta_json
        ?.objetos;
      const immediateObjects = this.resultadoSegmentacionActivo?.objetos;

      if (Array.isArray(historicalObjects)) return historicalObjects.length;
      if (Array.isArray(immediateObjects)) return immediateObjects.length;
      return 0;
    },
  },

  watch: {
    imagenes(nuevas) {
      this.selectImagen(nuevas[0] || null);
    },
  },

  methods: {
    selectImagen(muestra) {
      this.imagenSeleccionada = muestra;
      this.segmentacionResultado = null;
      this.segmentacionError = "";
      this.segmentacionLoading = false;
      this.historialSegmentacion = [];
      this.historialError = "";
      this.historialLoading = false;

      if (muestra) {
        this.cargarHistorialSegmentacion(muestra.id_muestra);
      }
    },

    async cargarHistorialSegmentacion(muestraId) {
      this.historialLoading = true;
      this.historialError = "";

      try {
        const response = await obtenerResultadosSegmentacion(muestraId);

        if (this.imagenSeleccionada?.id_muestra === muestraId) {
          this.historialSegmentacion = Array.isArray(response.data)
            ? response.data
            : [];
        }
      } catch (error) {
        console.error("Error al cargar historial de segmentacion:", error);

        if (this.imagenSeleccionada?.id_muestra === muestraId) {
          this.historialSegmentacion = [];
          this.historialError =
            error.response?.data?.error || "No fue posible cargar el historial";
        }
      } finally {
        if (this.imagenSeleccionada?.id_muestra === muestraId) {
          this.historialLoading = false;
        }
      }
    },

    async ejecutarSegmentacion() {
      if (!this.imagenSeleccionada || this.segmentacionLoading) return;

      this.segmentacionLoading = true;
      this.segmentacionResultado = null;
      this.segmentacionError = "";

      try {
        const response = await segmentarMuestra(this.imagenSeleccionada.id_muestra);
        this.segmentacionResultado = response.data;
        await this.cargarHistorialSegmentacion(this.imagenSeleccionada.id_muestra);
      } catch (error) {
        console.error("Error al segmentar muestra:", error);
        this.segmentacionError =
          error.response?.data?.error || "No fue posible segmentar la muestra";
      } finally {
        this.segmentacionLoading = false;
      }
    },

    formatearFechaResultado(fecha) {
      if (!fecha) return "";
      return new Date(fecha).toLocaleString("es-MX");
    },

    geometryType(objeto) {
      return objeto.geometry?.type || "Sin geometria";
    },

    geometryPointsCount(objeto) {
      const points = objeto.geometry?.points;
      return Array.isArray(points) ? points.length : 0;
    },
  },

  mounted() {
    apiClient
      .get("/api/analisis/")
      .then((response) => {
        this.analisis = response.data;
      })
      .catch((error) => {
        console.error("Error API:", error);
      })
      .finally(() => {
        this.loading = false;
      });
  },
};
</script>

<style scoped>
.content {
  flex: 1;
  padding: 16px;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  background: #f8f9fa;
  height: 100vh;
}

/* HEADER */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 2px solid #e0e0e0;
  height: 60px;
}

.header-left {
  flex: 1;
}

.page-title {
  margin: 0 0 6px 0;
  font-size: 24px;
  font-weight: 700;
  color: #2c3e50;
}

.breadcrumb {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}

.breadcrumb-item {
  color: #666;
  padding: 4px 10px;
  background: #f0f4f8;
  border-radius: 6px;
}

.breadcrumb-item.active {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  font-weight: 500;
}

.breadcrumb-separator {
  color: #999;
}

.breadcrumb-placeholder {
  color: #999;
  font-style: italic;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.btn-action {
  padding: 10px 18px;
  border: 2px solid #e0e0e0;
  background: white;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  border-radius: 10px;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 8px;
  color: #2c3e50;
}

.btn-action:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.btn-action.csv:hover {
  border-color: #43a047;
  background: #e8f5e9;
}

.btn-action.pdf:hover {
  border-color: #e53935;
  background: #ffebee;
}

.btn-icon {
  font-size: 16px;
}

/* LAYOUT */
.layout-grid {
  display: flex;
  gap: 16px;
  height: auto;
  min-height: 0;
  overflow: visible;
}

/* GALERÍA */
.gallery-column {
  width: 240px;
  display: flex;
  flex-direction: column;
  background: white;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.gallery-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding-bottom: 10px;
  border-bottom: 2px solid #f0f0f0;
}

.gallery-header h3 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: #2c3e50;
}

.gallery-count {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 3px 10px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
}

.gallery-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  grid-auto-rows: 68px;
  gap: 10px;
  overflow-y: auto;
}

.thumb {
  cursor: pointer;
  border: 3px solid transparent;
  border-radius: 10px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  opacity: 0.7;
  overflow: hidden;
  position: relative;
  background: #f0f0f0;
}

.thumb:hover {
  opacity: 1;
  transform: scale(1.05);
}

.thumb.active {
  border-color: #667eea;
  opacity: 1;
  box-shadow: 0 4px 16px rgba(102, 126, 234, 0.4);
  transform: scale(1.05);
}

.thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.thumb-overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  background: linear-gradient(to top, rgba(0,0,0,0.7), transparent);
  padding: 4px;
  opacity: 0;
  transition: opacity 0.3s ease;
}

.thumb:hover .thumb-overlay,
.thumb.active .thumb-overlay {
  opacity: 1;
}

.thumb-id {
  color: white;
  font-size: 10px;
  font-weight: 600;
}

.empty-gallery {
  grid-column: 1 / -1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 30px 20px;
  text-align: center;
  color: #999;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 12px;
  opacity: 0.3;
}

.empty-gallery p {
  margin: 0 0 4px 0;
  font-size: 14px;
  font-weight: 500;
  color: #666;
}

.empty-gallery span {
  font-size: 12px;
  color: #999;
}

/* VISOR */
.viewer-column {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 16px;
  height: auto;
  min-height: 700px;
  overflow: hidden;
}

/* TARJETAS */
.card {
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.main-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.card-header {
  padding: 16px 20px;
  border-bottom: 2px solid #f0f0f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: linear-gradient(to right, #fafbfc, #ffffff);
  flex-shrink: 0;
}

.card-title-section h3 {
  font-size: 16px;
  margin: 0 0 2px 0;
  font-weight: 600;
  color: #2c3e50;
}

.card-subtitle {
  font-size: 12px;
  color: #999;
}

.card-tools {
  display: flex;
  gap: 8px;
}

.tool-btn {
  width: 36px;
  height: 36px;
  border: 2px solid #e0e0e0;
  background: white;
  cursor: pointer;
  border-radius: 8px;
  font-size: 16px;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.tool-btn:hover {
  background: #f0f4f8;
  transform: translateY(-2px);
}

.tool-btn.danger:hover {
  border-color: #ef5350;
  background: #ffebee;
}

.tool-btn.success:hover {
  border-color: #66bb6a;
  background: #e8f5e9;
}

/* VISTA DIVIDIDA */
.split-view {
  display: flex;
  gap: 20px;
  padding: 16px;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.image-container {
  flex: 1.6;
  display: flex;
  flex-direction: column;
  gap: 10px;
  height: 100%;
  min-height: 0;
}

.img-placeholder {
  position: relative;
  flex: 1;
  background: #f8f9fa;
  border: 2px dashed #e0e0e0;
  border-radius: 12px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  /*height: 100%;*/
  min-height: 0px;
}

.main-image {
  width: 100%;
  height: 100%;
  object-fit: contain;
  object-position: center;
}

.empty-image-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  color: #999;
}

.empty-image-icon {
  font-size: 64px;
  opacity: 0.3;
}

.empty-image-state p {
  margin: 0;
  font-size: 14px;
}

.img-overlay {
  position: absolute;
  bottom: 12px;
  left: 12px;
  right: 12px;
  display: flex;
  justify-content: space-between;
  gap: 8px;
}

.overlay-badge {
  font-size: 11px;
  padding: 6px 12px;
  border-radius: 8px;
  font-weight: 600;
  backdrop-filter: blur(10px);
}

.overlay-badge.original {
  background: rgba(66, 165, 245, 0.9);
  color: white;
}

.overlay-badge.segmented {
  background: rgba(255, 152, 0, 0.9);
  color: white;
}

.image-controls {
  display: flex;
  gap: 8px;
}

.control-btn {
  flex: 1;
  padding: 8px;
  border: 2px solid #e0e0e0;
  background: white;
  border-radius: 8px;
  cursor: pointer;
  font-size: 12px;
  font-weight: 500;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.control-btn:hover {
  border-color: #1e88e5;
  background: #e3f2fd;
}

/* DATOS */
.data-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.data-header {
  padding-bottom: 8px;
  border-bottom: 2px solid #f0f0f0;
}

.data-header h4 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: #2c3e50;
}

.data-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  font-size: 13px;
}

.data-table thead th {
  padding: 12px;
  background: #f8f9fa;
  border-bottom: 2px solid #e0e0e0;
  text-align: left;
  font-weight: 600;
  color: #666;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.data-table tbody td {
  padding: 14px 12px;
  border-bottom: 1px solid #f0f0f0;
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

.structure-icon {
  margin-right: 8px;
  font-size: 14px;
}

.count {
  font-weight: 700;
  font-size: 16px;
  text-align: right;
  color: #2c3e50;
}

.count.critical {
  color: #ef5350;
}

.no-data {
  text-align: center;
  padding: 40px 20px !important;
  color: #999;
}

.no-data-icon {
  font-size: 48px;
  margin-bottom: 12px;
  opacity: 0.3;
}

.segmentation-panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.btn-segment {
  padding: 12px;
  border: 2px solid #1e88e5;
  background: #1e88e5;
  color: white;
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  border-radius: 10px;
  transition: all 0.2s ease;
}

.btn-segment:hover:not(:disabled) {
  background: #1976d2;
  border-color: #1976d2;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(30, 136, 229, 0.25);
}

.btn-segment:disabled {
  cursor: wait;
  opacity: 0.7;
}

.segmentation-status {
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 12px;
  line-height: 1.4;
}

.segmentation-status.error {
  border: 1px solid #ffcdd2;
  background: #ffebee;
  color: #c62828;
}

.segmentation-status.success {
  border: 1px solid #c8e6c9;
  background: #e8f5e9;
  color: #2e7d32;
}

.segmentation-status.neutral {
  border: 1px solid #d9e2ec;
  background: #f8f9fa;
  color: #2c3e50;
}

.segmentation-history {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.normalized-panel {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.normalized-section {
  margin-top: 10px;
}

.normalized-subtitle {
  color: #666;
  font-size: 11px;
  font-weight: 700;
  margin-bottom: 6px;
  text-transform: uppercase;
}

.label-counts {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.label-count {
  background: #eef2ff;
  border: 1px solid #c7d2fe;
  border-radius: 10px;
  color: #374151;
  font-size: 11px;
  padding: 3px 8px;
}

.normalized-table {
  border-collapse: collapse;
  font-size: 11px;
  width: 100%;
}

.normalized-table th,
.normalized-table td {
  border-bottom: 1px solid #e0e0e0;
  padding: 6px 4px;
  text-align: left;
}

.normalized-table th {
  color: #666;
  font-weight: 700;
}

.empty-normalized {
  color: #777;
  font-size: 11px;
}

.legacy-count {
  margin-top: 8px;
}

.history-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  font-weight: 700;
  color: #2c3e50;
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
  grid-template-columns: 1fr auto;
  gap: 6px 10px;
}

.btn-review {
  padding: 14px;
  border: 2px solid #ff9800;
  background: white;
  color: #f57c00;
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  border-radius: 10px;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-top: auto;
}

.btn-review:hover {
  background: #fff3e0;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(255, 152, 0, 0.2);
}

.full-width {
  width: 100%;
}

/* OBJETOS */
.objects-card {
  height: 250px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
}

.card-header {
  padding: 8px 20px; /* Reducido para que sea más delgada */
  border-bottom: 2px solid #f0f0f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: linear-gradient(to right, #fafbfc, #ffffff);
  flex-shrink: 0;
  height: 50px;
}

.card-header-simple {
  padding: 10px 20px;
  border-bottom: 2px solid #f0f0f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: linear-gradient(to right, #fafbfc, #ffffff);
  flex-shrink: 0;
}

.card-header-simple h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #2c3e50;
}

.objects-count {
  font-size: 12px;
  color: #999;
  background: #f0f4f8;
  padding: 4px 12px;
  border-radius: 12px;
}

.objects-layout {
  display: flex;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.objects-table-wrapper {
  flex: 1;
  padding: 16px;
  padding-bottom: 100px;
  border-right: 2px solid #f0f0f0;
  overflow-y: auto;
  min-height: 0;
}

.obj-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  font-size: 13px;
}

.obj-table thead th {
  padding: 12px;
  background: #f8f9fa;
  border-bottom: 2px solid #e0e0e0;
  text-align: center;
  font-weight: 600;
  color: #666;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.obj-table tbody td {
  padding: 12px;
  border-bottom: 1px solid #f0f0f0;
  text-align: center;
}

.obj-row {
  transition: background 0.2s ease;
}

.obj-row:hover {
  background: #f8f9fa;
}

.checkbox-custom {
  width: 18px;
  height: 18px;
  cursor: pointer;
  accent-color: #667eea;
}

.obj-type {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-weight: 500;
}

.obj-icon {
  font-size: 16px;
}

.obj-icon.nucleos {
  color: #66bb6a;
}

.obj-icon.micronucleos {
  color: #ef5350;
}

.obj-icon.membranas {
  color: #8d6e63;
}

.obj-actions {
  display: flex;
  gap: 6px;
  justify-content: center;
}

.obj-btn {
  width: 32px;
  height: 32px;
  border: 2px solid #e0e0e0;
  background: white;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s ease;
}

.obj-btn:hover {
  background: #f0f4f8;
  border-color: #1e88e5;
  transform: scale(1.1);
}

.objects-tools-panel {
  width: 240px;
  padding: 16px;
  padding-bottom: 100px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  background: #fafbfc;
  overflow-y: auto;
}

.info-box {
  border: 2px solid #e3f2fd;
  border-radius: 10px;
  padding: 12px;
  font-size: 11px;
  background: white;
  color: #666;
  line-height: 1.5;
}

.info-icon {
  font-size: 20px;
  margin-bottom: 6px;
}

.info-box p {
  margin: 0;
}

.btn-tool-large {
  padding: 12px;
  border: 2px solid #e0e0e0;
  background: white;
  cursor: pointer;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 600;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.btn-tool-large:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.btn-tool-large.review:hover {
  border-color: #ff9800;
  background: #fff3e0;
}

.btn-tool-large.export:hover {
  border-color: #1e88e5;
  background: #e3f2fd;
}

.btn-tool-large span {
  font-size: 16px;
}
</style>
