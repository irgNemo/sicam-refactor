<template>
  <section class="effective-overlay-card">
    <header class="overlay-header">
      <div>
        <h4>Segmentacion efectiva</h4>
        <p>Objetos usados por la caracterizacion actual.</p>
      </div>
      <span
        v-if="sourceDisplay"
        class="source-badge"
      >
        {{ sourceDisplay }}
      </span>
    </header>

    <div
      v-if="loading"
      class="overlay-status neutral"
    >
      Cargando segmentacion efectiva...
    </div>
    <div
      v-else-if="error"
      class="overlay-status error"
    >
      {{ error }}
    </div>
    <div
      v-else-if="!effectiveSegmentation"
      class="overlay-status neutral"
    >
      No hay una segmentacion efectiva disponible.
    </div>
    <div
      v-else-if="!imageSrc"
      class="overlay-status warning"
    >
      La imagen de la muestra no esta disponible.
    </div>

    <template v-else>
      <div
        ref="imageFrame"
        class="overlay-frame"
      >
        <img
          ref="image"
          :src="imageSrc"
          alt="Muestra microscopica con segmentacion efectiva"
          draggable="false"
          @load="onImageLoad"
          @dragstart.prevent
        />
        <svg
          v-if="canShowOverlay"
          class="readonly-overlay"
          :width="renderedSize.width"
          :height="renderedSize.height"
          :viewBox="`0 0 ${renderedSize.width} ${renderedSize.height}`"
          aria-label="Contornos de la segmentacion efectiva"
          role="group"
        >
          <polygon
            v-for="polygon in overlayPolygons"
            :key="polygon.key"
            :points="polygon.points"
            :class="{ 'selected-object': polygon.selected, 'selectable-cell': polygon.cellId != null }"
            :role="polygon.cellId != null ? 'button' : undefined"
            :tabindex="polygon.cellId != null ? 0 : undefined"
            :aria-label="polygon.cellId != null ? `Célula ${polygon.cellId}` : undefined"
            :aria-pressed="polygon.cellId != null ? selectedCellId === polygon.cellId : undefined"
            :style="{
              fill: polygon.fill,
              stroke: polygon.stroke,
              strokeWidth: polygon.selected ? overlayStrokeWidth * 2.5 : overlayStrokeWidth
            }"
            @click.stop="selectPolygon(polygon)"
            @keydown.enter.stop.prevent="selectPolygon(polygon)"
            @keydown.space.stop.prevent="selectPolygon(polygon)"
          />
        </svg>
      </div>

      <div
        v-if="overlayLabels.length"
        class="overlay-legend"
        aria-label="Capas visibles"
      >
        <label
          v-for="item in overlayLabels"
          :key="item.label"
          class="legend-item"
        >
          <input
            type="checkbox"
            :checked="item.visible"
            @change="setLabelVisibility(item.label, $event.target.checked)"
          />
          <span
            class="legend-swatch"
            :style="{ background: item.fill, borderColor: item.stroke }"
          ></span>
          {{ item.displayName }}
        </label>
      </div>

      <p
        v-if="imageLoaded && !drawableObjects.length"
        class="overlay-empty"
      >
        La segmentacion efectiva no contiene poligonos visibles.
      </p>
    </template>
  </section>
</template>

<script>
import {
  calculateOverlayContainment,
  scalePolygonPointsToOverlay,
} from "../../composables/useSegmentationViewport";
import {
  getLabelPalette,
  getSegmentationTypeConfig,
  OVERLAY_FALLBACK_PALETTE,
  SAMPLE_TYPES,
} from "../../domain/segmentationTypes";

