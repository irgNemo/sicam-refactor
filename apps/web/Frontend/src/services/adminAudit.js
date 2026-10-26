import api from './apiClient';
export const auditLabels = { HARD_DELETE: 'Eliminar permanentemente', ARCHIVE: 'Archivar', RESTORE: 'Restaurar', RETIRE: 'Retirar calibración' };
export const archiveLabels = { pacientes: 'Pacientes', casos: 'Casos', analisis: 'Análisis', muestras: 'Imágenes SALIVA', 'muestras-sangre': 'Imágenes SANGRE', 'acquisition-series': 'Series', 'acquisition-profiles': 'Configuraciones', calibrations: 'Calibraciones retiradas' };
export function adminParams(filters, user) {
  return Object.fromEntries(Object.entries(filters).filter(([key, value]) => value !== '' && value != null && (key !== 'institution' || user?.is_superuser)));
}
export const fetchAudit = (kind, filters, user) => api.get(`/api/admin-audit/${kind}/`, { params: adminParams(filters, user) }).then(r => r.data);
export const fetchEvent = id => api.get(`/api/admin-audit/events/${id}/`).then(r => r.data);
export const auditError = error => error.response?.status === 403 ? 'No tiene acceso administrativo.' : error.response?.status === 404 ? 'El registro no está disponible.' : 'No se pudo consultar. Revise los filtros y vuelva a intentar.';
export const displayDate = value => value ? new Date(value).toLocaleString() : '—';
