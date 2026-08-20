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
          Mover
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
    </div>
  </div>
</template>

<script>
export default {
  name: "SegmentationEditorToolbar",
  emits: ["change-viewer-mode", "change-editor-tool"],
  props: {
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
</style>
