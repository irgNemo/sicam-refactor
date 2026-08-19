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
          </div>

          <div class="card-body split-view">

            <!-- IMAGEN -->
            <div class="image-container">
              <div v-if="imagenSeleccionada" class="viewer-editor-toolbar">
                <div class="editor-mode-row">
                  <div class="viewer-mode-buttons">
                    <button
                      class="mode-btn"
                      :class="{ active: viewerMode === 'NAVIGATE' }"
                      title="Navegar por la imagen"
                      :aria-pressed="viewerMode === 'NAVIGATE'"
                      @click="setViewerMode('NAVIGATE')"
                    >
                      Navegar
                    </button>
                    <button
                      class="mode-btn"
                      :class="{ active: viewerMode === 'EDIT' }"
                      :disabled="revisionLoading"
                      title="Editar revision experta"
                      :aria-pressed="viewerMode === 'EDIT'"
                      @click="setViewerMode('EDIT')"
                    >
                      {{ revisionLoading ? 'Cargando...' : 'Editar' }}
                    </button>
                  </div>
                  <div class="editor-revision-status">
                    <span
                      v-if="isEditMode && activeRevision"
                      class="revision-badge"
                    >
                      Revisión #{{ activeRevision.numero_revision }} · {{ activeRevision.estado }}
                    </span>
                    <span
                      v-if="isDraftDirty"
                      class="revision-badge dirty"
                    >
                      Cambios sin guardar
                    </span>
                  </div>
                </div>
                <div
                  v-if="isEditMode"
                  class="editor-tools-row"
                >
                  <div class="editor-tool-buttons">
                    <button
                      class="mode-btn editor-tool-btn"
                      :class="{ active: editorTool === 'SELECT' }"
                      title="Seleccionar máscaras"
                      :aria-pressed="editorTool === 'SELECT'"
                      @click="setEditorTool('SELECT')"
                    >
                      Seleccionar
                    </button>
                    <button
                      class="mode-btn editor-tool-btn"
                      :class="{ active: editorTool === 'PAN' }"
                      title="Mover visor"
                      :aria-pressed="editorTool === 'PAN'"
                      @click="setEditorTool('PAN')"
                    >
                      Mover
                    </button>
                    <button
                      class="mode-btn editor-tool-btn"
                      :class="{ active: editorTool === 'DRAW' }"
                      title="Dibujar máscara"
                      :aria-pressed="editorTool === 'DRAW'"
                      @click="setEditorTool('DRAW')"
                    >
                      Dibujar
                    </button>
                    <button
                      class="mode-btn editor-tool-btn"
                      :class="{ active: editorTool === 'VERTEX' }"
                      title="Editar contorno"
                      :aria-pressed="editorTool === 'VERTEX'"
                      @click="setEditorTool('VERTEX')"
                    >
                      Editar contorno
                    </button>
                  </div>
                </div>
              </div>

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
                  <svg
                    v-if="shouldShowSegmentationOverlay"
                    class="segmentation-svg-overlay"
                    :class="{
                      'is-editable': isEditMode,
                      'is-pan-mode': effectivePanMode,
                      'is-draw-mode': isDrawMode,
                      'is-vertex-mode': isVertexMode,
                      'is-vertex-insert-mode': isVertexMode && vertexEditMode === 'INSERT'
                    }"
                    ref="segmentationSvg"
                    :width="imageRenderedSize.width"
                    :height="imageRenderedSize.height"
                    :viewBox="`0 0 ${imageRenderedSize.width} ${imageRenderedSize.height}`"
                    @click="handleOverlaySvgClick"
                  >
                    <g class="segmentation-polygons">
                      <polygon
                        v-for="polygon in overlayPolygons"
                        :key="polygon.key"
                        :points="polygon.points"
                        class="segmentation-polygon"
                        :class="{
                          manual: polygon.origin === 'manual',
                          selected: polygon.selected
                        }"
                        :style="{
                          fill: polygon.fill,
                          stroke: polygon.stroke,
                          strokeWidth: overlayStrokeWidth
                        }"
                        @pointerdown="handleOverlayPolygonPointerDown"
                        @click="handleOverlayPolygonClick(polygon.selectionKey, $event)"
                      />
                    </g>
                    <g
                      class="selection-highlight"
                      pointer-events="none"
                    >
                      <polygon
                        v-for="polygon in selectionHighlightPolygons"
                        :key="`highlight-${polygon.key}`"
                        :points="polygon.points"
                        class="segmentation-selection-highlight"
                        :class="{ manual: polygon.origin === 'manual' }"
                        :style="{
                          stroke: polygon.stroke,
                          strokeWidth: selectedOverlayStrokeWidth
                        }"
                      />
                    </g>
                    <g
                      v-if="draftPolygonSvgPoints.length"
                      class="draft-polygon-layer"
                    >
                      <polyline
                        :points="draftPolygonSvgPointsString"
                        class="draft-polygon-line"
                        :style="{
                          stroke: drawingColor.stroke,
                          strokeWidth: draftStrokeWidth
                        }"
                      />
                      <polygon
                        v-if="draftPolygonSvgPoints.length >= 3"
                        :points="draftPolygonSvgPointsString"
                        class="draft-polygon-fill"
                        :style="{
                          fill: overlayFillForLabel(drawingLabel, 'draft'),
                          stroke: drawingColor.stroke,
                          strokeWidth: draftStrokeWidth
                        }"
                      />
                      <line
                        v-for="segment in draftPolygonSegments"
                        :key="segment.key"
                        class="draft-segment-hit"
                        :x1="segment.start[0]"
                        :y1="segment.start[1]"
                        :x2="segment.end[0]"
                        :y2="segment.end[1]"
                        :stroke-width="draftSegmentHitStrokeWidth"
                        @pointerdown="handleDraftSegmentPointerDown(segment, $event)"
                        @click.stop.prevent
                      />
                      <circle
                        v-for="(point, index) in draftPolygonSvgPoints"
                        :key="`draft-point-hit-${index}`"
                        :cx="point[0]"
                        :cy="point[1]"
                        class="draft-polygon-point-hit"
                        :r="draftPointHitRadius"
                        @pointerdown="startDraftPointDrag(index, $event)"
                        @pointermove="moveDraftPointDrag"
                        @pointerup="endDraftPointDrag"
                        @pointercancel="cancelDraftPointDrag"
                        @lostpointercapture="cancelDraftPointDrag"
                        @click.stop.prevent
                      />
                      <circle
                        v-for="(point, index) in draftPolygonSvgPoints"
                        :key="`draft-point-${index}`"
                        :cx="point[0]"
                        :cy="point[1]"
                        class="draft-polygon-point"
                        :class="{ selected: selectedDraftPointIndex === index }"
                        :r="selectedDraftPointIndex === index ? draftSelectedPointRadius : draftPointRadius"
                        :style="{
                          fill: drawingColor.stroke,
                          strokeWidth: selectedDraftPointIndex === index
                            ? draftSelectedPointStrokeWidth
                            : draftPointStrokeWidth
                        }"
                      />
                    </g>
                    <g
                      v-if="selectedVertexHandles.length"
                      class="vertex-handle-layer"
                    >
                      <g
                        v-for="handle in selectedVertexHandles"
                        :key="handle.key"
                      >
                        <circle
                          class="vertex-handle-hit"
                          :class="handle.role"
                          :cx="handle.x"
                          :cy="handle.y"
                          :r="vertexHandleHitRadius"
                          @pointerdown="startVertexDrag(handle, $event)"
                          @pointermove="moveVertexDrag"
                          @pointerup="endVertexDrag"
                          @pointercancel="cancelVertexDrag"
                          @lostpointercapture="cancelVertexDrag"
                        />
                        <circle
                          class="vertex-handle"
                          :class="handle.role"
                          :cx="handle.x"
                          :cy="handle.y"
                          :r="handle.selected ? vertexSelectedHandleRadius : vertexHandleRadius"
                          :style="{
                            strokeWidth: handle.selected
                              ? vertexSelectedHandleStrokeWidth
                              : vertexHandleStrokeWidth
                          }"
                        />
                      </g>
                    </g>
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
                <button
                  class="control-btn"
                  title="Aumentar zoom"
                  aria-label="Aumentar zoom"
                  @click="zoomImage"
                >
                  <span>＋</span> Zoom {{ Math.round(imageZoom * 100) }}%
                </button>
                <button
                  class="control-btn"
                  title="Reducir zoom"
                  aria-label="Reducir zoom"
                  @click="zoomOutImage"
                >
                  <span>－</span> Zoom
                </button>
                <button
                  class="control-btn"
                  title="Rotar imagen"
                  aria-label="Rotar imagen"
                  @click="rotateImage"
                >
                  <span>↻</span> Rotar
                </button>
                <button
                  class="control-btn"
                  title="Ajustar vista"
                  aria-label="Ajustar vista"
                  @click="resetImageView"
                >
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
                      <option value="membrana">Membranas</option>
                      <option value="nucleo">Núcleos</option>
                      <option value="micronucleo">Micronúcleos</option>
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
              </div>

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
                    @click="setViewerMode('EDIT')"
                  >
                    Continuar edición
                  </button>
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
import {
  getSegmentationRevisions,
  getOrCreateSegmentationDraft,
  updateSegmentationDraft,
} from "../services/segmentationRevisionService";

