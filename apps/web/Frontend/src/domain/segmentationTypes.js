export const SAMPLE_TYPES = {
  SALIVA: "SALIVA",
  BLOOD: "SANGRE",
};

export const SEGMENTATION_TYPE_CONFIG = {
  [SAMPLE_TYPES.SALIVA]: {
    sampleType: SAMPLE_TYPES.SALIVA,
    defaultDrawingLabel: "membrana",
    labels: [
      {
        label: "membrana",
        displayName: "Membranas",
        order: 1,
        editable: true,
        stroke: "rgba(30, 136, 229, 0.92)",
        fill: "rgba(30, 136, 229, 0.16)",
      },
      {
        label: "nucleo",
        displayName: "Núcleos",
        order: 2,
        editable: true,
        stroke: "rgba(239, 83, 80, 0.92)",
        fill: "rgba(239, 83, 80, 0.16)",
      },
      {
        label: "micronucleo",
        displayName: "Micronúcleos",
        order: 3,
        editable: true,
        stroke: "rgba(67, 160, 71, 0.92)",
        fill: "rgba(67, 160, 71, 0.16)",
      },
    ],
  },
  [SAMPLE_TYPES.BLOOD]: {
    sampleType: SAMPLE_TYPES.BLOOD,
    defaultDrawingLabel: "membrana",
    labels: [
      {
        label: "membrana",
        displayName: "Membranas",
        order: 1,
        editable: true,
        stroke: "rgba(30, 136, 229, 0.92)",
        fill: "rgba(30, 136, 229, 0.16)",
      },
      {
        label: "micronucleo",
        displayName: "Micronúcleos",
        order: 2,
        editable: true,
        stroke: "rgba(67, 160, 71, 0.92)",
        fill: "rgba(67, 160, 71, 0.16)",
      },
    ],
  },
};

export const OVERLAY_FALLBACK_PALETTE = [
  { stroke: "rgba(30, 136, 229, 0.92)", fill: "rgba(30, 136, 229, 0.16)" },
  { stroke: "rgba(67, 160, 71, 0.92)", fill: "rgba(67, 160, 71, 0.16)" },
  { stroke: "rgba(239, 83, 80, 0.92)", fill: "rgba(239, 83, 80, 0.16)" },
  { stroke: "rgba(251, 140, 0, 0.92)", fill: "rgba(251, 140, 0, 0.16)" },
  { stroke: "rgba(142, 68, 173, 0.92)", fill: "rgba(142, 68, 173, 0.16)" },
  { stroke: "rgba(0, 137, 123, 0.92)", fill: "rgba(0, 137, 123, 0.16)" },
];

export function getSegmentationTypeConfig(sampleType) {
  return SEGMENTATION_TYPE_CONFIG[sampleType] || SEGMENTATION_TYPE_CONFIG[SAMPLE_TYPES.SALIVA];
}

export function getLabelConfig(sampleType, label) {
  return getSegmentationTypeConfig(sampleType).labels.find(
    item => item.label === label
  ) || null;
}

export function getLabelPalette(sampleType) {
  return Object.fromEntries(
    getSegmentationTypeConfig(sampleType).labels.map(item => [
      item.label,
      {
        stroke: item.stroke,
        fill: item.fill,
      },
    ])
  );
}
