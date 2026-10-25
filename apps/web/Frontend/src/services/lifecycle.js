import api from './apiClient';

export const actionLabels = { HARD_DELETE: 'Eliminar permanentemente', ARCHIVE: 'Archivar', RESTORE: 'Restaurar', RETIRE: 'Retirar calibración' };
export const consequences = {
  HARD_DELETE: 'El registro se eliminará permanentemente. Sus archivos se eliminarán sólo si no están compartidos. Esta acción no se puede deshacer.',
  ARCHIVE: 'Se ocultará de las operaciones normales. Los archivos, resultados y relaciones históricas se conservarán.',
  RESTORE: 'Volverá al flujo operativo. Los descendientes archivados por separado permanecerán archivados.',
  RETIRE: 'La calibración quedará retirada para nuevos usos. Sus evidencias y resultados históricos se conservarán. No se puede reactivar desde esta interfaz.',
};
export const dependencyLabels = { Caso: 'Casos', AnalisisPred: 'Análisis', MuestraSaliva: 'Imágenes de saliva', MuestraSangre: 'Imágenes de sangre', ResultadoSegmentacion: 'Segmentaciones', RevisionSegmentacion: 'Revisiones', ResultadoCaracterizacion: 'Caracterizaciones', AcquisitionSeries: 'Series', Calibration: 'Calibraciones', CalibrationReference: 'Referencias', ImageJImportRecord: 'Importaciones ImageJ', SegmentationExecution: 'Ejecuciones', ResultadoAnalisis: 'Resultados', AnalisisMascara: 'Máscaras' };
export const canManageLifecycle = user => Boolean(user && !user.must_change_password && (user.is_superuser || ['ADMIN','OPERATOR'].includes(user.role)));
export const canSeeArchived = user => Boolean(user && !user.must_change_password && (user.is_superuser || user.role === 'ADMIN'));
export const archivedParams = (user, include) => canSeeArchived(user) && include ? { include_archived: 'true' } : {};
export const inspectLifecycle = (resource, id) => api.get(`/api/lifecycle/${resource}/${id}/`).then(r => r.data);
export function applyLifecycle(resource, id, action, reason, confirmed) {
  if (!actionLabels[action] || !reason?.trim() || !confirmed) throw new Error('Seleccione una acción, indique el motivo y confirme el impacto.');
  return api.post(`/api/lifecycle/${resource}/${id}/`, { action, reason: reason.trim(), confirm: true }).then(r => r.data);
}
export function lifecycleError(error) {
  const data = error.response?.data;
  const code = data?.code;
  const messages = {
    RESOURCE_BUSY: 'Hay una segmentación en curso. Espere a que termine antes de cambiar el estado.',
    PARENT_ARCHIVED: 'Restaure primero el objeto superior archivado.',
    PROFILE_UNAVAILABLE: 'La configuración de adquisición no está disponible. Revísela antes de restaurar.',
    CALIBRATION_RETIRED: 'La calibración está retirada. No se reactivará automáticamente.',
    INSTITUTION_MISMATCH: 'Las relaciones institucionales son incompatibles.',
    SCIENTIFIC_DEPENDENCIES_EXIST: 'Existen dependencias. La eliminación está bloqueada; consulte las acciones actualizadas.',
    ACTION_NOT_AVAILABLE: 'La acción ya no está disponible para el estado actual. Revise las dependencias.',
    RESOURCE_ARCHIVED: 'El recurso está archivado y no admite esta operación.',
    ADMIN_REQUIRED: 'Esta operación requiere ADMIN.',
    IMMUTABLE_HISTORY: 'El historial científico se conserva; no admite eliminación.',
    MEDIA_INSPECTION_FAILED: 'No se pudo verificar el archivo. No se eliminó el registro.',
  };
  if (messages[code]) return messages[code];
  if (error.response?.status === 403) return 'No tiene permiso para esta acción.';
  if (error.response?.status === 404) return 'El registro ya no está disponible.';
  return 'No se pudo completar la operación. Actualice la vista antes de reintentar.';
}
