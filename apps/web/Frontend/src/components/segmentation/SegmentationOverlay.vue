<template>
  <svg
    v-if="show"
    ref="segmentationSvg"
    class="segmentation-svg-overlay"
    :class="{
      'is-editable': isEditMode,
      'is-pan-mode': effectivePanMode,
      'is-draw-mode': isDrawMode,
      'is-vertex-mode': isVertexMode,
      'is-vertex-insert-mode': isVertexMode && vertexEditMode === 'INSERT'
    }"
    :width="imageRenderedSize.width"
    :height="imageRenderedSize.height"
    :viewBox="`0 0 ${imageRenderedSize.width} ${imageRenderedSize.height}`"
    @click="$emit('overlay-click', $event)"
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
        @pointerdown="$emit('polygon-pointerdown', $event)"
        @click="$emit('polygon-click', polygon.selectionKey, $event)"
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
          fill: draftPolygonFill,
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
        @pointerdown="$emit('draft-segment-pointerdown', segment, $event)"
        @click.stop.prevent
      />
      <circle
        v-for="(point, index) in draftPolygonSvgPoints"
        :key="`draft-point-hit-${index}`"
        :cx="point[0]"
        :cy="point[1]"
        class="draft-polygon-point-hit"
        :r="draftPointHitRadius"
        @pointerdown="$emit('draft-point-pointerdown', index, $event)"
        @pointermove="$emit('draft-point-pointermove', $event)"
        @pointerup="$emit('draft-point-pointerup', $event)"
        @pointercancel="$emit('draft-point-pointercancel', $event)"
        @lostpointercapture="$emit('draft-point-pointercancel', $event)"
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
          @pointerdown="$emit('vertex-pointerdown', handle, $event)"
          @pointermove="$emit('vertex-pointermove', $event)"
          @pointerup="$emit('vertex-pointerup', $event)"
          @pointercancel="$emit('vertex-pointercancel', $event)"
          @lostpointercapture="$emit('vertex-pointercancel', $event)"
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
</template>

<script>
export default {
  name: "SegmentationOverlay",
  emits: [
    "overlay-click",
    "polygon-pointerdown",
    "polygon-click",
    "draft-segment-pointerdown",
    "draft-point-pointerdown",
    "draft-point-pointermove",
    "draft-point-pointerup",
    "draft-point-pointercancel",
    "vertex-pointerdown",
    "vertex-pointermove",
    "vertex-pointerup",
    "vertex-pointercancel",
  ],
  props: {
    show: {
      type: Boolean,
      required: true,
    },
    isEditMode: {
      type: Boolean,
      required: true,
    },
    effectivePanMode: {
      type: Boolean,
      required: true,
    },
    isDrawMode: {
      type: Boolean,
      required: true,
    },
    isVertexMode: {
      type: Boolean,
      required: true,
    },
    vertexEditMode: {
      type: String,
      required: true,
    },
    imageRenderedSize: {
      type: Object,
      required: true,
    },
    overlayPolygons: {
      type: Array,
      required: true,
    },
    selectionHighlightPolygons: {
      type: Array,
      required: true,
    },
    overlayStrokeWidth: {
      type: Number,
      required: true,
    },
    selectedOverlayStrokeWidth: {
      type: Number,
      required: true,
    },
    draftPolygonSvgPoints: {
      type: Array,
      required: true,
    },
    draftPolygonSvgPointsString: {
      type: String,
      required: true,
    },
    draftPolygonFill: {
      type: String,
      required: true,
    },
    draftPolygonSegments: {
      type: Array,
      required: true,
    },
    drawingColor: {
      type: Object,
      required: true,
    },
    draftStrokeWidth: {
      type: Number,
      required: true,
    },
    draftSegmentHitStrokeWidth: {
      type: Number,
      required: true,
    },
    draftPointHitRadius: {
      type: Number,
      required: true,
    },
    draftPointRadius: {
      type: Number,
      required: true,
    },
    draftSelectedPointRadius: {
      type: Number,
      required: true,
    },
    draftPointStrokeWidth: {
      type: Number,
      required: true,
    },
    draftSelectedPointStrokeWidth: {
      type: Number,
      required: true,
    },
    selectedDraftPointIndex: {
      type: Number,
      default: null,
    },
    selectedVertexHandles: {
      type: Array,
      required: true,
    },
    vertexHandleHitRadius: {
      type: Number,
      required: true,
    },
    vertexHandleRadius: {
      type: Number,
      required: true,
    },
    vertexSelectedHandleRadius: {
      type: Number,
      required: true,
    },
    vertexHandleStrokeWidth: {
      type: Number,
      required: true,
    },
    vertexSelectedHandleStrokeWidth: {
      type: Number,
      required: true,
    },
  },
  expose: ["getSvgElement"],
  methods: {
    getSvgElement() {
      return this.$refs.segmentationSvg || null;
    },
  },
};
</script>

<style scoped>
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
</style>
