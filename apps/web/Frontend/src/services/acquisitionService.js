import { auth } from './auth';
// The existing acquisition components now share the operational session.
export const operator = { get ready() { return Boolean(auth.user && !auth.user.must_change_password); } };
export function automaticPayload(profile, label, references, token = '') {
  const form = new FormData();
  form.append('acquisition_profile', profile);
  form.append('label', label);
  form.append('source_token', token);
  form.append('references', JSON.stringify(references.map(ref => ({
    pattern_type: ref.pattern_type, known_dimension_um: ref.known_dimension_um,
    ...(ref.pattern_type === 'GRADUATED_GRID' && ref.uniform ? { grid_reference: 'uniform_lattice' } : {}),
  }))));
  references.forEach((ref, index) => form.append(`reference_${index}`, ref.file));
  return form;
}
export const compatibilityText = status => ({
  COMPATIBLE: 'Compatible', COMPATIBLE_PROVISIONAL: 'Provisional compatible',
  RESOLUTION_MISMATCH: 'No disponible — resolución incompatible',
  NO_ACQUISITION_SERIES: 'No disponible — sin serie', NO_CALIBRATION: 'Sin calibración física',
  CALIBRATION_RETIRED: 'No disponible — calibración retirada', INVALID_IMAGE: 'No disponible — original inválido',
  IMAGE_MODE_MISMATCH: 'No disponible — modo de imagen incompatible',
  PATIENT_MISMATCH: 'No disponible — paciente incompatible', PROFILE_MISMATCH: 'No disponible — configuración incompatible',
  CHECK_PENDING: 'Comprobación pendiente', CHECK_FAILED: 'No se pudo consultar; la subida sí está confirmada',
}[status] || 'No disponible');
export function resolutionFeedback(dimensions, profile) {
  if (!profile) return 'La imagen no tendrá calibración física asociada.';
  if (!dimensions) return 'Dimensiones no disponibles en el navegador. Se comprobarán en el backend.';
  return dimensions.width === profile.image_width_px && dimensions.height === profile.image_height_px
    ? 'Compatible con la resolución de la configuración. Falta la comprobación del backend.'
    : 'Resolución incompatible con la configuración calibrada. Puede continuar sin medidas físicas.';
}
export function readDimensions(url) {
  return new Promise(resolve => {
    if (typeof Image === 'undefined') { resolve(null); return; }
    const image = new Image();
    let timer;
    const finish = result => { clearTimeout(timer); image.onload = image.onerror = null; resolve(result); };
    image.onload = () => finish({ width: image.naturalWidth, height: image.naturalHeight });
    image.onerror = () => finish(null);
    timer = setTimeout(() => finish(null), 10000);
    image.src = url;
  });
}
