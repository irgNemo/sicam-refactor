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

export function registrationFieldErrors(error) {
  if (error?.response?.status !== 400) return {};
  const data = error.response.data;
  if (!data || typeof data !== 'object' || Array.isArray(data)) return {};
  const errors = {};
  for (const field of Object.keys(labels)) {
    const values = Array.isArray(data[field]) ? data[field] : [data[field]];
    const text = values.filter(value => typeof value === 'string').join(' ');
    if (text) errors[field] = text.slice(0, 250);
  }
  return errors;
}

export function registrationErrorMessage(error, fallback) {
  const messages = Object.entries(registrationFieldErrors(error))
    .map(([field, text]) => `${labels[field]}: ${text}`);
  return messages.join(' · ').slice(0, 700) || fallback;
}
