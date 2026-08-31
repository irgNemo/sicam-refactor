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
          <div class="gallery-title-group">
            <h3>Galería</h3>
            <span>{{ activeSampleTypeDisplayName }}</span>
          </div>
          <span class="gallery-count">{{ imagenes.length }}</span>
        </div>

        <div class="sample-type-tabs" role="tablist" aria-label="Tipo de muestra">
          <button
            v-for="tab in sampleTypeTabs"
            :key="tab.sampleType"
            type="button"
            class="sample-type-tab"
            :class="{ active: activeSampleType === tab.sampleType }"
            :aria-selected="activeSampleType === tab.sampleType"
            :disabled="segmentacionLoading"
            role="tab"
            @click="setActiveSampleType(tab.sampleType)"
          >
            {{ tab.displayName }}
          </button>
        </div>

        <div class="gallery-grid">
          <div v-if="galleryLoading" class="empty-gallery">
            <div class="empty-icon">🖼️</div>
            <p>Cargando muestras...</p>
          </div>

          <div v-else-if="galleryError" class="empty-gallery error">
            <div class="empty-icon">🖼️</div>
            <p>{{ galleryError }}</p>
          </div>

          <template v-else>
            <div
              v-for="muestra in imagenes"
              :key="sampleKey(muestra)"
              class="thumb"
              :class="{
                active: isSelectedSample(muestra),
                disabled: segmentacionLoading && !isSelectedSample(muestra),
              }"
              @click="selectImagen(muestra)"
            >
              <img
                :src="muestra.imagen"
                alt="Muestra"
              />
              <div class="thumb-overlay">
                <span class="thumb-name">{{ sampleName(muestra) }}</span>
                <span class="thumb-id">Muestra #{{ muestra.id_muestra }}</span>
              </div>
            </div>

            <div v-if="imagenes.length === 0" class="empty-gallery">
              <div class="empty-icon">🖼️</div>
              <p>{{ emptyGalleryTitle }}</p>
              <span>{{ emptyGallerySubtitle }}</span>
            </div>
          </template>
        </div>
      </div>

      <!-- VISOR -->
      <div class="viewer-column">

        <!-- TARJETA PRINCIPAL -->
        <div class="card main-card">
          <div class="card-header">
            <div class="card-title-section">
              <h3>
                {{ imagenSeleccionada ? sampleName(imagenSeleccionada) : 'Vista previa' }}
              </h3>
              <span v-if="imagenSeleccionada" class="card-subtitle">
                {{ activeSampleTypeDisplayName }} · Muestra #{{ imagenSeleccionada.id_muestra }}
              </span>
            </div>
          </div>

          <div class="card-body split-view">

            <!-- IMAGEN -->
            <div class="image-container">
              <SegmentationEditorToolbar
                v-if="imagenSeleccionada"
                :viewer-mode="viewerMode"
                :is-edit-mode="isEditMode"
                :revision-loading="revisionLoading"
                :active-revision="activeRevision"
                :is-draft-dirty="isDraftDirty"
                :editor-tool="editorTool"
                @change-viewer-mode="setViewerMode"
                @change-editor-tool="setEditorTool"
              />

              <div
                v-if="revisionError"
                class="segmentation-status error"
              >
                {{ revisionError }}
              </div>

              <div ref="imageFrame" class="img-placeholder">
                <div
                  v-if="imagenSeleccionada"
                  class="image-transform-layer"
                  :class="imagePanClass"
                  :style="imageTransformStyle"
                  @pointerdown.capture="startImagePan"
                  @pointermove="moveImagePan"
                  @pointerup="endImagePan"
                  @pointercancel="endImagePan"
                  @lostpointercapture="endImagePan"
                >
                  <img
                    ref="mainImage"
                    :src="imagenSeleccionada.imagen"
                    class="main-image"
                    alt="Muestra microscópica"
                    draggable="false"
                    @load="onMainImageLoad"
                    @dragstart.prevent
                  />
                  <SegmentationOverlay
                    ref="segmentationOverlay"
                    :show="shouldShowSegmentationOverlay"
                    :is-edit-mode="isEditMode"
                    :effective-pan-mode="effectivePanMode"
                    :is-draw-mode="isDrawMode"
                    :is-vertex-mode="isVertexMode"
                    :vertex-edit-mode="vertexEditMode"
                    :image-rendered-size="imageRenderedSize"
                    :overlay-polygons="overlayPolygons"
                    :selection-highlight-polygons="selectionHighlightPolygons"
                    :overlay-stroke-width="overlayStrokeWidth"
                    :selected-overlay-stroke-width="selectedOverlayStrokeWidth"
                    :draft-polygon-svg-points="draftPolygonSvgPoints"
                    :draft-polygon-svg-points-string="draftPolygonSvgPointsString"
                    :draft-polygon-fill="overlayFillForLabel(drawingLabel, 'draft')"
                    :draft-polygon-segments="draftPolygonSegments"
                    :drawing-color="drawingColor"
                    :draft-stroke-width="draftStrokeWidth"
                    :draft-segment-hit-stroke-width="draftSegmentHitStrokeWidth"
                    :draft-point-hit-radius="draftPointHitRadius"
                    :draft-point-radius="draftPointRadius"
                    :draft-selected-point-radius="draftSelectedPointRadius"
                    :draft-point-stroke-width="draftPointStrokeWidth"
                    :draft-selected-point-stroke-width="draftSelectedPointStrokeWidth"
                    :selected-draft-point-index="selectedDraftPointIndex"
                    :selected-vertex-handles="selectedVertexHandles"
                    :vertex-handle-hit-radius="vertexHandleHitRadius"
                    :vertex-handle-radius="vertexHandleRadius"
                    :vertex-selected-handle-radius="vertexSelectedHandleRadius"
                    :vertex-handle-stroke-width="vertexHandleStrokeWidth"
                    :vertex-selected-handle-stroke-width="vertexSelectedHandleStrokeWidth"
                    @overlay-click="handleOverlaySvgClick"
                    @polygon-pointerdown="handleOverlayPolygonPointerDown"
                    @polygon-click="handleOverlayPolygonClick"
                    @draft-segment-pointerdown="handleDraftSegmentPointerDown"
                    @draft-point-pointerdown="startDraftPointDrag"
                    @draft-point-pointermove="moveDraftPointDrag"
                    @draft-point-pointerup="endDraftPointDrag"
                    @draft-point-pointercancel="cancelDraftPointDrag"
                    @vertex-pointerdown="startVertexDrag"
                    @vertex-pointermove="moveVertexDrag"
                    @vertex-pointerup="endVertexDrag"
                    @vertex-pointercancel="cancelVertexDrag"
                  />
                </div>
                <div
                  v-if="!imagenSeleccionada"
                  class="empty-image-state"
                >
                  <div class="empty-image-icon">🔬</div>
                  <p>Seleccione una imagen de la galería</p>
                </div>
              </div>

              <SegmentationImageControls
                v-if="imagenSeleccionada"
                :image-zoom="imageZoom"
                @zoom-in="zoomImage"
                @zoom-out="zoomOutImage"
                @rotate="rotateImage"
                @reset="resetImageView"
              />
            </div>

            <!-- DATOS -->
            <div class="data-container">
              <SegmentationCountSummary
                :summary="resumenConteoActivo"
                :palette="segmentationLabelPalette"
                :rows="resumenConteoRows"
              />

              <div
                v-if="isEditMode"
                class="selected-object-panel"
              >
                <div class="selected-object-header">
                  <h4>{{ contextualPanelTitle }}</h4>
                  <span v-if="isSpacePressed && editorTool !== 'PAN'" class="editor-hint">
                    Pan temporal
                  </span>
                  <span v-else-if="editorTool === 'PAN'" class="editor-hint">
                    Mover visor
                  </span>
                </div>

                <template v-if="showObjectContext">
                  <div v-if="selectedObject" class="selected-object-grid">
                    <span>Tipo</span>
                    <strong>{{ overlayLabelDisplayName(selectedObject.label) }}</strong>
                    <span>ID</span>
                    <strong>#{{ selectedObject.id }}</strong>
                    <span>Origen</span>
                    <strong>{{ provenanceDisplayName(selectedObject.provenance?.origin) }}</strong>
                    <span v-if="selectedObject.provenance?.base_object_id">
                      ID base
                    </span>
                    <strong v-if="selectedObject.provenance?.base_object_id">
                      #{{ selectedObject.provenance.base_object_id }}
                    </strong>
                    <span v-if="selectedObject.provenance?.modified">
                      Modificado
                    </span>
                    <strong v-if="selectedObject.provenance?.modified">
                      Sí
                    </strong>
                    <span v-if="editorTool === 'VERTEX' && selectedVertexIndex !== null">
                      Vértice
                    </span>
                    <strong v-if="editorTool === 'VERTEX' && selectedVertexIndex !== null">
                      #{{ selectedVertexIndex + 1 }}
                    </strong>
                  </div>

                  <div v-else class="selected-object-empty">
                    Seleccione una máscara sobre la imagen.
                  </div>
                  <div
                    v-if="editorTool === 'VERTEX' && !selectedObject"
                    class="draft-status"
                  >
                    Seleccione una máscara para editar su contorno.
                  </div>
                  <div
                    v-else-if="editorTool === 'VERTEX' && selectedObject"
                    class="draft-status"
                  >
                    {{ selectedVertexHandles.length }} handles visibles de
                    {{ selectedObject.geometry?.points?.length || 0 }} vértices.
                  </div>

                  <div
                    v-if="editorTool === 'VERTEX'"
                    class="vertex-mode-panel"
                  >
                    <div class="vertex-mode-buttons">
                      <button
                        class="mode-btn editor-tool-btn"
                        :class="{ active: vertexEditMode === 'MOVE' }"
                        :aria-pressed="vertexEditMode === 'MOVE'"
                        @click="setVertexEditMode('MOVE')"
                      >
                        Mover puntos
                      </button>
                      <button
                        class="mode-btn editor-tool-btn"
                        :class="{ active: vertexEditMode === 'INSERT' }"
                        :aria-pressed="vertexEditMode === 'INSERT'"
                        @click="setVertexEditMode('INSERT')"
                      >
                        Agregar punto
                      </button>
                    </div>
                    <div
                      v-if="selectedVertexIndex !== null"
                      class="draft-status"
                    >
                      Vértice seleccionado: #{{ selectedVertexIndex + 1 }}
                    </div>
                    <div
                      v-if="selectedObject && selectedVertexIndex !== null && !canDeleteSelectedVertex"
                      class="draft-status warning"
                    >
                      El contorno debe conservar al menos 3 puntos.
                    </div>
                    <button
                      v-if="selectedObject && selectedVertexIndex !== null"
                      class="control-btn danger full-width"
                      :disabled="!canDeleteSelectedVertex"
                      @click="deleteSelectedVertex"
                    >
                      Eliminar punto
                    </button>
                  </div>

                  <button
                    v-if="selectedObject"
                    class="control-btn danger full-width"
                    @click="deleteSelectedObject"
                  >
                    Eliminar máscara
                  </button>
                </template>

                <div
                  v-else-if="editorTool === 'PAN'"
                  class="draft-status"
                >
                  Mueva la imagen ampliada. Use Seleccionar o Editar contorno para acciones de edición.
                </div>

                <div
                  v-if="isDrawTool"
                  class="drawing-panel"
                >
                  <div class="drawing-label-row">
                    <span>Tipo a dibujar</span>
                    <select
                      v-model="drawingLabel"
                      class="drawing-label-select"
                      :disabled="!isEditMode"
                    >
                      <option
                        v-for="labelConfig in editableDrawingLabels"
                        :key="labelConfig.label"
                        :value="labelConfig.label"
                      >
                        {{ labelConfig.displayName }}
                      </option>
                    </select>
                  </div>
                  <div
                    v-if="draftPolygonPoints.length"
                    class="draft-status"
                  >
                    Máscara en construcción: {{ draftPolygonPoints.length }} puntos
                    <span v-if="selectedDraftPointIndex !== null">
                      · Punto #{{ selectedDraftPointIndex + 1 }} seleccionado
                    </span>
                  </div>
                  <div
                    v-else-if="isDrawMode"
                    class="draft-status"
                  >
                    Click sobre la imagen para agregar vértices.
                  </div>
                  <div
                    v-if="invalidDrawMessage"
                    class="draft-status warning"
                  >
                    {{ invalidDrawMessage }}
                  </div>
                  <div class="editor-actions">
                    <button
                      class="control-btn success"
                      :disabled="draftPolygonPoints.length < 3"
                      @click="finishDraftPolygon"
                    >
                      Finalizar máscara
                    </button>
                    <button
                      class="control-btn"
                      :disabled="!draftPolygonPoints.length"
                      @click="cancelDraftPolygon"
                    >
                      Cancelar
                    </button>
                    <button
                      class="control-btn danger"
                      :disabled="selectedDraftPointIndex === null"
                      @click="deleteSelectedDraftPoint"
                    >
                      Eliminar punto
                    </button>
                  </div>
                </div>

                <div
                  v-if="showRevisionActions && saveDraftError"
                  class="segmentation-status error"
                >
                  {{ saveDraftError }}
                </div>
                <div
                  v-if="showRevisionActions && saveDraftMessage"
                  class="segmentation-status success"
                >
                  {{ saveDraftMessage }}
                </div>
                <div
                  v-if="showRevisionActions && validateRevisionError"
                  class="segmentation-status error"
                >
                  {{ validateRevisionError }}
                </div>
                <div
                  v-if="showRevisionActions && validateRevisionMessage"
                  class="segmentation-status success"
                >
                  {{ validateRevisionMessage }}
                </div>
                <div
                  v-if="isDrawTool && draftPolygonPoints.length"
                  class="segmentation-status warning"
                >
                  Finalice o cancele la máscara en construcción.
                </div>
                <div
                  v-if="showRevisionActions"
                  class="editor-actions"
                >
                  <button
                    class="control-btn"
                    :disabled="!canUndo"
                    @click="undoRevisionEdit"
                  >
                    Deshacer
                  </button>
                  <button
                    class="control-btn"
                    :disabled="!canRedo"
                    @click="redoRevisionEdit"
                  >
                    Rehacer
                  </button>
                  <button
                    class="btn-segment"
                    :disabled="!canSaveDraft"
                    @click="saveDraft"
                  >
                    {{ isSavingDraft ? 'Guardando...' : 'Guardar borrador' }}
                  </button>
                </div>
                <div
                  v-if="showRevisionActions && validateRevisionBlockReason"
                  class="draft-status warning"
                >
                  {{ validateRevisionBlockReason }}
                </div>
                <button
                  v-if="showRevisionActions && activeRevision?.estado === 'BORRADOR'"
                  class="btn-segment success full-width"
                  :disabled="!canValidateRevision"
                  @click="confirmAndValidateRevision"
                >
                  {{ isValidatingRevision ? 'Validando...' : 'Validar revisión' }}
                </button>
              </div>

              <SegmentationResultPanel
                v-if="imagenSeleccionada"
                :segmentacion-loading="segmentacionLoading"
                :segmentacion-error="segmentacionError"
                :segmentacion-metadata="segmentacionMetadata"
                :segmentacion-objetos-count="segmentacionObjetosCount"
                :active-sample-type="activeSampleType"
                :active-sample-type-display-name="activeSampleTypeDisplayName"
                :is-blood-sample-type="isBloodSampleType"
                :effective-segmentation-loading="effectiveSegmentationLoading"
                :effective-segmentation-error="effectiveSegmentationError"
                :effective-segmentation="effectiveSegmentation"
                :effective-segmentation-display="effectiveSegmentationDisplay"
                :show-pending-draft-notice="showPendingDraftNotice"
                :pending-draft-revision="pendingDraftRevision"
                :show-validated-revision-notice="showValidatedRevisionNotice"
                :latest-validated-revision="latestValidatedRevision"
                :pending-draft-error="pendingDraftError"
                :is-edit-mode="isEditMode"
                :historial-segmentacion="historialSegmentacion"
                :historial-loading="historialLoading"
                :historial-error="historialError"
                :ultimo-resultado-segmentacion="ultimoResultadoSegmentacion"
                :ultimo-historial-objetos-count="ultimoHistorialObjetosCount"
                :completed-segmentation-results="completedSegmentationResults"
                :selected-segmentation-result-id="activeResultadoSegmentacionId"
                @run-segmentation="ejecutarSegmentacion"
                @continue-edit="setViewerMode('EDIT')"
                @change-segmentation-result="setSelectedSegmentationResult"
              />

            </div>

          </div>
        </div>

        <OverlayLayersCard
          :labels="overlayLabels"
          @change-visibility="setOverlayLabelVisibility"
        />

      </div>
    </div>
  </main>
