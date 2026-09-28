// Synthetic presentation fixture. No clinical images, results or calculated metrics.
export function saliva21Fixture() {
  const metrics = () => ({
    area_px2: 120.25, perimeter_px: 44.5, centroid_px: [10, 12.5],
    circularity: 0.812345, eccentricity: 0.654321,
    mean_gray_intensity: 0.5, std_gray_intensity: 0.125,
    texture: { contrast: 0, homogeneity: 1, energy: 1, correlation: null,
      entropy: 0, valid_angles: 4, valid_pairs: 123 },
  });
  const nucleus = id => ({ id, source_raw_id: 255, metrics: metrics(), association_status: 'ASSOCIATED' });
  return {
    version: '2.1', schema_version: '2.1', sample_type: 'SALIVA',
    source: { type: 'AUTOMATICO', resultado_segmentacion_id: 7 },
    methodology: { texture: { method: 'GLCM', gray_levels: 32, distance_px: 1,
      angles_deg: [0, 45, 90, 135], symmetric: true, normalized: true,
      aggregation: 'mean_over_valid_angles' } },
    summary: { total_membranes: 2, total_nuclei: 3, total_micronuclei: 1,
      genotoxicity_index: 0.5, cytotoxicity_index: 0.5,
      genotoxicity_status: 'VALID', cytotoxicity_status: 'VALID', association_quality: {} },
    cells: [
      { membrane_id: 1, display_label: 'Célula 1', source_raw_id: 255,
        metrics: metrics(), nuclear_class: 'MONONUCLEATED', association_status: 'ASSOCIATED',
        nuclei_count: 1, micronuclei_count: 1, nuclei: [nucleus(2)],
        micronuclei: [{ id: 3, source_raw_id: 255, display_label: '1.1', nucleus_id: 2,
          association_status: 'ASSOCIATED', metrics: { ...metrics(),
            distance_to_nucleus_px: null, area_fraction_to_nucleus: 0.04, intensity_fraction_to_nucleus: 0 } }] },
      { membrane_id: 4, display_label: 'Célula 4', source_raw_id: 255,
        metrics: metrics(), nuclear_class: 'BINUCLEATED', association_status: 'ASSOCIATED',
        nuclei_count: 2, micronuclei_count: 0, nuclei: [nucleus(5), nucleus(6)], micronuclei: [] },
    ],
    unassociated: { nuclei: [{ id: 9, association_status: 'UNASSOCIATED', metrics: null }], micronuclei: [] },
    ambiguous: { nuclei: [], micronuclei: [{ id: 10, association_status: 'AMBIGUOUS',
      candidate_membrane_ids: [1, 4], metrics: metrics() }] },
    warnings: [
      { code: 'TEXTURE_CORRELATION_UNDEFINED', object_id: 3, message: 'Intensidad constante.' },
      { code: 'ECCENTRICITY_NOT_COMPUTABLE', object_id: 9, message: 'Geometría inválida.' },
      { code: 'TEXTURE_INSUFFICIENT_PAIRS', object_id: 9, message: 'Sin pares vecinos.' },
      { code: 'SELF_INTERSECTING_POLYGON', object_id: 9, message: 'Autointersección.' },
      { code: 'FUTURE_WARNING', object_id: 10, message: 'Aviso futuro preservado.' },
    ],
  };
}

export function effective21Fixture() {
  return { fuente: 'AUTOMATICO', resultado: { objects: [
    { id: 1, label: 'membrana', geometry: { type: 'polygon', points: [[0, 0], [40, 0], [40, 40], [0, 40]] } },
    { id: 2, label: 'nucleo', geometry: { type: 'polygon', points: [[10, 10], [20, 10], [20, 20]] } },
    { id: 3, label: 'micronucleo', geometry: { type: 'polygon', points: [[25, 10], [30, 10], [30, 15]] } },
    { id: 4, label: 'membrana', geometry: { type: 'polygon', points: [[50, 0], [90, 0], [90, 40], [50, 40]] } },
  ] } };
}
