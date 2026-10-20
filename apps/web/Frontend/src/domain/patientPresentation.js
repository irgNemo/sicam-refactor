export function patientDisplayName(patient) {
  if (!patient) return '';
  if (patient.identity_mode === 'PSEUDONYMIZED') return patient.initials || '';
  return patient.display_name || [patient.nombre, patient.apellido].filter(Boolean).join(' ');
}

export function patientInitials(patient) {
  if (!patient) return '';
  if (patient.identity_mode === 'PSEUDONYMIZED') return patient.initials || '';
  return ((patient.nombre || '').charAt(0) + (patient.apellido || '').charAt(0)).toUpperCase();
}

// Registration needs the external authority to distinguish equal initials,
// while other screens retain their existing compact display name.
export function patientRegistrationLabel(patient) {
  if (!patient) return '';
  if (patient.identity_mode === 'PSEUDONYMIZED') {
    const authority = [patient.external_id_namespace, patient.external_patient_id].filter(Boolean).join(' / ');
    return [patient.initials || 'Paciente pseudonimizado', authority].filter(Boolean).join(' · ');
  }
  return [patientDisplayName(patient) || 'Paciente', patient.identificacion].filter(Boolean).join(' · ');
}