</template>

<script>
import apiClient from "../services/apiClient";
import OverlayLayersCard from "./segmentation/OverlayLayersCard.vue";
import SegmentationCountSummary from "./segmentation/SegmentationCountSummary.vue";
import SegmentationEditorToolbar from "./segmentation/SegmentationEditorToolbar.vue";
import SegmentationImageControls from "./segmentation/SegmentationImageControls.vue";
import SegmentationOverlay from "./segmentation/SegmentationOverlay.vue";
import SegmentationResultPanel from "./segmentation/SegmentationResultPanel.vue";
import {
  listarMuestras,
  obtenerResultadosSegmentacion,
  segmentarMuestra,
} from "../services/segmentationService";
import {
  ZOOM_MIN,
  ZOOM_MAX,
  ZOOM_STEP,
  calculateImagePanLimits,
  calculateOverlayContainment,
  getValidPolygonPoints,
  scalePointToOverlay,
  scalePolygonPointsToOverlay,
} from "../composables/useSegmentationViewport";
import { useSegmentationEditor } from "../composables/useSegmentationEditor";
import { useSegmentationRevision } from "../composables/useSegmentationRevision";
import {
  OVERLAY_FALLBACK_PALETTE,
  SAMPLE_TYPES,
  getLabelConfig,
  getLabelPalette,
  getSegmentationTypeConfig,
} from "../domain/segmentationTypes";

const SEGMENT_HIT_TOLERANCE_PX = 8;
const VERTEX_SEGMENT_HIT_TOLERANCE_PX = 8;
const DRAW_HANDLE_VISIBLE_RADIUS_PX = 2;
const DRAW_HANDLE_SELECTED_RADIUS_PX = 3;
const DRAW_HANDLE_HIT_RADIUS_PX = 8;
const VERTEX_HANDLE_VISIBLE_RADIUS_PX = 2.25;
const VERTEX_HANDLE_SELECTED_RADIUS_PX = 3.25;
const VERTEX_HANDLE_HIT_RADIUS_PX = 8;
const OVERLAY_STROKE_PX = 1.5;
const SELECTED_OVERLAY_STROKE_PX = 2;
const DRAFT_STROKE_PX = 1.25;
const DRAW_HANDLE_STROKE_PX = 1;
const DRAW_SELECTED_HANDLE_STROKE_PX = 1.25;
const VERTEX_HANDLE_STROKE_PX = 1.1;
const VERTEX_SELECTED_HANDLE_STROKE_PX = 1.25;
const MIN_VERTEX_HANDLE_SPACING_PX = 12;
const NEAREST_VERTEX_HIT_PX = 12;
const VERTEX_NEIGHBOR_RADIUS = 3;

