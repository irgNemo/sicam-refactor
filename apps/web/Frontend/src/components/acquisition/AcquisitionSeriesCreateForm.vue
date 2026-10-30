<template>
  <div class="series-form">
    <p>La configuración y calibración se definen para la serie, no para cada imagen.</p>
    <OperatorAccess :disabled="disabled || busy" />
    <template v-if="operator.ready">
      <p v-if="loadError" role="alert">{{ loadError }}</p>
      <label>Nombre *<input v-model="form.label" maxlength="150" :disabled="disabled || busy" /></label>
      <label>Configuración *<select v-model="form.acquisition_profile" :disabled="disabled || busy" @change="form.calibration = ''">
        <option value="">Seleccione</option>
        <option v-for="profile in profiles" :key="profile.id" :value="profile.id">{{ profile.name }}</option>
      </select></label>
      <label>Calibración<select v-model="form.calibration" :disabled="disabled || busy">
        <option value="">Sin calibración física</option>
        <option v-for="calibration in eligibleCalibrations" :key="calibration.id" :value="calibration.id">{{ calibration.label }} · {{ calibration.status === 'PROVISIONAL' ? 'Provisional' : 'Validada' }}</option>
      </select></label>
      <label>Fecha (opcional)<input v-model="form.acquisition_date" type="date" :disabled="disabled || busy" /></label>
      <p v-if="error" role="alert">{{ error }}</p>
      <button type="button" :disabled="disabled || busy || !form.label.trim() || !form.acquisition_profile" @click="create">{{ busy ? 'Guardando…' : 'Guardar serie' }}</button>
      <button type="button" :disabled="disabled || busy" @click="cancel">Cancelar</button>
    </template>
    <p v-else>Inicie sesión para crear series.</p>
  </div>
</template>
<script>
import api from '../../services/apiClient';
import { operator } from '../../services/acquisitionService';
import { registrationErrorMessage } from '../../services/registrationErrors';
import OperatorAccess from './OperatorAccess.vue';
const blank = () => ({ label: '', acquisition_profile: '', calibration: '', acquisition_date: '' });
export default {
  components: { OperatorAccess },
  props: { patientId: { type: [Number, String], default: null }, disabled: Boolean },
  emits: ['created', 'cancel', 'busy'],
  data: () => ({ operator, profiles: [], calibrations: [], form: blank(), busy: false, error: '', loadError: '', disposed: false }),
  computed: {
    eligibleCalibrations() {
      return this.calibrations.filter(c => c.acquisition_profile === Number(this.form.acquisition_profile) && c.status !== 'RETIRED');
    },
  },
  watch: {
    patientId() { this.reset(); this.load(); },
  },
  mounted() { this.load(); },
  beforeUnmount() { this.disposed = true; },
  methods: {
    reset() {
      this.form = blank();
      this.error = '';
    },
    async load() {
      this.loadError = '';
      try {
        const [profiles, calibrations] = await Promise.all([
          api.get('/api/acquisition-profiles/'),
          api.get('/api/calibrations/'),
        ]);
        if (this.disposed) return;
        this.profiles = profiles.data.filter(p => p.active !== false && !p.archived_at);
        this.calibrations = calibrations.data;
      } catch (err) {
        if (!this.disposed) this.loadError = registrationErrorMessage(err, 'No se pudieron cargar las opciones.');
      }
    },
    cancel() {
      this.reset();
      this.$emit('cancel');
    },
    async create() {
      if (this.disabled || this.busy || !this.patientId || !this.form.label.trim() || !this.form.acquisition_profile) return;
      this.busy = true;
      this.$emit('busy', true);
      this.error = '';
      try {
        const response = await api.post('/api/acquisition-series/', {
          ...this.form,
          patient: this.patientId,
          calibration: this.form.calibration || null,
          acquisition_date: this.form.acquisition_date || null,
        });
        if (!this.disposed) {
          const created = response.data;
          this.reset();
          this.$emit('created', created);
        }
      } catch (err) {
        if (!this.disposed) this.error = registrationErrorMessage(err, 'No se pudo crear la serie.');
      } finally {
        this.busy = false;
        this.$emit('busy', false);
      }
    },
  },
};
</script>
<style scoped>
.series-form { display: grid; gap: 12px; margin-top: 16px; }
label { display: flex; flex-direction: column; gap: 6px; font-size: 14px; }
input, select, button { padding: 9px; border: 1px solid #aab8c7; border-radius: 6px; }
button { background: white; cursor: pointer; margin-top: 8px; }
</style>
