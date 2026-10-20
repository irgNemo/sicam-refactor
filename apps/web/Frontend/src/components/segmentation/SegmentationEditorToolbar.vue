<template>
  <div class="viewer-editor-toolbar">
    <div class="editor-mode-row">
      <div class="viewer-mode-buttons">
        <button
          class="mode-btn"
          :class="{ active: viewerMode === 'NAVIGATE' }"
          title="Navegar por la imagen"
          :aria-pressed="viewerMode === 'NAVIGATE'"
          @click="$emit('change-viewer-mode', 'NAVIGATE')"
        >
          Navegar
        </button>
        <button
          class="mode-btn"
          :class="{ active: viewerMode === 'EDIT' }"
          :disabled="revisionLoading"
          title="Editar revision experta"
          :aria-pressed="viewerMode === 'EDIT'"
          @click="$emit('change-viewer-mode', 'EDIT')"
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
          @click="$emit('change-editor-tool', 'SELECT')"
        >
          Seleccionar
        </button>
        <button
          class="mode-btn editor-tool-btn"
          :class="{ active: editorTool === 'PAN' }"
          title="Mover visor"
          :aria-pressed="editorTool === 'PAN'"
          @click="$emit('change-editor-tool', 'PAN')"
        >
          Mover vista
        </button>
        <button
          class="mode-btn editor-tool-btn"
          :class="{ active: editorTool === 'DRAW' }"
          title="Dibujar máscara"
          :aria-pressed="editorTool === 'DRAW'"
          @click="$emit('change-editor-tool', 'DRAW')"
        >
          Dibujar
        </button>
        <button
          class="mode-btn editor-tool-btn"
          :class="{ active: editorTool === 'VERTEX' }"
          title="Editar contorno"
          :aria-pressed="editorTool === 'VERTEX'"
          @click="$emit('change-editor-tool', 'VERTEX')"
        >
          Editar contorno
        </button>
      </div>
      <div class="editor-tool-buttons" aria-label="Historial de edición" :inert="drawingDisabled || undefined">
        <button class="mode-btn" :disabled="!canUndo" @click="$emit('undo')">Deshacer</button>
        <button class="mode-btn" :disabled="!canRedo" @click="$emit('redo')">Rehacer</button>
      </div>
    </div>
    <div v-if="isEditMode && editorTool === 'DRAW'" class="editor-tool-buttons" role="group" aria-label="Tipo a dibujar">
      <span class="drawing-type-label">Dibujar:</span>
      <button
        v-for="labelConfig in drawingLabels"
        :key="labelConfig.label"
        class="mode-btn"
        :disabled="drawingDisabled"
        :class="{ active: drawingLabel === labelConfig.label }"
        :aria-pressed="drawingLabel === labelConfig.label"
        @click="$emit('change-drawing-label', labelConfig.label)"
      >{{ labelConfig.displayName }}</button>
    </div>
  </div>
</template>

<script>
export default {
  name: "SegmentationEditorToolbar",
  emits: ["change-viewer-mode", "change-editor-tool", "undo", "redo", "change-drawing-label"],
  props: {
    canUndo: { type: Boolean, default: false },
    canRedo: { type: Boolean, default: false },
    drawingDisabled: { type: Boolean, default: false },
    drawingLabels: { type: Array, default: () => [] },
    drawingLabel: { type: String, default: "" },
    viewerMode: {
      type: String,
      required: true,
    },
    isEditMode: {
      type: Boolean,
      required: true,
    },
    revisionLoading: {
      type: Boolean,
      required: true,
    },
    activeRevision: {
      type: Object,
      default: null,
    },
    isDraftDirty: {
      type: Boolean,
      required: true,
    },
    editorTool: {
      type: String,
      required: true,
    },
  },
};
</script>

<style scoped>
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
  cursor: not-allowed;
  opacity: 0.7;
}

.revision-badge {
  background: #f0f4f8;
  border-radius: 999px;
  color: #52606d;
  font-size: 12px;
  font-weight: 700;
  padding: 6px 10px;
  max-width: 100%;
  overflow-wrap: anywhere;
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

.drawing-type-label {
  align-self: center;
  font-size: 12px;
  font-weight: 700;
}
</style>