export default {
  name: "CharacterizationEffectiveOverlay",
  emits: ["select-cell"],
  props: {
    cells: {
      type: Array,
      default: () => [],
    },
    selectedCellId: {
      type: [Number, String],
      default: null,
    },
    imageSrc: {
      type: String,
      default: "",
    },
    effectiveSegmentation: {
      type: Object,
      default: null,
    },
    loading: {
      type: Boolean,
      default: false,
    },
    error: {
      type: String,
      default: "",
    },
    sampleType: {
      type: String,
      default: SAMPLE_TYPES.SALIVA,
    },
  },

  data() {
    return {
      naturalSize: { width: 0, height: 0 },
      renderedSize: { width: 0, height: 0 },
      labelVisibility: {},
      resizeObserver: null,
    };
  },

  computed: {
    cellsById() {
      return new Map(this.cells.filter(cell => cell.membrane_id != null)
        .map(cell => [cell.membrane_id, cell]));
    },

    selectedObjectIds() {
      const cell = this.cellsById.get(this.selectedCellId);
      // Backend relations only; IDs are qualified by label to avoid collisions.
      return {
        membrana: new Set(cell ? [cell.membrane_id] : []),
        nucleo: new Set((cell?.nuclei || []).map(item => item.id)),
        micronucleo: new Set((cell?.micronuclei || []).map(item => item.id)),
      };
    },

    imageLoaded() {
      return Boolean(this.naturalSize.width && this.naturalSize.height);
    },

    containment() {
      return calculateOverlayContainment(this.naturalSize, this.renderedSize);
    },

    effectiveObjects() {
      const objects = this.effectiveSegmentation?.resultado?.objects;
      return Array.isArray(objects) ? objects : [];
    },

    drawableObjects() {
      return this.effectiveObjects
        .map((object, index) => ({
          object,
          index,
          label: object?.label || "desconocido",
          points: object?.geometry?.type === "polygon"
            ? scalePolygonPointsToOverlay(
              object.geometry.points,
              this.containment
            )
            : [],
        }))
        .filter(item => item.points.length >= 3);
    },

    labelNames() {
      return [...new Set(this.drawableObjects.map(item => item.label))].sort();
    },

    labelPalette() {
      return getLabelPalette(this.sampleType);
    },

    overlayLabels() {
      const configuredLabels = getSegmentationTypeConfig(this.sampleType).labels;

      return this.labelNames.map((label, index) => {
        const configured = configuredLabels.find(item => item.label === label);
        const palette = this.colorForLabel(label, index);
        return {
          label,
          displayName: configured?.displayName || label,
          visible: this.labelVisibility[label] !== false,
          fill: palette.fill,
          stroke: palette.stroke,
        };
      });
    },

    overlayPolygons() {
      return this.drawableObjects
        .filter(item => this.labelVisibility[item.label] !== false)
        // Keep nuclei/MN above membranes so their clicks cannot select a cell underneath.
        .sort((a, b) => Number(b.label === "membrana") - Number(a.label === "membrana"))
        .map(item => {
          const palette = this.colorForLabel(
            item.label,
            this.labelNames.indexOf(item.label)
          );
          return {
            key: `${item.label}-${item.object?.id ?? item.index}-${item.index}`,
            points: item.points.map(point => point.join(",")).join(" "),
            fill: palette.fill,
            stroke: palette.stroke,
            cellId: item.label === "membrana" && this.cellsById.has(item.object.id)
              ? item.object.id : null,
            selected: this.selectedObjectIds[item.label]?.has(item.object.id) || false,
          };
        });
    },

    canShowOverlay() {
      return Boolean(
        this.containment.canProject &&
        this.overlayPolygons.length
      );
    },

    overlayStrokeWidth() {
      const shortestSide = Math.min(
        this.renderedSize.width || 0,
        this.renderedSize.height || 0
      );
      return Math.max(1.25, Math.min(2.5, shortestSide / 240));
    },

    sourceDisplay() {
      if (!this.effectiveSegmentation) return "";
      if (this.effectiveSegmentation.fuente === "VALIDADA") {
        const revision = this.effectiveSegmentation.revision?.numero_revision;
        return revision ? `Revision #${revision} validada` : "Revision validada";
      }
      if (this.effectiveSegmentation.fuente === "AUTOMATICO") {
        return "Automatico";
      }
      return "Fuente no definida";
    },
  },

  watch: {
    imageSrc() {
      this.naturalSize = { width: 0, height: 0 };
      this.$nextTick(this.observeImageFrame);
    },

    effectiveSegmentation: {
      handler() {
        this.syncLabelVisibility();
        this.$nextTick(this.observeImageFrame);
      },
      deep: false,
    },

    labelNames() {
      this.syncLabelVisibility();
    },
  },

  mounted() {
    if (typeof ResizeObserver !== "undefined") {
      this.resizeObserver = new ResizeObserver(this.updateRenderedSize);
    }
    window.addEventListener("resize", this.updateRenderedSize);
    this.observeImageFrame();
  },

  beforeUnmount() {
    this.resizeObserver?.disconnect();
    window.removeEventListener("resize", this.updateRenderedSize);
  },

  methods: {
    selectPolygon(polygon) {
      if (polygon.cellId != null) this.$emit("select-cell", polygon.cellId);
    },

    onImageLoad() {
      const image = this.$refs.image;
      this.naturalSize = {
        width: image?.naturalWidth || 0,
        height: image?.naturalHeight || 0,
      };
      this.updateRenderedSize();
    },

    updateRenderedSize() {
      const frame = this.$refs.imageFrame;
      this.renderedSize = {
        width: Math.round(frame?.clientWidth || 0),
        height: Math.round(frame?.clientHeight || 0),
      };
    },

    observeImageFrame() {
      this.resizeObserver?.disconnect();
      if (this.$refs.imageFrame) {
        this.resizeObserver?.observe(this.$refs.imageFrame);
      }
      this.updateRenderedSize();
    },

    syncLabelVisibility() {
      const next = { ...this.labelVisibility };
      this.labelNames.forEach(label => {
        if (!(label in next)) next[label] = true;
      });
      this.labelVisibility = next;
    },

    setLabelVisibility(label, visible) {
      this.labelVisibility = {
        ...this.labelVisibility,
        [label]: visible,
      };
    },

    colorForLabel(label, fallbackIndex) {
      if (this.labelPalette[label]) return this.labelPalette[label];
      const safeIndex = Math.max(fallbackIndex, 0);
      return OVERLAY_FALLBACK_PALETTE[
        safeIndex % OVERLAY_FALLBACK_PALETTE.length
      ];
    },
  },
};
</script>