export default {
  name: "MainContent",
  emits: [
    "sample-type-changed",
    "segmentation-completed",
    "sample-selected",
    "segmentation-result-selected",
  ],
  components: {
    OverlayLayersCard,
    SegmentationCountSummary,
    SegmentationEditorToolbar,
    SegmentationImageControls,
    SegmentationOverlay,
    SegmentationResultPanel,
  },

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

  setup() {
    return {
      ...useSegmentationEditor(),
      ...useSegmentationRevision(),
    };
  },

  data() {
    return {
      analisis: [],
      muestrasSangre: [],
      muestrasSangreLoading: false,
      muestrasSangreError: "",
      loading: true,
      imagenSeleccionada: null,
      segmentacionLoading: false,
      segmentacionResultado: null,
      segmentacionError: "",
      historialSegmentacion: [],
      historialLoading: false,
      historialError: "",
      viewerMode: "NAVIGATE",
      isSpacePressed: false,
      activePanPointerId: null,
      panCaptureTarget: null,
      didPointerDrag: false,
      dragThreshold: 5,
      lastPointerDragAt: 0,
      lastSpacePointerAt: 0,
      imageNaturalSize: { width: 0, height: 0 },
      imageRenderedSize: { width: 0, height: 0 },
      imageZoom: 1,
      imageRotation: 0,
      panX: 0,
      panY: 0,
      isPanning: false,
      panStartPointerX: 0,
      panStartPointerY: 0,
      panStartX: 0,
      panStartY: 0,
      overlayLabelVisibility: {},
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
      if (!this.analisisActual) return [];

      if (this.activeSampleType === SAMPLE_TYPES.BLOOD) {
        return this.muestrasSangre.filter(
          muestra => Number(muestra.analisis) === Number(this.analisisActual.id_analisis)
        );
      }

      return this.analisisActual.muestras_saliva || [];
    },

    sampleTypeTabs() {
      return [SAMPLE_TYPES.SALIVA, SAMPLE_TYPES.BLOOD].map(sampleType => ({
        sampleType,
        displayName: getSegmentationTypeConfig(sampleType).displayName,
      }));
    },

    activeSampleTypeDisplayName() {
      return this.activeSegmentationConfig.displayName || this.activeSampleType;
    },

    isBloodSampleType() {
      return this.activeSampleType === SAMPLE_TYPES.BLOOD;
    },

    galleryLoading() {
      return this.activeSampleType === SAMPLE_TYPES.BLOOD
        ? this.muestrasSangreLoading
        : this.loading;
    },

    galleryError() {
      return this.activeSampleType === SAMPLE_TYPES.BLOOD
        ? this.muestrasSangreError
        : "";
    },

    emptyGalleryTitle() {
      if (!this.patientId || !this.caseId) {
        return "No hay imágenes disponibles";
      }

      return this.activeSampleType === SAMPLE_TYPES.BLOOD
        ? "No hay muestras de sangre cargadas."
        : "No hay muestras de saliva cargadas.";
    },

    emptyGallerySubtitle() {
      if (!this.patientId || !this.caseId) {
        return "Seleccione un caso válido";
      }

      return this.activeSampleType === SAMPLE_TYPES.BLOOD
        ? "Cargue muestras de sangre desde Registro o API."
        : "Cargue muestras de saliva desde Registro.";
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

    completedSegmentationResults() {
      return this.historialSegmentacion
        .filter(result => result.estado === "COMPLETADO")
        .sort((a, b) => {
          const byDate = new Date(b.creado_en || 0) - new Date(a.creado_en || 0);
          if (byDate !== 0) return byDate;
          return Number(b.id || 0) - Number(a.id || 0);
        });
    },

    selectedResultadoSegmentacion() {
      if (!this.selectedSegmentationResultId) return null;

      return this.completedSegmentationResults.find(
        result => result.id === this.selectedSegmentationResultId
      ) || null;
    },

    resultadoSegmentacionActivo() {
      return (
        this.selectedResultadoSegmentacion ||
        this.completedSegmentationResults[0] ||
        this.segmentacionResultado ||
        null
      );
    },

    activeResultadoSegmentacionId() {
      return (
        this.resultadoSegmentacionActivo?.id ||
        this.resultadoSegmentacionActivo?.resultado_segmentacion?.id ||
        null
      );
    },

    resultadoNormalizadoActivo() {
      return this.resultadoSegmentacionActivo?.resultado_normalizado || null;
    },

    activeSegmentationConfig() {
      return getSegmentationTypeConfig(this.activeSampleType);
    },

    editableDrawingLabels() {
      return this.activeSegmentationConfig.labels.filter(label => label.editable);
    },

    segmentationLabelPalette() {
      return getLabelPalette(this.activeSampleType);
    },

    isEditMode() {
      return this.viewerMode === "EDIT";
    },

    effectivePanMode() {
      return (
        this.viewerMode === "NAVIGATE" ||
        (this.viewerMode === "EDIT" && this.editorTool === "PAN") ||
        (this.viewerMode === "EDIT" && this.isSpacePressed)
      );
    },

    isDrawMode() {
      return this.isEditMode && this.editorTool === "DRAW" && !this.effectivePanMode;
    },

    isVertexMode() {
      return this.isEditMode && this.editorTool === "VERTEX" && !this.effectivePanMode;
    },

    isDrawTool() {
      return this.isEditMode && this.editorTool === "DRAW";
    },

    showObjectContext() {
      return this.isEditMode && ["SELECT", "VERTEX"].includes(this.editorTool);
    },

    showRevisionActions() {
      return this.isEditMode && ["SELECT", "VERTEX"].includes(this.editorTool);
    },

    contextualPanelTitle() {
      const titles = {
        SELECT: "Objeto seleccionado",
        PAN: "Navegación",
        DRAW: "Máscara en construcción",
        VERTEX: "Editar contorno",
      };

      return titles[this.editorTool] || "Edición";
    },

    activeRevisionSummary() {
      return this.isEditMode ? this.workingSummary : null;
    },

    activeOverlaySummary() {
      if (this.isEditMode) {
        return this.activeRevisionSummary;
      }

      return this.effectiveSegmentation?.resumen || null;
    },

    activeOverlayObjects() {
      if (this.isEditMode) {
        return this.workingObjects;
      }

      const objects = this.effectiveSegmentation?.resultado?.objects;
      return Array.isArray(objects)
        ? objects
        : [];
    },

    effectiveSegmentationDisplay() {
      if (!this.effectiveSegmentation) return "";

      if (this.effectiveSegmentation.fuente === "VALIDADA") {
        const revisionNumber =
          this.effectiveSegmentation.revision?.numero_revision;
        return revisionNumber
          ? `Revisión #${revisionNumber} validada`
          : "Revisión validada";
      }

      return "Automático";
    },

    resumenConteoActivo() {
      const summary = this.activeOverlaySummary;
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
        : Object.values(counts).reduce((accumulator, value) => {
          const parsed = Number(value);
          return Number.isFinite(parsed) ? accumulator + parsed : accumulator;
        }, 0);

      return {
        membranas,
        nucleos,
        micronucleos,
        total,
      };
    },

    resumenConteoRows() {
      const summary = this.activeOverlaySummary;
      if (!summary || typeof summary !== "object") return [];

      const counts = summary.counts_by_label;
      if (!counts || typeof counts !== "object") return [];

      return this.activeSegmentationConfig.labels.map(labelConfig => {
        const value = Number(counts[labelConfig.label]);
        return {
          label: labelConfig.label,
          displayName: labelConfig.displayName,
          count: Number.isFinite(value) ? value : 0,
          color: this.overlayColorForLabel(labelConfig.label),
        };
      });
    },

    imageTransformStyle() {
      return {
        transform: `translate(${this.panX}px, ${this.panY}px) scale(${this.imageZoom}) rotate(${this.imageRotation}deg)`,
      };
    },

    imagePanClass() {
      return {
        "is-pannable": this.imageZoom > 1 && this.effectivePanMode,
        "is-panning": this.isPanning,
        "is-edit-mode": this.isEditMode,
        "is-effective-pan-mode": this.effectivePanMode,
      };
    },

    drawingColor() {
      return this.overlayColorForLabel(this.drawingLabel);
    },

    overlayStrokeWidth() {
      return Number((OVERLAY_STROKE_PX / Math.max(this.imageZoom, 1)).toFixed(3));
    },

    selectedOverlayStrokeWidth() {
      return Number((SELECTED_OVERLAY_STROKE_PX / Math.max(this.imageZoom, 1)).toFixed(3));
    },

    draftStrokeWidth() {
      return Number((DRAFT_STROKE_PX / Math.max(this.imageZoom, 1)).toFixed(3));
    },

    draftSegmentHitStrokeWidth() {
      return Number(((SEGMENT_HIT_TOLERANCE_PX * 2) / Math.max(this.imageZoom, 1)).toFixed(3));
    },

    draftPolygonSvgPoints() {
      return this.draftPolygonPoints
        .map(point => this.scalePoint(point))
        .filter(Boolean);
    },

    draftPolygonSvgPointsString() {
      return this.draftPolygonSvgPoints
        .map(point => point.join(","))
        .join(" ");
    },

    draftPolygonSegments() {
      const points = this.draftPolygonSvgPoints;
      if (points.length < 2) return [];

      const segments = points.slice(0, -1).map((point, index) => ({
        key: `draft-segment-${index}-${index + 1}`,
        startIndex: index,
        endIndex: index + 1,
        start: point,
        end: points[index + 1],
      }));

      if (points.length >= 3) {
        segments.push({
          key: `draft-segment-${points.length - 1}-0`,
          startIndex: points.length - 1,
          endIndex: 0,
          start: points[points.length - 1],
          end: points[0],
        });
      }

      return segments;
    },

    draftPointRadius() {
      return Number((DRAW_HANDLE_VISIBLE_RADIUS_PX / Math.max(this.imageZoom, 1)).toFixed(3));
    },

    draftSelectedPointRadius() {
      return Number((DRAW_HANDLE_SELECTED_RADIUS_PX / Math.max(this.imageZoom, 1)).toFixed(3));
    },

    draftPointHitRadius() {
      return Number((DRAW_HANDLE_HIT_RADIUS_PX / Math.max(this.imageZoom, 1)).toFixed(3));
    },

    draftPointStrokeWidth() {
      return Number((DRAW_HANDLE_STROKE_PX / Math.max(this.imageZoom, 1)).toFixed(3));
    },

    draftSelectedPointStrokeWidth() {
      return Number((DRAW_SELECTED_HANDLE_STROKE_PX / Math.max(this.imageZoom, 1)).toFixed(3));
    },

    vertexHandleRadius() {
      return Number((VERTEX_HANDLE_VISIBLE_RADIUS_PX / Math.max(this.imageZoom, 1)).toFixed(3));
    },

    vertexSelectedHandleRadius() {
      return Number((VERTEX_HANDLE_SELECTED_RADIUS_PX / Math.max(this.imageZoom, 1)).toFixed(3));
    },

    vertexHandleHitRadius() {
      return Number((VERTEX_HANDLE_HIT_RADIUS_PX / Math.max(this.imageZoom, 1)).toFixed(3));
    },

    vertexHandleStrokeWidth() {
      return Number((VERTEX_HANDLE_STROKE_PX / Math.max(this.imageZoom, 1)).toFixed(3));
    },

    vertexSelectedHandleStrokeWidth() {
      return Number((VERTEX_SELECTED_HANDLE_STROKE_PX / Math.max(this.imageZoom, 1)).toFixed(3));
    },

    selectedVertexHandles() {
      if (!this.isVertexMode || !this.selectedObject) return [];

      const points = this.selectedObject.geometry?.points;
      if (!Array.isArray(points)) return [];

      const neighborIndices = new Set(this.selectedVertexNeighborIndices);

      return this.visibleVertexIndices
        .map(vertexIndex => {
          const svgPoint = this.scalePoint(points[vertexIndex]);
          if (!svgPoint) return null;
          const selected = vertexIndex === this.selectedVertexIndex;
          const neighbor = neighborIndices.has(vertexIndex) && !selected;

          return {
            key: `${this.selectedObject.id}-${vertexIndex}`,
            objectId: this.selectedObject.id,
            vertexIndex,
            x: svgPoint[0],
            y: svgPoint[1],
            selected,
            role: selected ? "selected" : neighbor ? "neighbor" : "general",
          };
        })
        .filter(Boolean);
    },

    visibleVertexIndices() {
      if (!this.isVertexMode || !this.selectedObject) return [];

      const points = this.selectedObject.geometry?.points;
      if (!Array.isArray(points) || !points.length) return [];

      const visible = new Set(this.computeLodVertexIndices(points));
      this.selectedVertexNeighborIndices.forEach(index => visible.add(index));

      return [...visible].sort((a, b) => a - b);
    },

    selectedVertexNeighborIndices() {
      const points = this.selectedObject?.geometry?.points;
      if (
        !Array.isArray(points) ||
        !points.length ||
        this.selectedVertexIndex === null ||
        this.selectedVertexIndex < 0 ||
        this.selectedVertexIndex >= points.length
      ) {
        return [];
      }

      const indices = new Set();
      const count = points.length;

      for (let offset = -VERTEX_NEIGHBOR_RADIUS; offset <= VERTEX_NEIGHBOR_RADIUS; offset += 1) {
        indices.add((this.selectedVertexIndex + offset + count) % count);
      }

      return [...indices];
    },

    selectedObjectVertexSegments() {
      const points = this.selectedObject?.geometry?.points;
      if (!Array.isArray(points) || points.length < 3) return [];

      return points
        .map((point, index) => {
          const nextIndex = (index + 1) % points.length;
          const start = this.scalePoint(point);
          const end = this.scalePoint(points[nextIndex]);
          if (!start || !end) return null;

          return {
            key: `object-segment-${index}-${nextIndex}`,
            startIndex: index,
            endIndex: nextIndex,
            start,
            end,
          };
        })
        .filter(Boolean);
    },

    canUndo() {
      return this.isEditMode && this.undoStack.length > 0;
    },

    canRedo() {
      return this.isEditMode && this.redoStack.length > 0;
    },

    canSaveDraft() {
      return (
        this.isEditMode &&
        this.isDraftDirty &&
        !this.isSavingDraft &&
        this.draftPolygonPoints.length === 0 &&
        !this.draftPointDrag &&
        !this.vertexDrag
      );
    },

    noEditorialInteractionInProgress() {
      return !this.draftPointDrag && !this.vertexDrag && !this.isPanning;
    },

    validateRevisionBlockReason() {
      if (!this.activeRevision || this.activeRevision.estado !== "BORRADOR") {
        return "No hay una revisión BORRADOR activa.";
      }

      if (this.isDraftDirty) {
        return "Guarda los cambios antes de validar la revisión.";
      }

      if (this.draftPolygonPoints.length > 0) {
        return "Finaliza o cancela la máscara en construcción antes de validar.";
      }

      if (!this.noEditorialInteractionInProgress) {
        return "Termina la interacción actual antes de validar.";
      }

      if (this.isValidatingRevision) {
        return "Validando revisión...";
      }

      return "";
    },

    canValidateRevision() {
      return (
        this.isEditMode &&
        ["SELECT", "VERTEX"].includes(this.editorTool) &&
        !this.validateRevisionBlockReason
      );
    },

    showValidatedRevisionNotice() {
      return (
        this.viewerMode === "NAVIGATE" &&
        !this.pendingDraftRevision &&
        Boolean(this.latestValidatedRevision)
      );
    },

    showPendingDraftNotice() {
      return (
        this.viewerMode === "NAVIGATE" &&
        this.pendingDraftRevision?.estado === "BORRADOR"
      );
    },

    imagePanLimits() {
      return calculateImagePanLimits(
        this.imageRenderedSize,
        this.imageZoom,
        this.imageRotation
      );
    },

    overlayContainment() {
      return calculateOverlayContainment(
        this.imageNaturalSize,
        this.imageRenderedSize
      );
    },

    overlayPolygons() {
      if (!this.imagenSeleccionada || !this.overlayContainment.canProject) {
        return [];
      }

      return this.overlayVisibleDrawableObjectsForRender
        .map((item, index) => {
          const color = this.overlayColorForLabel(item.label);
          return {
            key: this.overlayPolygonKey(item, index),
            selectionKey: item.selectionKey,
            objectId: item.object.id,
            origin: item.object.provenance?.origin,
            selected: this.isEditMode && item.selectionKey === this.selectedObjectKey,
            points: item.points,
            fill: this.overlayFillForLabel(item.label),
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

    selectionHighlightPolygons() {
      return this.overlayPolygons.filter(polygon => polygon.selected);
    },

    shouldShowSegmentationOverlay() {
      return Boolean(
        this.imagenSeleccionada &&
        this.overlayContainment.canProject &&
        (this.overlayPolygons.length || this.isEditMode)
      );
    },

    overlayDrawableObjects() {
      return this.activeOverlayObjects
        .filter(object => object.geometry?.type === "polygon")
        .map((object, index) => ({
          object,
          objectIndex: index,
          selectionKey: this.overlayObjectKey(object, index),
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

    overlayVisibleDrawableObjectsForRender() {
      return [...this.overlayVisibleDrawableObjects].sort((a, b) => {
        const labelDiff =
          this.overlayLabelRenderOrder(a.label) -
          this.overlayLabelRenderOrder(b.label);

        if (labelDiff !== 0) return labelDiff;
        return a.objectIndex - b.objectIndex;
      });
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
          displayName: this.overlayLabelDisplayName(label),
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
      this.restoreSelectedSample(nuevas);
    },

    selectedSampleId() {
      this.restoreSelectedSample(this.imagenes);
    },

    selectedSegmentationResultId() {
      if (this.historialSegmentacion.length) {
        this.syncSelectedSegmentationResult();
      }
    },

    activeResultadoSegmentacionId(newId, oldId) {
      if (newId !== oldId) {
        if (this.hasPendingDraftWork && !this.confirmDiscardDraftChanges()) {
          this.emitSegmentationResultSelected(oldId || null);
          return;
        }
        this.resetEditorState({ clearRevision: true });
        this.loadEffectiveSegmentation(newId);
        this.loadRevisionState(newId);
      }
    },

    drawingLabel(label) {
      if (this.isEditMode && this.editorTool === "DRAW") {
        this.showOverlayLabel(label);
      }
    },

    activeSampleType(newType, oldType) {
      const allowedLabels = this.editableDrawingLabels.map(
        labelConfig => labelConfig.label
      );

      if (!allowedLabels.includes(this.drawingLabel)) {
        this.drawingLabel = this.activeSegmentationConfig.defaultDrawingLabel;
      }

      if (newType !== oldType) {
        this.resetCurrentSampleState();

        if (newType === SAMPLE_TYPES.BLOOD && !this.muestrasSangre.length) {
          this.cargarMuestrasSangre();
        }

        this.$nextTick(() => {
          this.restoreSelectedSample(this.imagenes);
        });
      }
    },
  },

  methods: {
    sampleKey(muestra) {
      return `${this.activeSampleType}-${muestra?.id_muestra || "sin-id"}`;
    },

    isSelectedSample(muestra) {
      return Boolean(
        this.imagenSeleccionada &&
        muestra &&
        this.imagenSeleccionada.id_muestra === muestra.id_muestra
      );
    },

    isCurrentSample(muestraId, sampleType = this.activeSampleType) {
      return Boolean(
        this.imagenSeleccionada &&
        this.imagenSeleccionada.id_muestra === muestraId &&
        this.activeSampleType === sampleType
      );
    },

    syncSelectedSegmentationResult() {
      const selected = this.selectedSegmentationResultId
        ? this.completedSegmentationResults.find(
          result => result.id === this.selectedSegmentationResultId
        )
        : null;
      const nextResult = selected || this.completedSegmentationResults[0] || null;
      const nextId = nextResult?.id || null;

      if (nextId !== this.selectedSegmentationResultId) {
        this.emitSegmentationResultSelected(nextId);
      }
    },

    emitSegmentationResultSelected(resultadoId) {
      this.$emit("segmentation-result-selected", {
        sampleType: this.activeSampleType,
        sampleId: this.imagenSeleccionada?.id_muestra || null,
        resultadoId: resultadoId || null,
      });
    },

    setSelectedSegmentationResult(resultId) {
      const parsedId = Number(resultId);
      const selected = Number.isFinite(parsedId)
        ? this.completedSegmentationResults.find(result => result.id === parsedId)
        : null;

      if (!selected) {
        this.emitSegmentationResultSelected(null);
        return;
      }

      if (
        this.activeResultadoSegmentacionId !== selected.id &&
        this.hasPendingDraftWork &&
        !this.confirmDiscardDraftChanges()
      ) {
        return;
      }

      this.emitSegmentationResultSelected(selected.id);
    },

    restoreSelectedSample(samples = this.imagenes) {
      if (this.selectedSampleId) {
        const selected = samples.find(
          muestra => muestra.id_muestra === this.selectedSampleId
        );

        this.selectImagen(selected || null);
        return;
      }

      this.selectImagen(samples[0] || null);
    },

    sampleName(muestra) {
      if (!muestra) return "Sin muestra";
      if (muestra.imagen) {
        const pieces = String(muestra.imagen).split("/");
        return pieces[pieces.length - 1] || `Muestra ${muestra.id_muestra}`;
      }
      return `Muestra ${muestra.id_muestra}`;
    },

    setActiveSampleType(sampleType) {
      if (
        sampleType === this.activeSampleType ||
        !this.sampleTypeTabs.some(tab => tab.sampleType === sampleType) ||
        this.segmentacionLoading
      ) {
        return;
      }

      if (this.hasPendingDraftWork && !this.confirmDiscardDraftChanges()) {
        return;
      }

      this.$emit("sample-type-changed", sampleType);
    },

    resetCurrentSampleState() {
      this.imagenSeleccionada = null;
      this.segmentacionResultado = null;
      this.segmentacionError = "";
      this.historialSegmentacion = [];
      this.historialError = "";
      this.historialLoading = false;
      this.clearEffectiveSegmentation();
      this.resetImageMeasurements();
      this.resetImageView();
      this.resetEditorState({ clearRevision: true });
      this.overlayLabelVisibility = {};
      this.drawingLabel = this.activeSegmentationConfig.defaultDrawingLabel;
    },

    async cargarMuestrasSangre() {
      this.muestrasSangreLoading = true;
      this.muestrasSangreError = "";

      try {
        const response = await listarMuestras(SAMPLE_TYPES.BLOOD);
        this.muestrasSangre = Array.isArray(response.data)
          ? response.data
          : [];
      } catch (error) {
        console.error("Error al cargar muestras de sangre:", error);
        this.muestrasSangre = [];
        this.muestrasSangreError = "No fue posible cargar muestras de sangre";
      } finally {
        this.muestrasSangreLoading = false;
      }
    },

    selectImagen(muestra) {
      if (
        this.segmentacionLoading &&
        this.imagenSeleccionada &&
        muestra?.id_muestra !== this.imagenSeleccionada.id_muestra
      ) {
        return;
      }

      if (
        this.imagenSeleccionada &&
        muestra?.id_muestra !== this.imagenSeleccionada.id_muestra &&
        this.hasPendingDraftWork &&
        !this.confirmDiscardDraftChanges()
      ) {
        return;
      }

      this.imagenSeleccionada = muestra;
      this.$emit("sample-selected", {
        sampleType: this.activeSampleType,
        sampleId: muestra?.id_muestra || null,
      });
      this.segmentacionResultado = null;
      this.segmentacionError = "";
      this.historialSegmentacion = [];
      this.historialError = "";
      this.historialLoading = false;
      this.clearEffectiveSegmentation();
      this.resetImageMeasurements();
      this.resetImageView();
      this.resetEditorState({ clearRevision: true });
      this.overlayLabelVisibility = {};
      this.drawingLabel = this.activeSegmentationConfig.defaultDrawingLabel;

      if (muestra) {
        this.cargarHistorialSegmentacion(muestra.id_muestra, this.activeSampleType);
        this.$nextTick(this.updateImageMeasurements);
      }
    },

    async cargarHistorialSegmentacion(muestraId, sampleType = this.activeSampleType) {
      this.historialLoading = true;
      this.historialError = "";

      try {
        const response = await obtenerResultadosSegmentacion(muestraId, sampleType);

        if (this.isCurrentSample(muestraId, sampleType)) {
          this.historialSegmentacion = Array.isArray(response.data)
            ? response.data
            : [];
          this.syncSelectedSegmentationResult();
          this.syncOverlayLabelVisibility();
          if (!this.ensureRevisionBelongsToResult(this.activeResultadoSegmentacionId)) {
            this.resetEditorState({ clearRevision: true });
          }
        }
      } catch (error) {
        console.error("Error al cargar historial de segmentacion:", error);

        if (this.isCurrentSample(muestraId, sampleType)) {
          this.historialSegmentacion = [];
          this.historialError =
            error.response?.data?.error || "No fue posible cargar el historial";
        }
      } finally {
        if (this.isCurrentSample(muestraId, sampleType)) {
          this.historialLoading = false;
        }
      }
    },

    async ejecutarSegmentacion() {
      if (!this.imagenSeleccionada || this.segmentacionLoading) return;

      this.segmentacionLoading = true;
      this.segmentacionResultado = null;
      this.segmentacionError = "";
      const sampleType = this.activeSampleType;
      const muestraId = this.imagenSeleccionada.id_muestra;

      try {
        const response = await segmentarMuestra(muestraId, sampleType);
        if (!this.isCurrentSample(muestraId, sampleType)) {
          return;
        }
        const resultadoId = response.data?.resultado_segmentacion?.id || null;
        this.segmentacionResultado = response.data;
        this.syncOverlayLabelVisibility();
        await this.cargarHistorialSegmentacion(muestraId, sampleType);
        if (resultadoId) {
          this.emitSegmentationResultSelected(resultadoId);
          await this.loadEffectiveSegmentation(resultadoId);
          await this.loadRevisionState(resultadoId);
        } else {
          await this.loadEffectiveSegmentation(this.activeResultadoSegmentacionId);
        }
        this.syncOverlayLabelVisibility();
        this.$emit("segmentation-completed", {
          caseId: this.caseId,
          muestraId,
          sampleType,
          resultadoId,
        });
      } catch (error) {
        if (!this.isCurrentSample(muestraId, sampleType)) return;
        console.error("Error al segmentar muestra:", error);
        this.segmentacionError =
          error.response?.data?.error || "No fue posible segmentar la muestra";
      } finally {
        if (this.isCurrentSample(muestraId, sampleType)) {
          this.segmentacionLoading = false;
        }
      }
    },

    setViewerMode(mode) {
      if (mode === "NAVIGATE") {
        if (this.hasPendingDraftWork && !this.confirmDiscardDraftChanges()) {
          return;
        }
        this.viewerMode = "NAVIGATE";
        this.editorTool = "SELECT";
        this.clearSelection();
        this.isSpacePressed = false;
        this.endImagePan();
        this.didPointerDrag = false;
        this.activePanPointerId = null;
        this.panCaptureTarget = null;
        return;
      }

      if (mode === "EDIT") {
        this.enterEditMode();
      }
    },

    async enterEditMode() {
      if (this.revisionLoading) return;

      this.revisionError = "";
      const resultadoId = this.activeResultadoSegmentacionId;

      if (!resultadoId) {
        this.viewerMode = "NAVIGATE";
        this.setActiveRevision(null);
        this.clearSelection();
        this.revisionError = "No hay resultado de segmentacion para editar.";
        return;
      }

      if (
        this.activeRevision &&
        this.activeRevision.resultado_segmentacion === resultadoId &&
        this.activeRevision.estado === "BORRADOR"
      ) {
        this.viewerMode = "EDIT";
        this.editorTool = "SELECT";
        if (!this.workingObjects.length) {
          this.loadWorkingRevision(this.activeRevision);
        }
        this.syncOverlayLabelVisibility();
        return;
      }

      this.clearSelection();

      const draft = await this.getOrCreateDraft(resultadoId);

      if (!draft || this.activeResultadoSegmentacionId !== resultadoId) {
        this.viewerMode = "NAVIGATE";
        this.clearSelection();
        return;
      }

      this.loadWorkingRevision(draft);
      this.viewerMode = "EDIT";
      this.editorTool = "SELECT";
      this.syncOverlayLabelVisibility();
    },

    resetEditorState({ clearRevision } = { clearRevision: true }) {
      this.viewerMode = "NAVIGATE";
      this.editorTool = "SELECT";
      this.clearSelection();
      this.revisionError = "";
      this.revisionLoading = false;
      this.isSpacePressed = false;
      this.endImagePan();
      this.didPointerDrag = false;
      this.activePanPointerId = null;
      this.panCaptureTarget = null;
      this.cancelVertexDrag();
      this.cancelDraftPointDrag();
      this.resetEditor();

      if (clearRevision) {
        this.resetRevisionState();
      }
    },

    setEditorTool(tool) {
      if (!["SELECT", "PAN", "DRAW", "VERTEX"].includes(tool)) return;

      this.cancelVertexDrag();
      this.cancelDraftPointDrag();
      this.editorTool = tool;
      if (tool !== "VERTEX") {
        this.selectedVertexIndex = null;
        this.vertexEditMode = "MOVE";
      } else if (!["MOVE", "INSERT"].includes(this.vertexEditMode)) {
        this.vertexEditMode = "MOVE";
      }
      this.isSpacePressed = false;
      this.endImagePan();

      if (tool === "DRAW") {
        this.showOverlayLabel(this.drawingLabel);
      }
    },

    showOverlayLabel(label) {
      this.overlayLabelVisibility = {
        ...this.overlayLabelVisibility,
        [label]: true,
      };
    },

    setVertexEditMode(mode) {
      if (!["MOVE", "INSERT"].includes(mode)) return;

      this.cancelVertexDrag();
      this.vertexEditMode = mode;
    },

    startVertexDrag(handle, event) {
      if (!this.isVertexMode || this.effectivePanMode || this.vertexEditMode !== "MOVE") return;

      event.preventDefault();
      event.stopPropagation();
      event.currentTarget?.setPointerCapture?.(event.pointerId);

      const started = this.beginVertexDrag(handle, {
        pointerId: event.pointerId,
        captureTarget: event.currentTarget,
      });

      if (!started) {
        this.releaseVertexPointerCapture(event);
      }
    },

    moveVertexDrag(event) {
      if (!this.vertexDrag || event.pointerId !== this.vertexDrag.pointerId) {
        return;
      }

      event.preventDefault();
      event.stopPropagation();

      const point = this.screenPointToNaturalImagePoint(event);
      if (!point) return;

      this.updateVertexDrag(point);
    },

    endVertexDrag(event) {
      if (!this.vertexDrag) return;
      if (event && event.pointerId !== this.vertexDrag.pointerId) return;

      event?.preventDefault?.();
      event?.stopPropagation?.();

      this.releaseVertexPointerCapture(event);
      this.finishVertexDrag();
    },

    cancelVertexDrag(event) {
      if (!this.vertexDrag) return;
      if (event && event.pointerId !== this.vertexDrag.pointerId) return;

      this.releaseVertexPointerCapture(event);
      this.cancelVertexDragState();
    },

    releaseVertexPointerCapture(event) {
      try {
        const pointerId = event?.pointerId ?? this.vertexDrag?.pointerId;
        const captureTarget = event?.currentTarget || this.vertexDrag?.captureTarget;
        if (pointerId !== null && pointerId !== undefined) {
          captureTarget?.releasePointerCapture?.(pointerId);
        }
      } catch {
        // Pointer capture may already be released after pointercancel/lostpointercapture.
      }
    },

    insertVertexOnSelectedObject(event) {
      if (!this.isVertexMode || this.vertexEditMode !== "INSERT" || !this.selectedObject) {
        return false;
      }

      const segmentHit = this.findSelectedObjectSegmentNearScreenPoint(event);
      if (!segmentHit) return false;

      const point = this.svgPointToNaturalImagePoint(segmentHit.hit.projectedSvgPoint);
      if (!point) return false;

      event.preventDefault();
      event.stopPropagation();

      return this.insertVertexInSelectedObject(segmentHit.segment, point);
    },

    deleteSelectedVertex() {
      this.cancelVertexDrag();
      this.deleteSelectedVertexEdit();
    },

    findSelectedObjectSegmentNearScreenPoint(event) {
      return this.selectedObjectVertexSegments
        .map(segment => ({
          segment,
          hit: this.projectEventToDraftSegment(event, segment),
        }))
        .filter(
          item =>
            item.hit &&
            item.hit.distance <= VERTEX_SEGMENT_HIT_TOLERANCE_PX
        )
        .sort((a, b) => a.hit.distance - b.hit.distance)[0] || null;
    },

    startDraftPointDrag(index, event) {
      if (!this.isDrawMode || this.effectivePanMode) return;

      event.preventDefault();
      event.stopPropagation();
      event.currentTarget?.setPointerCapture?.(event.pointerId);

      const started = this.beginDraftPointDrag(index, {
        pointerId: event.pointerId,
        captureTarget: event.currentTarget,
        startClientX: event.clientX,
        startClientY: event.clientY,
      });

      if (!started) {
        this.releaseDraftPointerCapture(event);
      }
    },

    moveDraftPointDrag(event) {
      if (!this.draftPointDrag || event.pointerId !== this.draftPointDrag.pointerId) {
        return;
      }

      event.preventDefault();
      event.stopPropagation();

      const point = this.screenPointToNaturalImagePoint(event);
      if (!point) return;

      const deltaX = event.clientX - this.draftPointDrag.startClientX;
      const deltaY = event.clientY - this.draftPointDrag.startClientY;
      const didDrag =
        Math.abs(deltaX) > this.dragThreshold ||
        Math.abs(deltaY) > this.dragThreshold;

      this.updateDraftPointDrag(point, didDrag);
    },

    endDraftPointDrag(event) {
      if (!this.draftPointDrag) return;
      if (event && event.pointerId !== this.draftPointDrag.pointerId) return;

      event?.preventDefault?.();
      event?.stopPropagation?.();

      if (this.draftPointDrag.didDrag) {
        this.lastPointerDragAt = Date.now();
      }

      this.releaseDraftPointerCapture(event);
      this.finishDraftPointDrag();
    },

    cancelDraftPointDrag(event) {
      if (!this.draftPointDrag) return;
      if (event && event.pointerId !== this.draftPointDrag.pointerId) return;

      this.releaseDraftPointerCapture(event);
      this.cancelDraftPointDragState();
    },

    releaseDraftPointerCapture(event) {
      try {
        const pointerId = event?.pointerId ?? this.draftPointDrag?.pointerId;
        const captureTarget = event?.currentTarget || this.draftPointDrag?.captureTarget;
        if (pointerId !== null && pointerId !== undefined) {
          captureTarget?.releasePointerCapture?.(pointerId);
        }
      } catch {
        // Pointer capture may already be released after pointercancel/lostpointercapture.
      }
    },

    deleteSelectedDraftPoint() {
      this.cancelDraftPointDrag();
      this.deleteSelectedDraftPointEdit();
    },

    handleDraftSegmentPointerDown(segment, event) {
      if (!this.isDrawMode || this.effectivePanMode) return;

      event.preventDefault();
      event.stopPropagation();

      this.insertDraftPointOnSegment(segment, event);
    },

    insertDraftPointOnSegment(segment, event) {
      const segmentHit = this.projectEventToDraftSegment(event, segment);
      if (!segmentHit || segmentHit.distance > SEGMENT_HIT_TOLERANCE_PX) return;

      const point = this.svgPointToNaturalImagePoint(segmentHit.projectedSvgPoint);
      if (!point) return;

      const insertIndex = segment.endIndex === 0
        ? this.draftPolygonPoints.length
        : segment.endIndex;

      this.insertDraftPoint(insertIndex, point);
    },

    findDraftSegmentNearScreenPoint(event) {
      return this.draftPolygonSegments
        .map(segment => ({
          segment,
          hit: this.projectEventToDraftSegment(event, segment),
        }))
        .filter(item => item.hit && item.hit.distance <= SEGMENT_HIT_TOLERANCE_PX)
        .sort((a, b) => a.hit.distance - b.hit.distance)[0] || null;
    },

    projectEventToDraftSegment(event, segment) {
      const startScreen = this.svgArrayPointToScreenPoint(segment.start);
      const endScreen = this.svgArrayPointToScreenPoint(segment.end);
      if (!startScreen || !endScreen) return null;

      const screenProjection = this.projectPointToSegment(
        { x: event.clientX, y: event.clientY },
        startScreen,
        endScreen
      );
      const projectedSvgPoint = this.interpolateSvgSegmentPoint(
        segment.start,
        segment.end,
        screenProjection.t
      );

      return {
        distance: screenProjection.distance,
        projectedSvgPoint,
      };
    },

    getSegmentationSvgElement() {
      return this.$refs.segmentationOverlay?.getSvgElement?.() || null;
    },

    svgArrayPointToScreenPoint(point) {
      const svg = this.getSegmentationSvgElement();
      if (!svg || !Array.isArray(point)) return null;

      const ctm = svg.getScreenCTM?.();
      if (!ctm) return null;

      const screenPoint = new DOMPoint(point[0], point[1]).matrixTransform(ctm);
      return {
        x: screenPoint.x,
        y: screenPoint.y,
      };
    },

    projectPointToSegment(point, start, end) {
      const deltaX = end.x - start.x;
      const deltaY = end.y - start.y;
      const lengthSquared = deltaX * deltaX + deltaY * deltaY;

      if (!lengthSquared) {
        const distance = Math.hypot(point.x - start.x, point.y - start.y);
        return { t: 0, distance };
      }

      const rawT =
        ((point.x - start.x) * deltaX + (point.y - start.y) * deltaY) /
        lengthSquared;
      const t = Math.min(Math.max(rawT, 0), 1);
      const projected = {
        x: start.x + t * deltaX,
        y: start.y + t * deltaY,
      };

      return {
        t,
        distance: Math.hypot(point.x - projected.x, point.y - projected.y),
      };
    },

    interpolateSvgSegmentPoint(start, end, t) {
      return {
        x: start[0] + (end[0] - start[0]) * t,
        y: start[1] + (end[1] - start[1]) * t,
      };
    },

    handleOverlaySvgClick(event) {
      if (!this.isDrawMode) return;
      if (event.defaultPrevented) return;

      const justDragged = Date.now() - this.lastPointerDragAt < 200;
      const spaceInteraction = Date.now() - this.lastSpacePointerAt < 200;
      if (justDragged || spaceInteraction) return;

      const segmentHit = this.findDraftSegmentNearScreenPoint(event);
      if (segmentHit) {
        event.stopPropagation();
        this.insertDraftPointOnSegment(segmentHit.segment, event);
        return;
      }

      const point = this.screenPointToNaturalImagePoint(event);
      if (!point) return;

      event.stopPropagation();
      this.appendDraftPoint(point);
    },

    screenPointToSvgPoint(event) {
      const svg = this.getSegmentationSvgElement();
      if (!svg) return null;

      const ctm = svg.getScreenCTM?.();
      if (!ctm) return null;

      const point = new DOMPoint(event.clientX, event.clientY);
      const svgPoint = point.matrixTransform(ctm.inverse());
      return {
        x: svgPoint.x,
        y: svgPoint.y,
      };
    },

    svgPointToNaturalImagePoint(point) {
      const containment = this.overlayContainment;
      if (!containment.canProject) return null;

      const { offsetX, offsetY, scaleX, scaleY, displayedSize } = containment;
      const maxX = offsetX + displayedSize.width;
      const maxY = offsetY + displayedSize.height;

      if (
        point.x < offsetX ||
        point.y < offsetY ||
        point.x > maxX ||
        point.y > maxY
      ) {
        this.invalidDrawMessage = "El punto esta fuera del area real de imagen.";
        return null;
      }

      return [
        Number(((point.x - offsetX) / scaleX).toFixed(2)),
        Number(((point.y - offsetY) / scaleY).toFixed(2)),
      ];
    },

    screenPointToNaturalImagePoint(event) {
      const svgPoint = this.screenPointToSvgPoint(event);
      if (!svgPoint) return null;
      return this.svgPointToNaturalImagePoint(svgPoint);
    },

    finishDraftPolygon() {
      this.cancelDraftPointDrag();
      const newObject = this.finishDraftPolygonEdit();
      if (newObject) {
        this.showOverlayLabel(newObject.label);
      }
    },

    cancelDraftPolygon() {
      this.cancelDraftPointDrag();
      this.cancelDraftPolygonEdit();
    },

    deleteSelectedObject() {
      this.cancelVertexDrag();
      this.deleteSelectedObjectEdit();
    },

    async saveDraft() {
      if (!this.canSaveDraft || !this.activeRevisionId) return;

      const selectedKey = this.selectedObjectKey;
      const savedRevision = await this.saveActiveDraft(
        this.buildEditableSnapshot(this.activeRevision?.resultado_editado || {})
      );

      if (!savedRevision) return;

      this.loadWorkingRevision(savedRevision);

      if (
        selectedKey &&
        this.workingObjects.some(
          object => this.revisionObjectSelectionKey(object) === selectedKey
        )
      ) {
        this.selectObjectVertex(selectedKey, null);
      }

      this.viewerMode = "EDIT";
    },

    async confirmAndValidateRevision() {
      if (!this.canValidateRevision || !this.activeRevisionId) return;

      const revisionNumber = this.activeRevision?.numero_revision;
      const confirmed = window.confirm(
        `Validar revisión\n\nLa Revisión #${revisionNumber} quedará marcada como VALIDADA y ya no podrá editarse.\n\nEl resultado automático se conservará como referencia histórica.\n\n¿Deseas continuar?`
      );

      if (!confirmed) return;

      if (!this.canValidateRevision || !this.activeRevisionId) return;

      const resultadoId = this.activeResultadoSegmentacionId;
      const validatedRevision = await this.validateActiveRevision(resultadoId);
      if (!validatedRevision) return;

      this.cancelVertexDrag();
      this.cancelDraftPointDrag();
      this.loadWorkingRevision(validatedRevision);
      this.viewerMode = "NAVIGATE";
      this.editorTool = "SELECT";
      this.vertexEditMode = "MOVE";
      this.isSpacePressed = false;
      this.endImagePan();
      this.syncOverlayLabelVisibility();
      this.$emit("segmentation-completed", {
        caseId: this.caseId,
        resultadoId,
      });
    },

    confirmDiscardDraftChanges() {
      return window.confirm(
        "Hay cambios locales sin guardar. Desea descartarlos?"
      );
    },

    handleOverlayPolygonPointerDown(event) {
      if (!this.isEditMode) return;

      if (this.effectivePanMode) {
        this.lastSpacePointerAt = Date.now();
        return;
      }

      event.stopPropagation();
    },

    handleOverlayPolygonClick(selectionKey, event) {
      const justDragged = Date.now() - this.lastPointerDragAt < 200;
      const spaceInteraction = Date.now() - this.lastSpacePointerAt < 200;

      if (
        !this.isEditMode ||
        this.effectivePanMode ||
        justDragged ||
        spaceInteraction
      ) {
        return;
      }

      event.stopPropagation();

      if (this.editorTool === "VERTEX") {
        if (this.vertexEditMode === "INSERT") {
          this.insertVertexOnSelectedObject(event);
          return;
        }

        const objectItem = this.overlayDrawableObjects.find(
          item => item.selectionKey === selectionKey
        );
        const nearestVertexIndex = this.findNearestVertexIndexForEvent(
          objectItem?.object,
          event
        );
        this.selectObjectVertex(selectionKey, nearestVertexIndex);
        return;
      }

      if (this.editorTool !== "SELECT") return;

      this.selectObject(selectionKey);
    },

    provenanceDisplayName(origin) {
      const displayNames = {
        automatic: "Automático",
        manual: "Manual",
      };

      return displayNames[origin] || "No especificado";
    },

    handleEditorKeyDown(event) {
      if (
        this.isVertexMode &&
        this.selectedVertexIndex !== null &&
        (event.code === "Delete" || event.code === "Backspace") &&
        !this.isTypingTarget(event.target)
      ) {
        if (this.canDeleteSelectedVertex) {
          event.preventDefault();
          this.deleteSelectedVertex();
        }
        return;
      }

      if (
        this.isDrawMode &&
        this.selectedDraftPointIndex !== null &&
        (event.code === "Delete" || event.code === "Backspace") &&
        !this.isTypingTarget(event.target)
      ) {
        event.preventDefault();
        this.deleteSelectedDraftPoint();
        return;
      }

      if (event.code !== "Space" || !this.isEditMode || this.isTypingTarget(event.target)) {
        return;
      }

      if (event.repeat) {
        event.preventDefault();
        return;
      }

      if (this.editorTool !== "PAN") {
        this.isSpacePressed = true;
      }
      event.preventDefault();
    },

    handleEditorKeyUp(event) {
      if (event.code !== "Space") return;

      this.isSpacePressed = false;
      this.endImagePan();
    },

    handleWindowBlur() {
      this.isSpacePressed = false;
      this.endImagePan();
    },

    handleBeforeUnload(event) {
      if (!this.hasPendingDraftWork) return;

      event.preventDefault();
      event.returnValue = "";
    },

    isTypingTarget(target) {
      const tagName = target?.tagName?.toLowerCase();
      return (
        tagName === "input" ||
        tagName === "textarea" ||
        tagName === "select" ||
        target?.isContentEditable
      );
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
      this.clampImagePan();
    },

    validPolygonPoints(points) {
      return getValidPolygonPoints(points);
    },

    scalePoint(point) {
      return scalePointToOverlay(point, this.overlayContainment);
    },

    scalePolygonPoints(points) {
      return scalePolygonPointsToOverlay(points, this.overlayContainment);
    },

    computeLodVertexIndices(points) {
      const occupiedCells = new Map();
      const visibleIndices = [];

      points.forEach((point, vertexIndex) => {
        if (!this.validPolygonPoints([point]).length) return;

        const svgPoint = this.scalePoint(point);
        const screenPoint = this.svgArrayPointToScreenPoint(svgPoint);
        if (!screenPoint) return;

        const cellX = Math.floor(screenPoint.x / MIN_VERTEX_HANDLE_SPACING_PX);
        const cellY = Math.floor(screenPoint.y / MIN_VERTEX_HANDLE_SPACING_PX);

        if (this.hasNearbyOccupiedVertex(occupiedCells, cellX, cellY, screenPoint)) {
          return;
        }

        const key = this.vertexLodCellKey(cellX, cellY);
        const bucket = occupiedCells.get(key) || [];
        bucket.push(screenPoint);
        occupiedCells.set(key, bucket);
        visibleIndices.push(vertexIndex);
      });

      return visibleIndices;
    },

    hasNearbyOccupiedVertex(occupiedCells, cellX, cellY, screenPoint) {
      for (let offsetX = -1; offsetX <= 1; offsetX += 1) {
        for (let offsetY = -1; offsetY <= 1; offsetY += 1) {
          const key = this.vertexLodCellKey(cellX + offsetX, cellY + offsetY);
          const bucket = occupiedCells.get(key) || [];
          const tooClose = bucket.some(existingPoint => (
            Math.hypot(
              screenPoint.x - existingPoint.x,
              screenPoint.y - existingPoint.y
            ) < MIN_VERTEX_HANDLE_SPACING_PX
          ));

          if (tooClose) return true;
        }
      }

      return false;
    },

    vertexLodCellKey(cellX, cellY) {
      return `${cellX}:${cellY}`;
    },

    findNearestVertexIndexForEvent(object, event) {
      const points = object?.geometry?.points;
      if (!Array.isArray(points) || !points.length) return null;

      let nearest = null;

      points.forEach((point, index) => {
        const svgPoint = this.scalePoint(point);
        const screenPoint = this.svgArrayPointToScreenPoint(svgPoint);
        if (!screenPoint) return;

        const distance = Math.hypot(
          event.clientX - screenPoint.x,
          event.clientY - screenPoint.y
        );

        if (!nearest || distance < nearest.distance) {
          nearest = { index, distance };
        }
      });

      return nearest && nearest.distance <= NEAREST_VERTEX_HIT_PX
        ? nearest.index
        : null;
    },

    overlayObjectKey(object, index) {
      if (this.isEditMode && Number.isInteger(Number(object?.id))) {
        return this.revisionObjectSelectionKey(object);
      }

      const normalizedId = object?.id ?? "sin-id";
      const label = object?.label || "desconocido";
      return `${index}-${normalizedId}-${label}`;
    },

    overlayPolygonKey(item, index) {
      const normalizedId = item.object?.id ?? "sin-id";
      return `${item.selectionKey}-${index}-${normalizedId}-${item.label}`;
    },

    zoomImage() {
      this.imageZoom = Math.min(Number((this.imageZoom + ZOOM_STEP).toFixed(2)), ZOOM_MAX);
      this.clampImagePan();
    },

    zoomOutImage() {
      this.imageZoom = Math.max(Number((this.imageZoom - ZOOM_STEP).toFixed(2)), ZOOM_MIN);
      this.clampImagePan();
    },

    rotateImage() {
      this.imageRotation = (this.imageRotation + 90) % 360;
      this.clampImagePan();
    },

    resetImageView() {
      this.imageZoom = ZOOM_MIN;
      this.imageRotation = 0;
      this.panX = 0;
      this.panY = 0;
      this.isPanning = false;
      this.activePanPointerId = null;
      this.panCaptureTarget = null;
      this.didPointerDrag = false;
    },

    clampImagePan() {
      if (this.imageZoom <= 1) {
        this.panX = 0;
        this.panY = 0;
        this.isPanning = false;
        return;
      }

      const { maxX, maxY } = this.imagePanLimits;
      this.panX = Math.min(Math.max(this.panX, -maxX), maxX);
      this.panY = Math.min(Math.max(this.panY, -maxY), maxY);
    },

    startImagePan(event) {
      if (!this.effectivePanMode) return;
      if (this.imageZoom <= 1 || event.button !== 0) return;

      event.preventDefault();
      this.isPanning = true;
      this.activePanPointerId = event.pointerId;
      this.panCaptureTarget = event.currentTarget;
      this.didPointerDrag = false;
      this.panStartPointerX = event.clientX;
      this.panStartPointerY = event.clientY;
      this.panStartX = this.panX;
      this.panStartY = this.panY;
      event.currentTarget?.setPointerCapture?.(event.pointerId);
    },

    moveImagePan(event) {
      if (!this.isPanning) return;
      if (
        this.activePanPointerId !== null &&
        event.pointerId !== this.activePanPointerId
      ) {
        return;
      }

      event.preventDefault();
      const deltaX = event.clientX - this.panStartPointerX;
      const deltaY = event.clientY - this.panStartPointerY;
      const nextPanX = this.panStartX + deltaX;
      const nextPanY = this.panStartY + deltaY;
      const { maxX, maxY } = this.imagePanLimits;

      if (
        Math.abs(deltaX) > this.dragThreshold ||
        Math.abs(deltaY) > this.dragThreshold
      ) {
        this.didPointerDrag = true;
      }

      this.panX = Math.min(Math.max(nextPanX, -maxX), maxX);
      this.panY = Math.min(Math.max(nextPanY, -maxY), maxY);
    },

    endImagePan(event) {
      if (!this.isPanning) return;
      if (
        event &&
        this.activePanPointerId !== null &&
        event.pointerId !== this.activePanPointerId
      ) {
        return;
      }

      try {
        const pointerId = event?.pointerId ?? this.activePanPointerId;
        const captureTarget = event?.currentTarget || this.panCaptureTarget;
        if (pointerId !== null && pointerId !== undefined) {
          captureTarget?.releasePointerCapture?.(pointerId);
        }
      } catch {
        // Pointer capture may already be released after pointercancel/lostpointercapture.
      }
      if (this.didPointerDrag) {
        this.lastPointerDragAt = Date.now();
      }
      this.isPanning = false;
      this.activePanPointerId = null;
      this.panCaptureTarget = null;
      this.didPointerDrag = false;
    },

    overlayColorForLabel(label) {
      if (this.segmentationLabelPalette[label]) {
        return this.segmentationLabelPalette[label];
      }

      const index = Math.max(this.overlayLabelNames.indexOf(label), 0);
      return OVERLAY_FALLBACK_PALETTE[index % OVERLAY_FALLBACK_PALETTE.length];
    },

    overlayFillForLabel(label, context = "overlay") {
      const color = this.overlayColorForLabel(label);
      const alpha = context === "draft"
        ? 0.06
        : this.overlayFillAlpha();

      return this.withRgbaAlpha(color.fill, alpha);
    },

    overlayFillAlpha() {
      if (!this.isEditMode) return 0.16;
      if (this.editorTool === "DRAW") return 0.06;
      if (this.editorTool === "VERTEX") return 0.09;
      if (this.editorTool === "SELECT") return 0.14;
      return 0.1;
    },

    withRgbaAlpha(color, alpha) {
      const rgbaMatch = String(color).match(
        /rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)(?:\s*,\s*[\d.]+)?\s*\)/
      );

      if (!rgbaMatch) return color;

      return `rgba(${rgbaMatch[1]}, ${rgbaMatch[2]}, ${rgbaMatch[3]}, ${alpha})`;
    },

    overlayLabelRenderOrder(label) {
      return getLabelConfig(this.activeSampleType, label)?.order || 10;
    },

    overlayLabelDisplayName(label) {
      return getLabelConfig(this.activeSampleType, label)?.displayName || label;
    },

    syncOverlayLabelVisibility() {
      const nextVisibility = {};

      this.overlayLabelNames.forEach(label => {
        nextVisibility[label] =
          this.overlayLabelVisibility[label] !== undefined
            ? this.overlayLabelVisibility[label]
            : true;
      });

      this.overlayLabelVisibility = nextVisibility;
    },

    setOverlayLabelVisibility(label, visible) {
      this.overlayLabelVisibility = {
        ...this.overlayLabelVisibility,
        [label]: visible,
      };

      if (!visible && this.selectedObject?.label === label) {
        this.cancelVertexDrag();
        this.clearSelection();
      }
    },
  },

  mounted() {
    window.addEventListener("resize", this.updateImageMeasurements);
    window.addEventListener("keydown", this.handleEditorKeyDown);
    window.addEventListener("keyup", this.handleEditorKeyUp);
    window.addEventListener("blur", this.handleWindowBlur);
    window.addEventListener("beforeunload", this.handleBeforeUnload);

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

    this.cargarMuestrasSangre();
  },

  beforeUnmount() {
    window.removeEventListener("resize", this.updateImageMeasurements);
    window.removeEventListener("keydown", this.handleEditorKeyDown);
    window.removeEventListener("keyup", this.handleEditorKeyUp);
    window.removeEventListener("blur", this.handleWindowBlur);
    window.removeEventListener("beforeunload", this.handleBeforeUnload);
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

.gallery-title-group {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.gallery-header h3 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: #2c3e50;
}

.gallery-title-group span {
  color: #64748b;
  font-size: 11px;
}

.gallery-count {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 3px 10px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
}

.sample-type-tabs {
  display: grid;
  flex-shrink: 0;
  gap: 6px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  margin-bottom: 12px;
}

.sample-type-tab {
  background: #f8fafc;
  border: 1px solid #d9e2ec;
  border-radius: 8px;
  color: #52606d;
  cursor: pointer;
  font-size: 12px;
  font-weight: 700;
  padding: 7px 8px;
}

.sample-type-tab.active {
  background: #e3f2fd;
  border-color: #1e88e5;
  color: #1565c0;
}

.sample-type-tab:disabled {
  cursor: wait;
  opacity: 0.65;
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

.thumb.disabled {
  cursor: wait;
  opacity: 0.45;
}

.thumb.disabled:hover {
  transform: none;
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
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 4px;
  opacity: 0;
  transition: opacity 0.3s ease;
}

.thumb:hover .thumb-overlay,
.thumb.active .thumb-overlay {
  opacity: 1;
}

.thumb-name,
.thumb-id {
  color: white;
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.thumb-name {
  font-size: 11px;
  font-weight: 700;
}

.thumb-id {
  font-size: 10px;
  font-weight: 500;
  opacity: 0.85;
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

.empty-gallery.error p {
  color: #c62828;
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

.mode-btn {
  background: #ffffff;
  border: 2px solid #d9e2ec;
  border-radius: 8px;
  color: #2c3e50;
  cursor: pointer;
  font-size: 12px;
  font-weight: 700;
  padding: 8px 12px;
}

.mode-btn.active {
  background: #e3f2fd;
  border-color: #1e88e5;
  color: #1565c0;
}

.mode-btn:disabled {
  cursor: wait;
  opacity: 0.7;
}

.editor-tool-btn {
  padding-inline: 10px;
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
  pointer-events: none;
  user-select: none;
}

.image-transform-layer {
  height: 100%;
  inset: 0;
  position: absolute;
  transform-origin: center center;
  user-select: none;
  width: 100%;
}

.image-transform-layer.is-pannable {
  cursor: grab;
}

.image-transform-layer.is-panning {
  cursor: grabbing;
}

.image-transform-layer.is-edit-mode {
  cursor: default;
}

.image-transform-layer.is-edit-mode.is-pannable {
  cursor: grab;
}

.image-transform-layer.is-edit-mode.is-panning {
  cursor: grabbing;
}

.image-transform-layer.is-edit-mode.is-effective-pan-mode {
  cursor: grab;
}

.image-transform-layer.is-edit-mode.is-effective-pan-mode.is-panning {
  cursor: grabbing;
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

.control-btn.danger {
  border-color: #ffcdd2;
  color: #c62828;
}

.control-btn.danger:hover:not(:disabled) {
  background: #ffebee;
  border-color: #ef5350;
}

.control-btn.success {
  border-color: #c8e6c9;
  color: #2e7d32;
}

.control-btn.success:hover:not(:disabled) {
  background: #e8f5e9;
  border-color: #43a047;
}

.control-btn:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

/* DATOS */
.data-container {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.selected-object-panel {
  background: #f8f9fa;
  border: 1px solid #d9e2ec;
  border-radius: 10px;
  padding: 10px 12px;
}

.selected-object-header {
  align-items: center;
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
}

.selected-object-header h4 {
  color: #2c3e50;
  font-size: 13px;
  margin: 0;
}

.editor-hint {
  background: #fff8e1;
  border: 1px solid #ffe082;
  border-radius: 999px;
  color: #8a6d1d;
  font-size: 11px;
  font-weight: 700;
  padding: 3px 8px;
}

.selected-object-grid {
  display: grid;
  font-size: 12px;
  gap: 6px 10px;
  grid-template-columns: auto 1fr;
}

.selected-object-grid span {
  color: #667;
}

.selected-object-grid strong {
  color: #2c3e50;
}

.selected-object-empty {
  color: #667;
  font-size: 12px;
  line-height: 1.4;
}

.editor-actions {
  display: grid;
  gap: 8px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  margin-top: 10px;
}

.drawing-panel {
  border-top: 1px solid #d9e2ec;
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 10px;
  padding-top: 10px;
}

.vertex-mode-panel {
  border-top: 1px solid #d9e2ec;
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 10px;
  padding-top: 10px;
}

.vertex-mode-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.drawing-label-row {
  align-items: center;
  display: flex;
  gap: 8px;
  justify-content: space-between;
}

.drawing-label-row span {
  color: #667;
  font-size: 12px;
}

.drawing-label-select {
  border: 1px solid #d9e2ec;
  border-radius: 8px;
  color: #2c3e50;
  font-size: 12px;
  min-width: 130px;
  padding: 6px 8px;
}

.draft-status {
  background: #f0f4f8;
  border: 1px solid #d9e2ec;
  border-radius: 8px;
  color: #52606d;
  font-size: 12px;
  padding: 8px 10px;
}

.draft-status.warning,
.segmentation-status.warning {
  background: #fff8e1;
  border-color: #ffe082;
  color: #8a6d1d;
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

.full-width {
  width: 100%;
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

  .card-header {
    padding: 10px 14px;
  }

  .split-view {
    gap: 12px;
    grid-template-columns: minmax(0, 1fr) minmax(280px, 320px);
    padding: 12px;
  }

  .data-container {
    gap: 10px;
  }

  .segmentation-status {
    padding: 8px 10px;
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
}
</style>
