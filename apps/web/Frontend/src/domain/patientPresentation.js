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
