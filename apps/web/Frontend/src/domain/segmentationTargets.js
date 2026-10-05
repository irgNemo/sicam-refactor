export const SALIVA_TARGETS = Object.freeze({ ALL: 'ALL', MEMBRANES: 'MEMBRANES', NUCLEI_AND_MICRONUCLEI: 'NUCLEI_AND_MICRONUCLEI' });
export const SALIVA_TARGET_OPTIONS = Object.freeze([
  { value: 'MEMBRANES', label: 'Membranas' },
  { value: 'NUCLEI_AND_MICRONUCLEI', label: 'Núcleos y micronúcleos' },
  { value: 'ALL', label: 'Todo' },
]);
export function replacementWarning(target, summary, hasDraft = false) {
  const counts = summary?.counts_by_label || {};
  const count = target === 'MEMBRANES' ? (counts.membrana || 0)
    : target === 'NUCLEI_AND_MICRONUCLEI' ? (counts.nucleo || 0) + (counts.micronucleo || 0)
      : summary?.total_objects || Object.values(counts).reduce((sum, n) => sum + n, 0);
  if (!count && !hasDraft) return '';
  const message = target === 'MEMBRANES'
    ? 'Esta operación reemplazará todas las membranas actuales por las generadas automáticamente. Los núcleos y micronúcleos no se modificarán.'
    : target === 'NUCLEI_AND_MICRONUCLEI'
      ? 'Esta operación reemplazará todos los núcleos y micronúcleos actuales. Las membranas no se modificarán.'
      : 'Esta operación generará una nueva base automática que reemplazará todas las categorías mostradas. Las anotaciones anteriores permanecerán en el historial.';
  return `${message}\nEl resultado automático puede ser vacío.${hasDraft ? '\nSe actualizará el BORRADOR actual y se conservará un checkpoint recuperable.' : ''}\n¿Deseas continuar?`;
}
export function segmentationLoadingText(target) {
  return target === 'MEMBRANES' ? 'Segmentando membranas...'
    : target === 'NUCLEI_AND_MICRONUCLEI' ? 'Segmentando núcleos y micronúcleos...' : 'Segmentando muestra...';
}
