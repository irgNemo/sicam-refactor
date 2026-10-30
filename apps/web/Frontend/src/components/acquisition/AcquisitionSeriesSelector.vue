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
      <AcquisitionSeriesCreateForm
        v-if="showForm"
        :patientId="patientId"
        :disabled="disabled"
        @created="onCreated"
        @cancel="showForm = false"
        @busy="onBusy"
      />
    </template>
    <p v-if="!selectedId">La imagen no tendrá calibración física asociada. Puede continuar con el procesamiento en píxeles.</p>
  </section>
</template>
<script>
import api from '../../services/apiClient';
import { operator } from '../../services/acquisitionService';
import { registrationErrorMessage } from '../../services/registrationErrors';
import OperatorAccess from './OperatorAccess.vue';
import AcquisitionSeriesCreateForm from './AcquisitionSeriesCreateForm.vue';
export default {
  components: { OperatorAccess, AcquisitionSeriesCreateForm },
  props: { patientId: [Number, String], disabled: Boolean },
  emits: ['change', 'dirty', 'busy'],
  data: () => ({ operator, series: [], profiles: [], calibrations: [], selectedId: '', showForm: false,
    loading: false, busy: false, error: '', generation: 0, disposed: false }),
  computed: {
    selection() { const series = this.series.find(item => item.id === Number(this.selectedId)) || null;
      return { series, profile: this.profiles.find(p => p.id === series?.acquisition_profile) || null,
        calibration: this.calibrations.find(c => c.id === series?.calibration) || null }; },
    calibrationStatus() { return { PROVISIONAL: 'Provisional', VALIDATED: 'Validada', RETIRED: 'Retirada' }[this.selection.calibration?.status]; },
    dirty() { return this.showForm; },
  },
  watch: {
    patientId: { immediate: true, handler() { this.showForm = false; this.load(); } },
    dirty(value) { this.$emit('dirty', value); },
    busy(value) { this.$emit('busy', value); },
  },
  beforeUnmount() { this.disposed = true; this.generation++; },
  methods: {
    accessChanged() { this.showForm = false; this.load(); },
    onBusy(value) { this.busy = value; },
    onCreated(newSeries) {
      this.series.push(newSeries);
      this.selectedId = newSeries.id;
      this.$emit('change', this.selection);
      this.showForm = false;
    },
    async load() {
      const generation = ++this.generation, patient = this.patientId;
      this.series = []; this.selectedId = ''; this.error = ''; this.loading = false;
      this.$emit('change', this.selection);
      if (!patient || !operator.ready) return;
      this.loading = true;
      try {
        const [seriesRes, profilesRes, calibrationsRes] = await Promise.all([
          api.get('/api/acquisition-series/', { params: { patient } }),
          api.get('/api/acquisition-profiles/'),
          api.get('/api/calibrations/'),
        ]);
        if (this.disposed || generation !== this.generation) return;
        this.profiles = profilesRes.data.filter(profile => profile.active !== false && !profile.archived_at);
        this.calibrations = calibrationsRes.data;
        this.series = seriesRes.data.filter(item => item.patient === Number(patient) && !item.archived_at
          && this.profiles.some(profile => profile.id === item.acquisition_profile)
          && (!item.calibration || this.calibrations.some(calibration => calibration.id === item.calibration && calibration.status !== 'RETIRED')));
        if (this.series.length === 1 && !this.disabled) this.choose(this.series[0].id);
      } catch (error) {
        if (!this.disposed && generation === this.generation) this.error = registrationErrorMessage(error, 'No se pudieron cargar las series. Puede continuar sin serie.');
      } finally {
        if (generation === this.generation) this.loading = false;
      }
    },
    choose(value) {
      if (this.disabled || this.busy) return;
      this.selectedId = this.series.some(item => item.id === Number(value)) ? Number(value) : '';
      this.$emit('change', this.selection);
    },
  },
};
</script>
<style scoped>
.series-section { background: #f7f9fc; border: 1px solid #dce3eb; border-radius: 8px; padding: 16px; margin: 16px 0; }
h4 { margin-top: 0; } p { font-size: 13px; line-height: 1.5; }
label { display: flex; flex-direction: column; gap: 6px; font-size: 14px; }input, select, button { padding: 9px; border: 1px solid #aab8c7; border-radius: 6px; }
button { background: white; cursor: pointer; margin-top: 8px; }.summary { padding: 8px 0; }
</style>