<style scoped>
.effective-overlay-card {
  background: #f8fafc;
  border: 1px solid #dde4ee;
  border-radius: 10px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-width: 100%;
  min-width: 0;
  padding: 14px;
  width: 100%;
}

.overlay-header {
  align-items: flex-start;
  display: flex;
  gap: 12px;
  justify-content: space-between;
}

.overlay-header h4 {
  color: #344054;
  font-size: 14px;
  margin: 0 0 3px;
}

.overlay-header p {
  color: #667085;
  font-size: 12px;
  margin: 0;
}

.source-badge {
  background: #e8f5e9;
  border-radius: 999px;
  color: #2e7d32;
  flex: 0 0 auto;
  font-size: 11px;
  font-weight: 700;
  padding: 5px 9px;
}

.overlay-frame {
  background: #111827;
  border-radius: 8px;
  height: clamp(320px, 45vw, 520px);
  overflow: hidden;
  position: relative;
  width: 100%;
}

.overlay-frame img,
.readonly-overlay {
  display: block;
  height: 100%;
  inset: 0;
  position: absolute;
  width: 100%;
}

.overlay-frame img {
  object-fit: contain;
  user-select: none;
}

.readonly-overlay {
  pointer-events: none;
}

.readonly-overlay polygon {
  pointer-events: all;
  vector-effect: non-scaling-stroke;
}

.readonly-overlay .selectable-cell {
  cursor: pointer;
}

.readonly-overlay .selected-object,
.readonly-overlay .selectable-cell:focus-visible {
  filter: drop-shadow(0 0 2px #ffffff);
}

.overlay-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.legend-item {
  align-items: center;
  background: #ffffff;
  border: 1px solid #dde4ee;
  border-radius: 999px;
  color: #475467;
  cursor: pointer;
  display: flex;
  font-size: 12px;
  gap: 6px;
  padding: 5px 9px;
}

.legend-item input {
  margin: 0;
}

.legend-swatch {
  border: 2px solid;
  border-radius: 3px;
  height: 12px;
  width: 12px;
}

.overlay-status,
.overlay-empty {
  border-radius: 8px;
  font-size: 12px;
  line-height: 1.4;
  margin: 0;
  padding: 12px;
}

.overlay-status.neutral,
.overlay-empty {
  background: #eef4ff;
  color: #3b5b8a;
}

.overlay-status.warning {
  background: #fff8e1;
  color: #8a6d1d;
}

.overlay-status.error {
  background: #ffebee;
  color: #c62828;
}

@media (max-width: 1023px) {
  .overlay-frame {
    height: clamp(280px, 60vw, 460px);
  }
}
</style>
