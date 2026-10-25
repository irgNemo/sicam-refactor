<template>
  <section class="series-section" aria-label="Serie de adquisición">
    <h4>Serie de adquisición</h4>
    <OperatorAccess :disabled="disabled || busy" @change="accessChanged" />
    <p v-if="!patientId">Seleccione un paciente para consultar sus series.</p>
    <template v-else-if="operator.ready">
      <p v-if="loading" role="status">Cargando series…</p>
      <p v-if="error" role="alert">{{ error }}</p>
      <p v-if="!loading && !error && !series.length">No hay una serie de adquisición registrada para este paciente.</p>
      <label>Serie<select :value="selectedId" :disabled="disabled || loading || busy" @change="choose($event.target.value)">
        <option value="">Continuar sin serie</option><option v-for="item in series" :key="item.id" :value="item.id">{{ item.label }}</option>
      </select></label>
      <p v-if="series.length > 1 && !selectedId">Hay varias series; elija una o continúe sin serie.</p>
      <div v-if="selection.series" class="summary">
        <p>Configuración: {{ selection.profile?.name }}</p>
        <p v-if="selection.calibration">Calibración: {{ selection.calibration.label }} · <strong>{{ calibrationStatus }}</strong></p>
        <p v-else>Sin calibración física</p>
        <p v-if="selection.calibration?.status === 'PROVISIONAL'">Las medidas físicas utilizarán una calibración provisional.</p>
        <p v-if="selection.calibration?.status === 'RETIRED'">Calibración retirada: nuevas medidas físicas no disponibles.</p>
      </div>
      <button type="button" :disabled="disabled || loading || busy" @click="showForm = !showForm">{{ showForm ? 'Ocultar formulario' : 'Crear serie' }}</button>
      <div v-if="showForm" class="series-form">
        <p>La configuración y calibración se definen para la serie, no para cada imagen.</p>
        <label>Nombre *<input v-model="form.label" maxlength="150" :disabled="disabled || busy" /></label>
        <label>Configuración *<select v-model="form.acquisition_profile" :disabled="disabled || busy" @change="form.calibration = ''"><option value="">Seleccione</option><option v-for="profile in profiles" :key="profile.id" :value="profile.id">{{ profile.name }}</option></select></label>
        <label>Calibración<select v-model="form.calibration" :disabled="disabled || busy"><option value="">Sin calibración física</option><option v-for="calibration in eligibleCalibrations" :key="calibration.id" :value="calibration.id">{{ calibration.label }} · {{ calibration.status === 'PROVISIONAL' ? 'Provisional' : 'Validada' }}</option></select></label>
        <label>Fecha (opcional)<input v-model="form.acquisition_date" type="date" :disabled="disabled || busy" /></label>
        <button type="button" :disabled="disabled || busy || !form.label.trim() || !form.acquisition_profile" @click="create">{{ busy ? 'Guardando…' : 'Guardar serie' }}</button>
        <button type="button" :disabled="disabled || busy" @click="resetForm">Cancelar</button>
      </div>
    </template>
    <p v-if="!selectedId">La imagen no tendrá calibración física asociada. Puede continuar con el procesamiento en píxeles.</p>
  </section>
