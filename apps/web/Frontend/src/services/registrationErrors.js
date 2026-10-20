// Only render known DRF validation fields as text; never display server tracebacks.
const labels = {
  nombre: 'Nombre', apellido: 'Apellido', identificacion: 'Identificación',
  fecha_nacimiento: 'Fecha de nacimiento', email: 'Email', telefono: 'Teléfono',
  paciente: 'Paciente', titulo: 'Título', descripcion: 'Descripción',
  id_paciente_fk: 'Paciente', id_caso_fk: 'Caso', analisis: 'Análisis',
  imagen: 'Imagen', identity_mode: 'Identidad', initials: 'Iniciales',
  external_patient_id: 'ID externo', external_id_namespace: 'Namespace',
  non_field_errors: 'Validación',
};

export function registrationErrorMessage(error, fallback) {
  if (error?.response?.status !== 400) return fallback;
  const data = error.response.data;
  if (!data || typeof data !== 'object' || Array.isArray(data)) return fallback;
  const messages = [];
  for (const [field, label] of Object.entries(labels)) {
    const values = Array.isArray(data[field]) ? data[field] : [data[field]];
    const text = values.filter(value => typeof value === 'string').join(' ');
    if (text) messages.push(`${label}: ${text.slice(0, 250)}`);
  }
  return messages.join(' · ').slice(0, 700) || fallback;
}