const ZOOM_MIN = 1;
const ZOOM_MAX = 8;
const ZOOM_STEP = 0.25;
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
      viewerMode: "NAVIGATE",
      editorTool: "SELECT",
      vertexEditMode: "MOVE",
      activeRevision: null,
      activeRevisionId: null,
      pendingDraftRevision: null,
      pendingDraftLoading: false,
      pendingDraftError: "",
      workingObjects: [],
      isDraftDirty: false,
      isSavingDraft: false,
      saveDraftError: "",
      saveDraftMessage: "",
      draftBaselineSignature: "",
      undoStack: [],
      redoStack: [],
      manualObjectIdCursor: 0,
      drawingLabel: "membrana",
      draftPolygonPoints: [],
      selectedDraftPointIndex: null,
      draftPointDrag: null,
      selectedVertexIndex: null,
      invalidDrawMessage: "",
      vertexDrag: null,
      revisionLoading: false,
      revisionError: "",
      selectedObjectKey: null,
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
      return this.activeRevisionSummary || this.resultadoNormalizadoActivo?.summary || null;
    },

    activeOverlayObjects() {
      if (this.isEditMode) {
        return this.workingObjects;
      }

      return Array.isArray(this.resultadoNormalizadoActivo?.objects)
        ? this.resultadoNormalizadoActivo.objects
        : [];
    },

    workingSummary() {
      const counts = {
        membrana: 0,
        nucleo: 0,
        micronucleo: 0,
      };

      this.workingObjects.forEach(object => {
        if (Object.prototype.hasOwnProperty.call(counts, object.label)) {
          counts[object.label] += 1;
        }
      });

      return {
        counts_by_label: counts,
        total_objects: this.workingObjects.length,
      };
    },

    selectedObject() {
      if (!this.isEditMode || this.selectedObjectKey === null) return null;

      const selectedItem = this.overlayDrawableObjects.find(
        item => item.selectionKey === this.selectedObjectKey
      );

      return selectedItem?.object || null;
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

    canDeleteSelectedVertex() {
      const points = this.selectedObject?.geometry?.points;
      return (
        this.isVertexMode &&
        this.selectedVertexIndex !== null &&
        Array.isArray(points) &&
        points.length > 3
      );
    },

    hasPendingDraftWork() {
      return this.isDraftDirty || this.draftPolygonPoints.length > 0;
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

    showPendingDraftNotice() {
      return (
        this.viewerMode === "NAVIGATE" &&
        this.pendingDraftRevision?.estado === "BORRADOR"
      );
    },

    imagePanLimits() {
      const width = this.imageRenderedSize.width;
      const height = this.imageRenderedSize.height;

      if (!width || !height || this.imageZoom <= 1) {
        return { maxX: 0, maxY: 0 };
      }

      const rotation = ((this.imageRotation % 360) + 360) % 360;
      const rotatedSideways = rotation === 90 || rotation === 270;
      const transformedWidth = (rotatedSideways ? height : width) * this.imageZoom;
      const transformedHeight = (rotatedSideways ? width : height) * this.imageZoom;

      return {
        maxX: Math.max(0, Math.round((transformedWidth - width) / 2)),
        maxY: Math.max(0, Math.round((transformedHeight - height) / 2)),
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

    activeResultadoSegmentacionId(newId, oldId) {
      if (newId !== oldId) {
        if (this.hasPendingDraftWork && !this.confirmDiscardDraftChanges()) {
          return;
        }
        this.resetEditorState({ clearRevision: true });
        this.loadPendingDraftRevision(newId);
      }
    },

    drawingLabel(label) {
      if (this.isEditMode && this.editorTool === "DRAW") {
        this.showOverlayLabel(label);
      }
    },
  },

  methods: {
    selectImagen(muestra) {
      if (
        this.imagenSeleccionada &&
        muestra?.id_muestra !== this.imagenSeleccionada.id_muestra &&
        this.hasPendingDraftWork &&
        !this.confirmDiscardDraftChanges()
      ) {
        return;
      }

      this.imagenSeleccionada = muestra;
      this.segmentacionResultado = null;
      this.segmentacionError = "";
      this.segmentacionLoading = false;
      this.historialSegmentacion = [];
      this.historialError = "";
      this.historialLoading = false;
      this.resetImageMeasurements();
      this.resetImageView();
      this.resetEditorState({ clearRevision: true });
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
          this.ensureRevisionBelongsToActiveResult();
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

    setViewerMode(mode) {
      if (mode === "NAVIGATE") {
        if (this.hasPendingDraftWork && !this.confirmDiscardDraftChanges()) {
          return;
        }
        this.viewerMode = "NAVIGATE";
        this.editorTool = "SELECT";
        this.selectedObjectKey = null;
        this.selectedVertexIndex = null;
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
        this.activeRevision = null;
        this.activeRevisionId = null;
        this.selectedObjectKey = null;
        this.selectedVertexIndex = null;
        this.revisionError = "No hay resultado de segmentacion para editar.";
        return;
      }

      if (
        this.activeRevision &&
        this.activeRevision.resultado_segmentacion === resultadoId
      ) {
        this.viewerMode = "EDIT";
        this.editorTool = "SELECT";
        this.pendingDraftRevision = this.activeRevision;
        if (!this.workingObjects.length) {
          this.loadWorkingRevision(this.activeRevision);
        }
        this.syncOverlayLabelVisibility();
        return;
      }

      this.revisionLoading = true;
      this.activeRevision = null;
      this.activeRevisionId = null;
      this.selectedObjectKey = null;
      this.selectedVertexIndex = null;

      try {
        const response = await getOrCreateSegmentationDraft(resultadoId);

        if (this.activeResultadoSegmentacionId !== resultadoId) return;

        this.activeRevision = response.data;
        this.activeRevisionId = response.data.id_revision_segmentacion;
        this.pendingDraftRevision = response.data;
        this.loadWorkingRevision(response.data);
        this.viewerMode = "EDIT";
        this.editorTool = "SELECT";
        this.syncOverlayLabelVisibility();
      } catch (error) {
        console.error("Error al cargar borrador de revision:", error);

        if (this.activeResultadoSegmentacionId === resultadoId) {
          this.viewerMode = "NAVIGATE";
          this.activeRevision = null;
          this.activeRevisionId = null;
          this.selectedObjectKey = null;
          this.selectedVertexIndex = null;
          this.revisionError =
            error.response?.data?.error || "No fue posible cargar el borrador experto.";
        }
      } finally {
        if (this.activeResultadoSegmentacionId === resultadoId) {
          this.revisionLoading = false;
        }
      }
    },

    resetEditorState({ clearRevision } = { clearRevision: true }) {
      this.viewerMode = "NAVIGATE";
      this.editorTool = "SELECT";
      this.selectedObjectKey = null;
      this.selectedVertexIndex = null;
      this.revisionError = "";
      this.revisionLoading = false;
      this.isSpacePressed = false;
      this.endImagePan();
      this.didPointerDrag = false;
      this.activePanPointerId = null;
      this.panCaptureTarget = null;
      this.cancelDraftPointDrag();
      this.draftPolygonPoints = [];
      this.selectedDraftPointIndex = null;
      this.invalidDrawMessage = "";
      this.cancelVertexDrag();
      this.isDraftDirty = false;
      this.isSavingDraft = false;
      this.saveDraftError = "";
      this.saveDraftMessage = "";
      this.draftBaselineSignature = "";
      this.undoStack = [];
      this.redoStack = [];
      this.workingObjects = [];
      this.manualObjectIdCursor = 0;

      if (clearRevision) {
        this.activeRevision = null;
        this.activeRevisionId = null;
        this.pendingDraftRevision = null;
        this.pendingDraftLoading = false;
        this.pendingDraftError = "";
      }
    },

    ensureRevisionBelongsToActiveResult() {
      if (
        this.activeRevision &&
        this.activeRevision.resultado_segmentacion !== this.activeResultadoSegmentacionId
      ) {
        this.resetEditorState({ clearRevision: true });
      }
    },

    async loadPendingDraftRevision(resultadoId = this.activeResultadoSegmentacionId) {
      this.pendingDraftRevision = null;
      this.pendingDraftError = "";

      if (!resultadoId) return;

      if (
        this.activeRevision?.resultado_segmentacion === resultadoId &&
        this.activeRevision?.estado === "BORRADOR"
      ) {
        this.pendingDraftRevision = this.activeRevision;
        return;
      }

      this.pendingDraftLoading = true;

      try {
        const response = await getSegmentationRevisions(resultadoId);

        if (this.activeResultadoSegmentacionId !== resultadoId) return;

        const revisions = Array.isArray(response.data) ? response.data : [];
        this.pendingDraftRevision =
          revisions.find(revision => revision.estado === "BORRADOR") || null;
      } catch (error) {
        if (this.activeResultadoSegmentacionId === resultadoId) {
          this.pendingDraftError =
            error.response?.data?.error ||
            "No fue posible consultar revisiones pendientes.";
        }
      } finally {
        if (this.activeResultadoSegmentacionId === resultadoId) {
          this.pendingDraftLoading = false;
        }
      }
    },

    cloneJson(value) {
      return value == null ? value : JSON.parse(JSON.stringify(value));
    },

    serializeObjects(objects) {
      return JSON.stringify(objects || []);
    },

    loadWorkingRevision(revision) {
      const objects = Array.isArray(revision?.resultado_editado?.objects)
        ? revision.resultado_editado.objects
        : [];

      this.workingObjects = this.cloneJson(objects);
      this.draftBaselineSignature = this.serializeObjects(this.workingObjects);
      this.isDraftDirty = false;
      this.isSavingDraft = false;
      this.saveDraftError = "";
      this.saveDraftMessage = "";
      this.cancelDraftPointDrag();
      this.draftPolygonPoints = [];
      this.selectedDraftPointIndex = null;
      this.invalidDrawMessage = "";
      this.undoStack = [];
      this.redoStack = [];
      this.selectedObjectKey = null;
      this.selectedVertexIndex = null;
      this.manualObjectIdCursor = this.maxRevisionObjectId(this.workingObjects);
    },

    updateDraftDirtyState() {
      this.isDraftDirty =
        this.serializeObjects(this.workingObjects) !== this.draftBaselineSignature;
    },

    maxRevisionObjectId(objects) {
      return objects.reduce((maxId, object) => {
        const objectId = Number(object?.id);
        return Number.isInteger(objectId) && objectId > maxId ? objectId : maxId;
      }, 0);
    },

    nextRevisionObjectId() {
      const usedIds = new Set(
        this.workingObjects
          .map(object => Number(object?.id))
          .filter(objectId => Number.isInteger(objectId) && objectId > 0)
      );
      let candidate = Math.max(
        this.manualObjectIdCursor,
        this.maxRevisionObjectId(this.workingObjects)
      ) + 1;

      while (usedIds.has(candidate)) {
        candidate += 1;
      }

      this.manualObjectIdCursor = candidate;
      return candidate;
    },

    revisionObjectSelectionKey(object) {
      return `revision-${object.id}`;
    },

    findWorkingObjectIndexByKey(selectionKey) {
      return this.workingObjects.findIndex(
        object => this.revisionObjectSelectionKey(object) === selectionKey
      );
    },

    findWorkingObjectIndexById(objectId) {
      return this.workingObjects.findIndex(object => object.id === objectId);
    },

    updateWorkingObjectAt(index, updater) {
      if (index < 0) return;

      const nextObjects = this.cloneJson(this.workingObjects);
      nextObjects[index] = updater(nextObjects[index]);
      this.workingObjects = nextObjects;
    },

    applyRevisionOperation(operation) {
      const object = this.cloneJson(operation.object);

      if (operation.type === "CREATE_OBJECT") {
        const index = Math.min(
          Math.max(operation.index, 0),
          this.workingObjects.length
        );
        this.workingObjects.splice(index, 0, object);
        this.selectedObjectKey = this.revisionObjectSelectionKey(object);
      }

      if (operation.type === "DELETE_OBJECT") {
        this.workingObjects = this.workingObjects.filter(
          item => item.id !== object.id
        );
        if (this.selectedObjectKey === this.revisionObjectSelectionKey(object)) {
          this.selectedObjectKey = null;
          this.selectedVertexIndex = null;
        }
      }

      if (operation.type === "MOVE_VERTEX") {
        this.applyVertexMove(
          operation.objectId,
          operation.vertexIndex,
          operation.after,
          operation.provenanceAfter
        );
      }

      if (["INSERT_VERTEX", "DELETE_VERTEX"].includes(operation.type)) {
        this.applyVertexPointsSnapshot(
          operation.objectId,
          operation.afterPoints,
          operation.provenanceAfter
        );
        this.selectedVertexIndex = operation.selectedVertexIndexAfter ?? null;
      }

      this.updateDraftDirtyState();
    },

    revertRevisionOperation(operation) {
      const object = this.cloneJson(operation.object);

      if (operation.type === "CREATE_OBJECT") {
        this.workingObjects = this.workingObjects.filter(
          item => item.id !== object.id
        );
        if (this.selectedObjectKey === this.revisionObjectSelectionKey(object)) {
          this.selectedObjectKey = null;
          this.selectedVertexIndex = null;
        }
      }

      if (operation.type === "DELETE_OBJECT") {
        const index = Math.min(
          Math.max(operation.index, 0),
          this.workingObjects.length
        );
        this.workingObjects.splice(index, 0, object);
      }

      if (operation.type === "MOVE_VERTEX") {
        this.applyVertexMove(
          operation.objectId,
          operation.vertexIndex,
          operation.before,
          operation.provenanceBefore
        );
      }

      if (["INSERT_VERTEX", "DELETE_VERTEX"].includes(operation.type)) {
        this.applyVertexPointsSnapshot(
          operation.objectId,
          operation.beforePoints,
          operation.provenanceBefore
        );
        this.selectedVertexIndex = operation.selectedVertexIndexBefore ?? null;
      }

      this.updateDraftDirtyState();
    },

    pushUndoOperation(operation) {
      this.undoStack.push(this.cloneJson(operation));
      this.redoStack = [];
      this.updateDraftDirtyState();
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

    buildModifiedProvenance(provenance) {
      return {
        ...(this.cloneJson(provenance) || {}),
        modified: true,
      };
    },

    setVertexEditMode(mode) {
      if (!["MOVE", "INSERT"].includes(mode)) return;

      this.cancelVertexDrag();
      this.vertexEditMode = mode;
    },

    applyVertexMove(objectId, vertexIndex, point, provenance) {
      const objectIndex = this.findWorkingObjectIndexById(objectId);
      if (objectIndex < 0) return;

      this.updateWorkingObjectAt(objectIndex, object => {
        const points = Array.isArray(object.geometry?.points)
          ? this.cloneJson(object.geometry.points)
          : [];
        if (!points[vertexIndex]) return object;

        points[vertexIndex] = this.cloneJson(point);

        return {
          ...object,
          geometry: {
            ...object.geometry,
            points,
          },
          provenance: this.cloneJson(provenance || object.provenance),
        };
      });
    },

    applyVertexPointsSnapshot(objectId, points, provenance) {
      const objectIndex = this.findWorkingObjectIndexById(objectId);
      if (objectIndex < 0 || !Array.isArray(points)) return;

      this.updateWorkingObjectAt(objectIndex, object => ({
        ...object,
        geometry: {
          ...object.geometry,
          points: this.cloneJson(points),
        },
        provenance: this.cloneJson(provenance || object.provenance),
      }));
    },

    startVertexDrag(handle, event) {
      if (!this.isVertexMode || this.effectivePanMode || this.vertexEditMode !== "MOVE") return;

      const objectIndex = this.findWorkingObjectIndexById(handle.objectId);
      const object = this.workingObjects[objectIndex];
      const beforePoint = object?.geometry?.points?.[handle.vertexIndex];
      if (!beforePoint) return;

      event.preventDefault();
      event.stopPropagation();
      event.currentTarget?.setPointerCapture?.(event.pointerId);

      this.selectedVertexIndex = handle.vertexIndex;
      this.vertexDrag = {
        objectId: handle.objectId,
        vertexIndex: handle.vertexIndex,
        pointerId: event.pointerId,
        captureTarget: event.currentTarget,
        before: this.cloneJson(beforePoint),
        after: this.cloneJson(beforePoint),
        provenanceBefore: this.cloneJson(object.provenance),
        provenanceAfter: this.buildModifiedProvenance(object.provenance),
      };
    },

    moveVertexDrag(event) {
      if (!this.vertexDrag || event.pointerId !== this.vertexDrag.pointerId) {
        return;
      }

      event.preventDefault();
      event.stopPropagation();

      const point = this.screenPointToNaturalImagePoint(event);
      if (!point) return;

      this.vertexDrag.after = this.cloneJson(point);
      this.applyVertexMove(
        this.vertexDrag.objectId,
        this.vertexDrag.vertexIndex,
        point,
        this.vertexDrag.provenanceAfter
      );
      this.updateDraftDirtyState();
    },

    endVertexDrag(event) {
      if (!this.vertexDrag) return;
      if (event && event.pointerId !== this.vertexDrag.pointerId) return;

      event?.preventDefault?.();
      event?.stopPropagation?.();

      const operation = {
        type: "MOVE_VERTEX",
        objectId: this.vertexDrag.objectId,
        vertexIndex: this.vertexDrag.vertexIndex,
        before: this.cloneJson(this.vertexDrag.before),
        after: this.cloneJson(this.vertexDrag.after),
        provenanceBefore: this.cloneJson(this.vertexDrag.provenanceBefore),
        provenanceAfter: this.cloneJson(this.vertexDrag.provenanceAfter),
      };
      const changed =
        this.serializeObjects([operation.before]) !==
        this.serializeObjects([operation.after]);

      this.releaseVertexPointerCapture(event);
      this.vertexDrag = null;

      if (changed) {
        this.pushUndoOperation(operation);
      } else {
        this.updateDraftDirtyState();
      }
    },

    cancelVertexDrag(event) {
      if (!this.vertexDrag) return;
      if (event && event.pointerId !== this.vertexDrag.pointerId) return;

      this.applyVertexMove(
        this.vertexDrag.objectId,
        this.vertexDrag.vertexIndex,
        this.vertexDrag.before,
        this.vertexDrag.provenanceBefore
      );
      this.releaseVertexPointerCapture(event);
      this.vertexDrag = null;
      this.updateDraftDirtyState();
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

      const object = this.selectedObject;
      const beforePoints = Array.isArray(object.geometry?.points)
        ? this.cloneJson(object.geometry.points)
        : [];
      if (beforePoints.length < 3) return false;

      const insertIndex = segmentHit.segment.endIndex === 0
        ? beforePoints.length
        : segmentHit.segment.startIndex + 1;
      const afterPoints = [
        ...beforePoints.slice(0, insertIndex),
        point,
        ...beforePoints.slice(insertIndex),
      ];
      const provenanceBefore = this.cloneJson(object.provenance);
      const provenanceAfter = this.buildModifiedProvenance(object.provenance);
      const selectedVertexIndexBefore = this.selectedVertexIndex;

      event.preventDefault();
      event.stopPropagation();

      this.applyVertexPointsSnapshot(object.id, afterPoints, provenanceAfter);
      this.selectedObjectKey = this.revisionObjectSelectionKey(object);
      this.selectedVertexIndex = insertIndex;
      this.pushUndoOperation({
        type: "INSERT_VERTEX",
        objectId: object.id,
        vertexIndex: insertIndex,
        point: this.cloneJson(point),
        beforePoints,
        afterPoints,
        provenanceBefore,
        provenanceAfter,
        selectedVertexIndexBefore,
        selectedVertexIndexAfter: insertIndex,
      });
      return true;
    },

    deleteSelectedVertex() {
      if (!this.canDeleteSelectedVertex || !this.selectedObject) return;

      const object = this.selectedObject;
      const beforePoints = this.cloneJson(object.geometry.points);
      const point = this.cloneJson(beforePoints[this.selectedVertexIndex]);
      const afterPoints = beforePoints.filter(
        (_item, index) => index !== this.selectedVertexIndex
      );
      const selectedVertexIndexBefore = this.selectedVertexIndex;
      const selectedVertexIndexAfter = Math.min(
        selectedVertexIndexBefore,
        afterPoints.length - 1
      );
      const provenanceBefore = this.cloneJson(object.provenance);
      const provenanceAfter = this.buildModifiedProvenance(object.provenance);

      this.cancelVertexDrag();
      this.applyVertexPointsSnapshot(object.id, afterPoints, provenanceAfter);
      this.selectedVertexIndex = selectedVertexIndexAfter;
      this.pushUndoOperation({
        type: "DELETE_VERTEX",
        objectId: object.id,
        vertexIndex: selectedVertexIndexBefore,
        point,
        beforePoints,
        afterPoints,
        provenanceBefore,
        provenanceAfter,
        selectedVertexIndexBefore,
        selectedVertexIndexAfter,
      });
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

      const beforePoint = this.draftPolygonPoints[index];
      if (!beforePoint) return;

      event.preventDefault();
      event.stopPropagation();
      event.currentTarget?.setPointerCapture?.(event.pointerId);

      this.selectedDraftPointIndex = index;
      this.draftPointDrag = {
        index,
        pointerId: event.pointerId,
        captureTarget: event.currentTarget,
        before: this.cloneJson(beforePoint),
        after: this.cloneJson(beforePoint),
        startClientX: event.clientX,
        startClientY: event.clientY,
        didDrag: false,
      };
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
      if (
        Math.abs(deltaX) > this.dragThreshold ||
        Math.abs(deltaY) > this.dragThreshold
      ) {
        this.draftPointDrag.didDrag = true;
      }

      this.draftPointDrag.after = this.cloneJson(point);
      this.updateDraftPointAt(this.draftPointDrag.index, point);
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
      this.draftPointDrag = null;
    },

    cancelDraftPointDrag(event) {
      if (!this.draftPointDrag) return;
      if (event && event.pointerId !== this.draftPointDrag.pointerId) return;

      this.updateDraftPointAt(this.draftPointDrag.index, this.draftPointDrag.before);
      this.releaseDraftPointerCapture(event);
      this.draftPointDrag = null;
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

    updateDraftPointAt(index, point) {
      if (index < 0 || index >= this.draftPolygonPoints.length) return;

      const nextPoints = this.cloneJson(this.draftPolygonPoints);
      nextPoints[index] = this.cloneJson(point);
      this.draftPolygonPoints = nextPoints;
      this.invalidDrawMessage = "";
    },

    deleteSelectedDraftPoint() {
      if (this.selectedDraftPointIndex === null) return;
      if (
        this.selectedDraftPointIndex < 0 ||
        this.selectedDraftPointIndex >= this.draftPolygonPoints.length
      ) {
        this.selectedDraftPointIndex = null;
        return;
      }

      this.cancelDraftPointDrag();
      this.draftPolygonPoints = this.draftPolygonPoints.filter(
        (_point, index) => index !== this.selectedDraftPointIndex
      );
      this.selectedDraftPointIndex = null;
      this.invalidDrawMessage = "";
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

      this.draftPolygonPoints = [
        ...this.draftPolygonPoints.slice(0, insertIndex),
        point,
        ...this.draftPolygonPoints.slice(insertIndex),
      ];
      this.selectedDraftPointIndex = insertIndex;
      this.invalidDrawMessage = "";
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

    svgArrayPointToScreenPoint(point) {
      const svg = this.$refs.segmentationSvg;
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
      this.invalidDrawMessage = "";
      this.draftPolygonPoints = [
        ...this.draftPolygonPoints,
        point,
      ];
      this.selectedDraftPointIndex = this.draftPolygonPoints.length - 1;
    },

    screenPointToSvgPoint(event) {
      const svg = this.$refs.segmentationSvg;
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
      if (this.draftPolygonPoints.length < 3) return;
      this.cancelDraftPointDrag();

      const newObject = {
        id: this.nextRevisionObjectId(),
        label: this.drawingLabel,
        geometry: {
          type: "polygon",
          points: this.cloneJson(this.draftPolygonPoints),
        },
        provenance: {
          origin: "manual",
          base_object_id: null,
        },
      };
      const index = this.workingObjects.length;

      this.workingObjects = [
        ...this.workingObjects,
        newObject,
      ];
      this.draftPolygonPoints = [];
      this.selectedDraftPointIndex = null;
      this.invalidDrawMessage = "";
      this.selectedObjectKey = this.revisionObjectSelectionKey(newObject);
      this.pushUndoOperation({
        type: "CREATE_OBJECT",
        object: newObject,
        index,
      });
      this.showOverlayLabel(newObject.label);
    },

    cancelDraftPolygon() {
      this.cancelDraftPointDrag();
      this.draftPolygonPoints = [];
      this.selectedDraftPointIndex = null;
      this.invalidDrawMessage = "";
    },

    deleteSelectedObject() {
      if (!this.selectedObjectKey) return;

      const index = this.findWorkingObjectIndexByKey(this.selectedObjectKey);
      if (index < 0) return;

      this.cancelVertexDrag();
      const object = this.cloneJson(this.workingObjects[index]);
      this.workingObjects.splice(index, 1);
      this.selectedObjectKey = null;
      this.selectedVertexIndex = null;
      this.pushUndoOperation({
        type: "DELETE_OBJECT",
        object,
        index,
      });
    },

    undoRevisionEdit() {
      const operation = this.undoStack.pop();
      if (!operation) return;

      this.revertRevisionOperation(operation);
      this.redoStack.push(this.cloneJson(operation));
    },

    redoRevisionEdit() {
      const operation = this.redoStack.pop();
      if (!operation) return;

      this.applyRevisionOperation(operation);
      this.undoStack.push(this.cloneJson(operation));
    },

    buildEditableSnapshot() {
      return {
        ...this.cloneJson(this.activeRevision?.resultado_editado || {}),
        objects: this.cloneJson(this.workingObjects),
      };
    },

    async saveDraft() {
      if (!this.canSaveDraft || !this.activeRevisionId) return;

      this.isSavingDraft = true;
      this.saveDraftError = "";
      this.saveDraftMessage = "";

      try {
        const response = await updateSegmentationDraft(
          this.activeRevisionId,
          this.buildEditableSnapshot()
        );
        const selectedKey = this.selectedObjectKey;

        this.activeRevision = response.data;
        this.activeRevisionId = response.data.id_revision_segmentacion;
        this.pendingDraftRevision = response.data;
        this.loadWorkingRevision(response.data);

        if (
          selectedKey &&
          this.workingObjects.some(
            object => this.revisionObjectSelectionKey(object) === selectedKey
          )
        ) {
          this.selectedObjectKey = selectedKey;
        }

        this.viewerMode = "EDIT";
        this.saveDraftMessage = "Borrador guardado.";
      } catch (error) {
        this.saveDraftError =
          error.response?.data?.resultado_editado?.[0] ||
          error.response?.data?.detail ||
          "No fue posible guardar el borrador.";
      } finally {
        this.isSavingDraft = false;
      }
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
        const changedObject = this.selectedObjectKey !== selectionKey;

        this.selectedObjectKey = selectionKey;
        if (nearestVertexIndex !== null) {
          this.selectedVertexIndex = nearestVertexIndex;
        } else if (changedObject) {
          this.selectedVertexIndex = null;
        }
        return;
      }

      if (this.editorTool !== "SELECT") return;

      this.selectedVertexIndex = null;
      this.selectedObjectKey =
        this.selectedObjectKey === selectionKey ? null : selectionKey;
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
      return this.overlayFallbackPalette[index % this.overlayFallbackPalette.length];
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
      const order = {
        membrana: 1,
        nucleo: 2,
        micronucleo: 3,
      };

      return order[label] || 10;
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

      if (!visible && this.selectedObject?.label === label) {
        this.cancelVertexDrag();
        this.selectedObjectKey = null;
        this.selectedVertexIndex = null;
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

.viewer-editor-toolbar {
  background: #f8fafc;
  border: 1px solid #d9e2ec;
  border-radius: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
  padding: 8px;
}

.editor-mode-row,
.editor-tools-row {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: space-between;
  min-width: 0;
}

.viewer-mode-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  min-width: 0;
}

.editor-revision-status {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  justify-content: flex-end;
  min-width: 0;
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

.revision-badge {
  background: #f0f4f8;
  border-radius: 999px;
  color: #52606d;
  font-size: 12px;
  font-weight: 700;
  padding: 6px 10px;
  white-space: nowrap;
}

.revision-badge.dirty {
  background: #fff8e1;
  color: #8a6d1d;
}

.editor-tool-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  min-width: 0;
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

.segmentation-svg-overlay {
  display: block;
  height: 100%;
  inset: 0;
  pointer-events: none;
  position: absolute;
  width: 100%;
  z-index: 2;
}

.segmentation-svg-overlay.is-editable {
  pointer-events: auto;
}

.segmentation-svg-overlay.is-pan-mode .segmentation-polygons {
  pointer-events: none;
}

.segmentation-svg-overlay.is-pan-mode .segmentation-polygon {
  pointer-events: none;
}

.segmentation-svg-overlay.is-draw-mode .segmentation-polygons {
  pointer-events: none;
}

.segmentation-svg-overlay.is-draw-mode .segmentation-polygon {
  pointer-events: none;
}

.segmentation-svg-overlay.is-vertex-mode .segmentation-polygon {
  pointer-events: none;
}

.segmentation-svg-overlay.is-vertex-mode .segmentation-polygon.selected {
  pointer-events: visiblePainted;
}

.segmentation-polygon {
  fill: rgba(30, 136, 229, 0.16);
  stroke: rgba(30, 136, 229, 0.92);
  stroke-linejoin: round;
  vector-effect: non-scaling-stroke;
}

.segmentation-svg-overlay.is-editable .segmentation-polygon {
  cursor: pointer;
  pointer-events: visiblePainted;
}

.segmentation-svg-overlay.is-editable.is-pan-mode .segmentation-polygon,
.segmentation-svg-overlay.is-editable.is-draw-mode .segmentation-polygon {
  pointer-events: none;
}

.segmentation-svg-overlay.is-editable.is-vertex-mode .segmentation-polygon {
  pointer-events: none;
}

.segmentation-svg-overlay.is-editable.is-vertex-mode .segmentation-polygon.selected {
  pointer-events: visiblePainted;
}

.segmentation-polygon.manual {
  stroke-dasharray: 7 4;
}

.selection-highlight {
  pointer-events: none;
}

.segmentation-selection-highlight {
  fill: transparent;
  filter: drop-shadow(0 0 5px rgba(0, 0, 0, 0.55));
  pointer-events: none;
  stroke-linejoin: round;
  vector-effect: non-scaling-stroke;
}

.segmentation-selection-highlight.manual {
  stroke-dasharray: 7 4;
}

.draft-polygon-layer {
  pointer-events: auto;
}

.segmentation-svg-overlay.is-pan-mode .draft-polygon-layer {
  pointer-events: none;
}

.draft-polygon-line,
.draft-polygon-fill {
  stroke-linejoin: round;
  vector-effect: non-scaling-stroke;
}

.draft-polygon-line {
  fill: none;
  stroke-dasharray: 6 4;
}

.draft-polygon-fill {
  opacity: 0.85;
}

.draft-segment-hit {
  cursor: copy;
  opacity: 0;
  pointer-events: stroke;
  stroke: #000;
  stroke-linecap: round;
  vector-effect: non-scaling-stroke;
}

.draft-polygon-point-hit {
  cursor: grab;
  fill: transparent;
  pointer-events: all;
  stroke: transparent;
}

.draft-polygon-point-hit:active {
  cursor: grabbing;
}

.draft-polygon-point {
  pointer-events: none;
  stroke: white;
  stroke-width: 1.25;
  vector-effect: non-scaling-stroke;
}

.draft-polygon-point.selected {
  stroke: #263238;
  stroke-width: 1.5;
}

.vertex-handle-layer {
  pointer-events: auto;
}

.segmentation-svg-overlay.is-pan-mode .vertex-handle-layer {
  pointer-events: none;
}

.segmentation-svg-overlay.is-vertex-insert-mode .vertex-handle-layer {
  pointer-events: none;
}

.vertex-handle-hit {
  cursor: grab;
  fill: transparent;
  pointer-events: all;
  stroke: transparent;
}

.vertex-handle-hit:active {
  cursor: grabbing;
}

.vertex-handle {
  fill: #ffffff;
  pointer-events: none;
  stroke: #263238;
  stroke-width: 1.5;
  vector-effect: non-scaling-stroke;
}

.vertex-handle.neighbor {
  fill: #f8fafc;
  stroke: #607d8b;
}

.vertex-handle.selected {
  fill: #263238;
  stroke: #ffffff;
  stroke-width: 1.5;
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
  display: block;
  flex: 1;
  min-height: 0;
  min-width: 0;
  overflow: visible;
}

.objects-table-wrapper {
  padding: 16px;
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

  .objects-table-wrapper {
    padding: 12px;
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

  .objects-table-wrapper {
    padding: 12px;
  }
}
</style>