</template>
<script>
import api from '../../services/apiClient';
import { operator } from '../../services/acquisitionService';
import { registrationErrorMessage } from '../../services/registrationErrors';
import OperatorAccess from './OperatorAccess.vue';
const blank = () => ({ label: '', acquisition_profile: '', calibration: '', acquisition_date: '' });
export default {
  components: { OperatorAccess }, props: { patientId: [Number, String], disabled: Boolean }, emits: ['change', 'dirty', 'busy'],
  data: () => ({ operator, series: [], profiles: [], calibrations: [], selectedId: '', form: blank(), showForm: false,
    loading: false, busy: false, error: '', generation: 0, disposed: false }),
  computed: {
    eligibleCalibrations() { return this.calibrations.filter(c => c.acquisition_profile === Number(this.form.acquisition_profile) && c.status !== 'RETIRED'); },
    selection() { const series = this.series.find(item => item.id === Number(this.selectedId)) || null;
      return { series, profile: this.profiles.find(p => p.id === series?.acquisition_profile) || null,
        calibration: this.calibrations.find(c => c.id === series?.calibration) || null }; },
    calibrationStatus() { return { PROVISIONAL: 'Provisional', VALIDATED: 'Validada', RETIRED: 'Retirada' }[this.selection.calibration?.status]; },
    dirty() { return Object.values(this.form).some(Boolean); },
  },
  watch: {
    patientId: { immediate: true, handler() { this.resetForm(); this.load(); } },
    dirty(value) { this.$emit('dirty', value); }, busy(value) { this.$emit('busy', value); },
  },
  beforeUnmount() { this.disposed = true; this.generation++; },
  methods: {
    resetForm() { this.form = blank(); this.showForm = false; this.$emit('dirty', false); },
    accessChanged() { this.resetForm(); this.load(); },
    async load() {
      const generation = ++this.generation, patient = this.patientId;
      this.series = []; this.selectedId = ''; this.error = ''; this.loading = false; this.$emit('change', this.selection);
      if (!patient || !operator.ready) return;
      this.loading = true;
      try { const [series, profiles, calibrations] = await Promise.all([
        api.get('/api/acquisition-series/', { params: { patient } }), api.get('/api/acquisition-profiles/'), api.get('/api/calibrations/'),
      ]);
        if (this.disposed || generation !== this.generation) return;
        this.profiles = profiles.data.filter(profile => profile.active !== false && !profile.archived_at);
        this.calibrations = calibrations.data;
        this.series = series.data.filter(item => item.patient === Number(patient) && !item.archived_at
          && this.profiles.some(profile => profile.id === item.acquisition_profile)
          && (!item.calibration || this.calibrations.some(calibration => calibration.id === item.calibration && calibration.status !== 'RETIRED')));
        if (this.series.length === 1 && !this.disabled) this.choose(this.series[0].id);
      } catch (error) { if (!this.disposed && generation === this.generation) this.error = registrationErrorMessage(error, 'No se pudieron cargar las series. Puede continuar sin serie.'); }
      finally { if (generation === this.generation) this.loading = false; }
    },
    choose(value) { if (this.disabled || this.busy) return; this.selectedId = this.series.some(item => item.id === Number(value)) ? Number(value) : ''; this.$emit('change', this.selection); },
    async create() {
      if (this.disabled || this.busy || !this.patientId || !this.form.label.trim() || !this.form.acquisition_profile) return;
      const generation = this.generation, patient = this.patientId; this.busy = true; this.error = '';
      try { const response = await api.post('/api/acquisition-series/', { ...this.form, patient,
        calibration: this.form.calibration || null, acquisition_date: this.form.acquisition_date || null });
        if (!this.disposed && generation === this.generation) {
          this.series.push(response.data); this.selectedId = response.data.id; this.$emit('change', this.selection); this.resetForm();
        }
      } catch (error) { if (!this.disposed && generation === this.generation) this.error = registrationErrorMessage(error, 'No se pudo confirmar la creación. Consulte las series antes de reintentar.'); }
      finally { this.busy = false; }
    },
  },
};
</script>
<style scoped>
.series-section { background: #f7f9fc; border: 1px solid #dce3eb; border-radius: 8px; padding: 16px; margin: 16px 0; }
h4 { margin-top: 0; } p { font-size: 13px; line-height: 1.5; }.series-form { display: grid; gap: 12px; margin-top: 16px; }
label { display: flex; flex-direction: column; gap: 6px; font-size: 14px; }input, select, button { padding: 9px; border: 1px solid #aab8c7; border-radius: 6px; }
button { background: white; cursor: pointer; margin-top: 8px; }.summary { padding: 8px 0; }
</style>
