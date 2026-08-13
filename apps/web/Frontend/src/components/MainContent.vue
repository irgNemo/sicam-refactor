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
              <div ref="imageFrame" class="img-placeholder">
                <div
                  v-if="imagenSeleccionada"
                  class="image-transform-layer"
                  :style="imageTransformStyle"
                >
                  <img
                    ref="mainImage"
                    :src="imagenSeleccionada.imagen"
                    class="main-image"
                    alt="Muestra microscópica"
                    @load="onMainImageLoad"
                  />
                  <svg
                    v-if="shouldShowSegmentationOverlay"
                    class="segmentation-svg-overlay"
                    :width="imageRenderedSize.width"
                    :height="imageRenderedSize.height"
                    :viewBox="`0 0 ${imageRenderedSize.width} ${imageRenderedSize.height}`"
                  >
                    <polygon
                      v-for="polygon in overlayPolygons"
                      :key="polygon.key"
                      :points="polygon.points"
                      class="segmentation-polygon"
                      :style="{ fill: polygon.fill, stroke: polygon.stroke }"
                    />
                  </svg>
                </div>
                <div
                  v-if="!imagenSeleccionada"
                  class="empty-image-state"
                >
                  <div class="empty-image-icon">🔬</div>
                  <p>Seleccione una imagen de la galería</p>
                </div>
              </div>

              <div v-if="imagenSeleccionada" class="image-controls">
                <button class="control-btn" @click="zoomImage">
                  <span>🔍</span> Zoom {{ Math.round(imageZoom * 100) }}%
                </button>
                <button class="control-btn" @click="rotateImage">
                  <span>↻</span> Rotar
                </button>
                <button class="control-btn" @click="resetImageView">
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

                <tbody v-if="resumenConteoActivo">
                  <tr class="data-row membranas">
                    <td>
                      <span
                        class="structure-dot"
                        :style="{ color: overlayColorForLabel('membrana').stroke }"
                      >●</span>
                      Membranas
                    </td>
                    <td class="count">{{ resumenConteoActivo.membranas }}</td>
                  </tr>
                  <tr class="data-row nucleos">
                    <td>
                      <span
                        class="structure-dot"
                        :style="{ color: overlayColorForLabel('nucleo').stroke }"
                      >●</span>
                      Núcleos
                    </td>
                    <td class="count">{{ resumenConteoActivo.nucleos }}</td>
                  </tr>
                  <tr class="data-row micronucleos highlight">
                    <td>
                      <span
                        class="structure-dot"
                        :style="{ color: overlayColorForLabel('micronucleo').stroke }"
                      >●</span>
                      Micronúcleos
                    </td>
                    <td class="count">{{ resumenConteoActivo.micronucleos }}</td>
                  </tr>
                  <tr class="data-row total">
                    <td>
                      <span class="structure-total-symbol">Σ</span>
                      Total
                    </td>
                    <td class="count">{{ resumenConteoActivo.total }}</td>
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

              <button class="btn-review full-width">
                <span class="btn-icon">⚠️</span>
                Marcar para revisión manual
              </button>
            </div>

          </div>
        </div>

        <!-- TARJETA CAPAS -->
        <div class="card objects-card">
          <div class="card-header-simple">
            <h3>Capas visibles</h3>
            <span class="objects-count">{{ overlayLabels.length }} tipos</span>
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
                <tbody v-if="overlayLabels.length">
                  <tr
                    v-for="label in overlayLabels"
                    :key="label.label"
                    class="obj-row"
                  >
                    <td>
                      <input
                        type="checkbox"
                        class="checkbox-custom"
                        :checked="label.visible"
                        @change="setOverlayLabelVisibility(label.label, $event.target.checked)"
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

            <div class="objects-tools-panel">
              <div class="info-box">
                <div class="info-icon">💡</div>
                <p>Active u oculte capas sin modificar los conteos del resultado</p>
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
  emits: ["segmentation-completed"],

  props: {
    patientId: {
      type: Number,
      default: null,
    },
    caseId: {
      type: Number,
      default: null,
    },
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
      imageNaturalSize: { width: 0, height: 0 },
      imageRenderedSize: { width: 0, height: 0 },
      imageZoom: 1,
      imageRotation: 0,
      overlayLabelVisibility: {},
      segmentationLabelPalette: {
        membrana: {
          stroke: "rgba(30, 136, 229, 0.92)",
          fill: "rgba(30, 136, 229, 0.16)",
        },
        micronucleo: {
          stroke: "rgba(67, 160, 71, 0.92)",
          fill: "rgba(67, 160, 71, 0.16)",
        },
        nucleo: {
          stroke: "rgba(239, 83, 80, 0.92)",
          fill: "rgba(239, 83, 80, 0.16)",
        },
      },
      overlayFallbackPalette: [
        { stroke: "rgba(30, 136, 229, 0.92)", fill: "rgba(30, 136, 229, 0.16)" },
        { stroke: "rgba(67, 160, 71, 0.92)", fill: "rgba(67, 160, 71, 0.16)" },
        { stroke: "rgba(239, 83, 80, 0.92)", fill: "rgba(239, 83, 80, 0.16)" },
        { stroke: "rgba(251, 140, 0, 0.92)", fill: "rgba(251, 140, 0, 0.16)" },
        { stroke: "rgba(142, 68, 173, 0.92)", fill: "rgba(142, 68, 173, 0.16)" },
        { stroke: "rgba(0, 137, 123, 0.92)", fill: "rgba(0, 137, 123, 0.16)" },
      ],
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

    resumenConteoActivo() {
      const summary = this.resultadoNormalizadoActivo?.summary;
      if (!summary || typeof summary !== "object") return null;

      const counts = summary.counts_by_label;
      if (!counts || typeof counts !== "object") return null;

      const countFor = (label) => {
        const value = Number(counts[label]);
        return Number.isFinite(value) ? value : 0;
      };

      const membranas = countFor("membrana");
      const nucleos = countFor("nucleo");
      const micronucleos = countFor("micronucleo");
      const totalValue = Number(summary.total_objects);
      const total = Number.isFinite(totalValue)
        ? totalValue
        : membranas + nucleos + micronucleos;

      return {
        membranas,
        nucleos,
        micronucleos,
        total,
      };
    },

    imageTransformStyle() {
      return {
        transform: `scale(${this.imageZoom}) rotate(${this.imageRotation}deg)`,
      };
    },

    overlayContainment() {
      const naturalWidth = this.imageNaturalSize.width;
      const naturalHeight = this.imageNaturalSize.height;
      const containerWidth = this.imageRenderedSize.width;
      const containerHeight = this.imageRenderedSize.height;

      if (
        !naturalWidth ||
        !naturalHeight ||
        !containerWidth ||
        !containerHeight
      ) {
        return {
          canProject: false,
          displayedSize: { width: 0, height: 0 },
          offsetX: 0,
          offsetY: 0,
          scaleX: null,
          scaleY: null,
        };
      }

      const imageAspect = naturalWidth / naturalHeight;
      const containerAspect = containerWidth / containerHeight;
      let displayedImageWidth;
      let displayedImageHeight;
      let offsetX;
      let offsetY;

      if (containerAspect > imageAspect) {
        displayedImageHeight = containerHeight;
        displayedImageWidth = containerHeight * imageAspect;
        offsetX = (containerWidth - displayedImageWidth) / 2;
        offsetY = 0;
      } else {
        displayedImageWidth = containerWidth;
        displayedImageHeight = containerWidth / imageAspect;
        offsetX = 0;
        offsetY = (containerHeight - displayedImageHeight) / 2;
      }

      return {
        canProject: true,
        displayedSize: {
          width: Math.round(displayedImageWidth),
          height: Math.round(displayedImageHeight),
        },
        offsetX,
        offsetY,
        scaleX: displayedImageWidth / naturalWidth,
        scaleY: displayedImageHeight / naturalHeight,
      };
    },

    overlayPolygons() {
      if (!this.imagenSeleccionada || !this.overlayContainment.canProject) {
        return [];
      }

      return this.overlayVisibleDrawableObjects
        .map((item, index) => {
          const color = this.overlayColorForLabel(item.label);
          return {
            key: this.overlayPolygonKey(item, index),
            points: item.points,
            fill: color.fill,
            stroke: color.stroke,
          };
        })
        .map(polygon => ({
          ...polygon,
          points: polygon.points
            .map(point => point.join(","))
            .join(" "),
        }));
    },

    shouldShowSegmentationOverlay() {
      return Boolean(
        this.imagenSeleccionada &&
        this.overlayContainment.canProject &&
        this.overlayPolygons.length
      );
    },

    overlayDrawableObjects() {
      const objects = Array.isArray(this.resultadoNormalizadoActivo?.objects)
        ? this.resultadoNormalizadoActivo.objects
        : [];

      return objects
        .filter(object => object.geometry?.type === "polygon")
        .map((object, index) => ({
          object,
          objectIndex: index,
          label: object.label || "desconocido",
          points: this.scalePolygonPoints(object.geometry?.points),
        }))
        .filter(item => item.points.length >= 3);
    },

    overlayVisibleDrawableObjects() {
      return this.overlayDrawableObjects.filter(
        item => this.overlayLabelVisibility[item.label] !== false
      );
    },

    overlayLabelNames() {
      return [...new Set(
        this.overlayDrawableObjects.map(item => item.label)
      )].sort();
    },

    overlayLabels() {
      return this.overlayLabelNames.map(label => {
        const color = this.overlayColorForLabel(label);
        return {
          label,
          count: this.overlayDrawableObjects.filter(
            item => item.label === label
          ).length,
          visible: this.overlayLabelVisibility[label] !== false,
          fill: color.fill,
          stroke: color.stroke,
        };
      });
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
      this.resetImageMeasurements();
      this.resetImageView();
      this.overlayLabelVisibility = {};

      if (muestra) {
        this.cargarHistorialSegmentacion(muestra.id_muestra);
        this.$nextTick(this.updateImageMeasurements);
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
          this.syncOverlayLabelVisibility();
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
        this.syncOverlayLabelVisibility();
        await this.cargarHistorialSegmentacion(this.imagenSeleccionada.id_muestra);
        this.$emit("segmentation-completed", {
          caseId: this.caseId,
          muestraId: this.imagenSeleccionada.id_muestra,
        });
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

    onMainImageLoad() {
      this.updateImageMeasurements();
    },

    resetImageMeasurements() {
      this.imageNaturalSize = { width: 0, height: 0 };
      this.imageRenderedSize = { width: 0, height: 0 };
    },

    updateImageMeasurements() {
      const image = this.$refs.mainImage;
      const frame = this.$refs.imageFrame;
      if (!image || !frame) return;

      this.imageNaturalSize = {
        width: image.naturalWidth || 0,
        height: image.naturalHeight || 0,
      };
      this.imageRenderedSize = {
        width: Math.round(frame.clientWidth),
        height: Math.round(frame.clientHeight),
      };
    },

    validPolygonPoints(points) {
      if (!Array.isArray(points)) return [];

      return points.filter(point => (
        Array.isArray(point) &&
        point.length >= 2 &&
        Number.isFinite(Number(point[0])) &&
        Number.isFinite(Number(point[1]))
      ));
    },

    scalePoint(point) {
      const containment = this.overlayContainment;

      if (!containment.canProject) return null;
      if (!this.validPolygonPoints([point]).length) return null;

      return [
        Math.round(containment.offsetX + Number(point[0]) * containment.scaleX),
        Math.round(containment.offsetY + Number(point[1]) * containment.scaleY),
      ];
    },

    scalePolygonPoints(points) {
      return this.validPolygonPoints(points)
        .map(point => this.scalePoint(point))
        .filter(Boolean);
    },

    overlayPolygonKey(item, index) {
      const normalizedId = item.object?.id ?? "sin-id";
      return `${item.objectIndex}-${index}-${normalizedId}-${item.label}`;
    },

    zoomImage() {
      this.imageZoom = Math.min(Number((this.imageZoom + 0.25).toFixed(2)), 2);
    },

    rotateImage() {
      this.imageRotation = (this.imageRotation + 90) % 360;
    },

    resetImageView() {
      this.imageZoom = 1;
      this.imageRotation = 0;
    },

    overlayColorForLabel(label) {
      if (this.segmentationLabelPalette[label]) {
        return this.segmentationLabelPalette[label];
      }

      const index = Math.max(this.overlayLabelNames.indexOf(label), 0);
      return this.overlayFallbackPalette[index % this.overlayFallbackPalette.length];
    },

    overlayLabelDisplayName(label) {
      const displayNames = {
        membrana: "Membranas",
        nucleo: "Núcleos",
        micronucleo: "Micronúcleos",
      };

      return displayNames[label] || label;
    },

    syncOverlayLabelVisibility() {
      const nextVisibility = {};

      this.overlayLabelNames.forEach(label => {
        nextVisibility[label] = true;
      });

      this.overlayLabelVisibility = nextVisibility;
    },

    setOverlayLabelVisibility(label, visible) {
      this.overlayLabelVisibility = {
        ...this.overlayLabelVisibility,
        [label]: visible,
      };
    },
  },

  mounted() {
    window.addEventListener("resize", this.updateImageMeasurements);

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

  beforeUnmount() {
    window.removeEventListener("resize", this.updateImageMeasurements);
  },
};
</script>

<style scoped>
.content {
  flex: 1 1 auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  background: #f8f9fa;
  min-height: 0;
  min-width: 0;
  overflow: visible;
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
  min-width: 0;
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
  align-items: start;
  display: grid;
  grid-template-columns: 240px minmax(0, 1fr);
  gap: 16px;
  flex: 1 1 auto;
  height: auto;
  min-height: 0;
  min-width: 0;
  overflow: visible;
  width: 100%;
}

/* GALERÍA */
.gallery-column {
  align-self: start;
  width: 100%;
  max-height: clamp(420px, 58vh, 620px);
  min-width: 0;
  display: flex;
  flex-direction: column;
  background: white;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.gallery-header {
  display: flex;
  flex-shrink: 0;
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
  flex: 1 1 auto;
  min-height: 0;
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
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
  height: auto;
  min-height: 0;
  overflow: visible;
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
  flex: 1 1 auto;
  display: flex;
  flex-direction: column;
  min-height: 0;
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
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(300px, 0.62fr);
  gap: 20px;
  padding: 16px;
  flex: 1 1 auto;
  min-height: 0;
  min-width: 0;
  overflow: visible;
}

.image-container {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
  height: auto;
  min-height: 0;
}

.img-placeholder {
  position: relative;
  flex: 0 0 auto;
  height: clamp(380px, 50vh, 560px);
  background: #f8f9fa;
  border: 2px dashed #e0e0e0;
  border-radius: 12px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 0;
}

.main-image {
  width: 100%;
  height: 100%;
  object-fit: contain;
  object-position: center;
}

.image-transform-layer {
  height: 100%;
  inset: 0;
  position: absolute;
  transform-origin: center center;
  width: 100%;
}

.segmentation-svg-overlay {
  display: block;
  height: 100%;
  inset: 0;
  pointer-events: none;
  position: absolute;
  width: 100%;
  z-index: 2;
}

.segmentation-polygon {
  fill: rgba(30, 136, 229, 0.16);
  stroke: rgba(30, 136, 229, 0.92);
  stroke-linejoin: round;
  stroke-width: 2;
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
  min-width: 0;
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
  font-weight: 700;
  font-size: 16px;
  text-align: right;
  color: #2c3e50;
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

.empty-normalized {
  color: #777;
  font-size: 11px;
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

.history-compact-card {
  border: 1px solid #d9e2ec;
  border-radius: 8px;
  background: #f8f9fa;
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
  height: auto;
  min-height: 170px;
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
  min-width: 0;
  overflow: visible;
}

.objects-table-wrapper {
  flex: 1;
  padding: 16px;
  border-right: 2px solid #f0f0f0;
  overflow-y: auto;
  min-height: 0;
  min-width: 0;
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
  flex: 0 0 240px;
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

@media (max-width: 1439px) and (min-width: 1024px) {
  .content {
    padding: 12px;
  }

  .page-header {
    height: auto;
    margin-bottom: 12px;
    padding-bottom: 10px;
  }

  .page-title {
    font-size: 20px;
  }

  .header-actions {
    gap: 8px;
  }

  .btn-action {
    padding: 8px 12px;
  }

  .layout-grid {
    gap: 12px;
    grid-template-columns: minmax(176px, 196px) minmax(0, 1fr);
  }

  .gallery-column {
    max-height: clamp(360px, 56vh, 500px);
    padding: 12px;
  }

  .gallery-grid {
    gap: 8px;
    grid-auto-rows: 64px;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .viewer-column {
    gap: 12px;
  }

  .main-card {
    min-height: 0;
  }

  .img-placeholder {
    height: clamp(320px, 46vh, 460px);
  }

  .card-header,
  .card-header-simple {
    padding: 10px 14px;
  }

  .split-view {
    gap: 12px;
    grid-template-columns: minmax(0, 1fr) minmax(280px, 320px);
    padding: 12px;
  }

  .data-container,
  .segmentation-panel {
    gap: 10px;
  }

  .segmentation-status {
    padding: 8px 10px;
  }

  .objects-card {
    min-height: 150px;
  }

  .objects-table-wrapper,
  .objects-tools-panel {
    padding: 12px;
  }

  .objects-tools-panel {
    flex-basis: 200px;
    width: 200px;
  }
}

@media (max-width: 1023px) {
  .content {
    padding: 12px;
  }

  .page-header {
    align-items: flex-start;
    flex-direction: column;
    gap: 10px;
    height: auto;
    margin-bottom: 12px;
    padding-bottom: 10px;
  }

  .header-actions {
    flex-wrap: wrap;
    width: 100%;
  }

  .layout-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .gallery-column {
    max-height: 260px;
    padding: 12px;
  }

  .gallery-grid {
    grid-auto-rows: 72px;
    grid-template-columns: repeat(auto-fill, minmax(86px, 1fr));
    max-height: 190px;
  }

  .viewer-column {
    gap: 12px;
  }

  .main-card {
    min-height: 0;
  }

  .split-view {
    grid-template-columns: minmax(0, 1fr);
    padding: 12px;
  }

  .image-container {
    min-height: 0;
  }

  .img-placeholder {
    height: clamp(300px, 50vh, 420px);
  }

  .data-container {
    gap: 12px;
  }

  .objects-layout {
    flex-direction: column;
  }

  .objects-table-wrapper {
    border-right: 0;
    padding: 12px;
  }

  .objects-tools-panel {
    flex-basis: auto;
    width: 100%;
  }
}
</style>
