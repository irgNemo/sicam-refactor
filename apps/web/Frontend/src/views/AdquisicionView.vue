<template>
  <main class="acquisition-content">
    <div class="acquisition-shell">
      <header><h2>Adquisición</h2><p>Configuraciones del microscopio y calibraciones espaciales.</p></header>
      <OperatorAccess :disabled="busy" @change="accessChanged" />
      <p v-if="error" role="alert" class="error">{{ error }}</p>
      <p v-if="notice" role="status">{{ notice }}</p>
      <div v-if="operator.ready">
        <nav class="tabs" aria-label="Adquisición">
          <button v-for="item in ['Configuraciones', 'Calibraciones']" :key="item" :aria-pressed="tab === item" @click="tab = item">{{ item }}</button>
        </nav>
        <p v-if="loading" role="status">Cargando…</p>
        <section v-if="tab === 'Configuraciones'" class="card">
          <div class="heading"><h3>Configuraciones</h3><button :disabled="busy" @click="editProfile(null)">Nueva configuración</button></div>
          <p v-if="!profiles.length && !loading">No hay configuraciones registradas.</p>
          <ul class="cards"><li v-for="profile in profiles" :key="profile.id">
            <strong>{{ profile.name }}</strong><p>{{ profile.image_width_px }} × {{ profile.image_height_px }} px · {{ profile.objective_magnification || 'Objetivo no indicado' }}{{ profile.objective_magnification ? '×' : '' }}</p>
            <p>{{ [profile.microscope_manufacturer, profile.microscope_model, profile.camera_model, profile.adapter_model].filter(Boolean).join(' · ') }}</p>
            <button :disabled="busy" @click="editProfile(profile)">Ver / editar metadata</button>
          </li></ul>
          <form v-if="profileForm" @submit.prevent="saveProfile">
            <h3>{{ profileForm.id ? 'Detalle de configuración' : 'Nueva configuración' }}</h3>
            <p v-if="profileForm.physical_fields_locked">Puede editar nombre y notas. Para otro montaje o resolución cree una configuración.</p>
            <fieldset :disabled="busy"><div class="field-grid">
              <label v-for="field in profileFields" :key="field.key">{{ field.label }}{{ field.required ? ' *' : '' }}
                <input v-model="profileForm[field.key]" :type="field.type || 'text'" :step="field.step || '1'" :min="field.type === 'number' ? (field.step || 1) : undefined"
                  :required="field.required" :disabled="Boolean(profileForm.physical_fields_locked && field.key !== 'name')" />
              </label>
              <label class="wide">Notas<textarea v-model="profileForm.notes" /></label>
            </div><div class="actions"><button type="submit">Guardar configuración</button><button type="button" @click="editProfile(null, true)">Cerrar</button></div></fieldset>
          </form>
        </section>
        <section v-else class="card">
          <div class="heading"><h3>Calibraciones</h3><button :disabled="busy || loading" @click="load">Actualizar lista</button></div>
          <p class="pending">La calibración provisional puede utilizarse operativamente, pero su validación experimental está pendiente (18S-A.2).</p>
          <p v-if="!calibrations.length && !loading">No hay calibraciones registradas.</p>
          <ul class="cards"><li v-for="calibration in calibrations" :key="calibration.id">
            <strong>{{ calibration.label }}</strong> <span class="badge">{{ statusLabel(calibration.status) }}</span>
            <p>{{ profileName(calibration.acquisition_profile) }} · {{ formatDate(calibration.created_at) }}</p>
            <p>sx {{ calibration.scale_x_um_per_px }} µm/px · sy {{ calibration.scale_y_um_per_px }} µm/px</p>
            <button :disabled="busy" @click="showReferences(calibration)">Ver referencias</button>
            <div v-if="selectedCalibration === calibration.id"><ul><li v-for="ref in shownReferences" :key="ref.id">{{ ref.source_filename }} · {{ ref.measurement_status }} · {{ ref.known_dimension_um }} µm</li></ul></div>
          </li></ul>
          <form @submit.prevent="measure" @input="review = null; created = false">
            <h3>Nueva calibración automática</h3>
            <fieldset :disabled="busy"><div class="field-grid">
              <label>Configuración *<select v-model="automaticProfile" required @change="review = null"><option value="">Seleccione</option><option v-for="profile in profiles" :key="profile.id" :value="profile.id">{{ profile.name }}</option></select></label>
              <label>Nombre de calibración *<input v-model="automaticLabel" required maxlength="150" /></label>
            </div>
            <div v-for="(reference, index) in references" :key="reference.key" class="reference">
              <h4>Referencia {{ index + 1 }}</h4><div class="field-grid">
                <label>Imagen *<input type="file" accept="image/*" required @change="reference.file = $event.target.files[0] || null; review = null" /></label>
                <label>Patrón *<select v-model="reference.pattern_type" @change="review = null"><option value="CIRCLE">Círculo</option><option value="GRADUATED_GRID">Retícula graduada</option></select></label>
                <label>{{ reference.pattern_type === 'CIRCLE' ? 'Diámetro conocido (µm)' : 'División conocida (µm)' }} *<input v-model="reference.known_dimension_um" type="number" min="0.000000000000001" step="any" required /></label>
                <label v-if="reference.pattern_type === 'GRADUATED_GRID'"><span><input v-model="reference.uniform" type="checkbox" /> El patrón es una retícula uniforme conocida</span><small>Déjelo desmarcado si existe ambigüedad entre divisiones.</small></label>
              </div><button type="button" :disabled="references.length === 1" @click="references.splice(index, 1); review = null">Quitar referencia</button>
            </div>
            <p>Indique la dimensión física del patrón; no se deduce del nombre. Máximo 8 referencias, 30 MiB por archivo.</p>
            <div class="actions"><button type="button" :disabled="references.length >= 8" @click="addReference">Añadir referencia</button><button type="submit">{{ busy ? 'Midiendo…' : 'Medir referencias' }}</button></div>
            </fieldset>
          </form>
          <section v-if="review" class="review" aria-live="polite">
            <h3>{{ created ? 'Calibración provisional registrada' : 'Resultado de la medición' }}</h3>
            <p v-if="review.usable">sx {{ review.scale_x_um_per_px }} µm/px · sy {{ review.scale_y_um_per_px }} µm/px</p>
            <p v-if="review.usable">Anisotropía: {{ review.anisotropy_percent?.toFixed(4) }} %</p>
            <p v-else>No existe una escala utilizable. Revise las referencias; no se creó una calibración.</p>
            <ul><li v-for="(result, index) in review.results" :key="index">{{ result.source_file }}: {{ result.measurement_status }}{{ result.measurement_status === 'MEASURED' ? ' — utilizada' : ' — excluida del consenso' }}</li></ul>
            <ul v-if="review.warnings?.length"><li v-for="warning in review.warnings" :key="warning">{{ warning }}</li></ul>
            <p class="pending">Provisional. Validación experimental pendiente.</p>
            <button v-if="review.usable && !created" :disabled="busy" @click="createCalibration">{{ busy ? 'Guardando…' : 'Crear calibración provisional' }}</button>
          </section>
        </section>
      </div>
    </div>
  </main>
</template>
<script>
import api from '../services/apiClient';
import { operator, automaticPayload } from '../services/acquisitionService';
import { registrationErrorMessage } from '../services/registrationErrors';
import OperatorAccess from '../components/acquisition/OperatorAccess.vue';
const fields = [
  ['name', 'Nombre', true], ['microscope_manufacturer', 'Fabricante del microscopio'], ['microscope_model', 'Modelo del microscopio'],
  ['camera_manufacturer', 'Fabricante de cámara'], ['camera_model', 'Modelo de cámara'], ['adapter_model', 'Adaptador'],
  ['objective_magnification', 'Objetivo (×)', false, 'number', '0.001'], ['image_width_px', 'Ancho (px)', true, 'number'], ['image_height_px', 'Alto (px)', true, 'number'],
  ['image_mode', 'Modo de imagen (p. ej. RGB)'], ['binning_x', 'Binning X', false, 'number'], ['binning_y', 'Binning Y', false, 'number'],
].map(([key, label, required = false, type, step]) => ({ key, label, required, type, step }));
export default {
  components: { OperatorAccess },
  data: () => ({ operator, tab: 'Configuraciones', profiles: [], calibrations: [], loading: false, busy: false,
    error: '', notice: '', profileFields: fields, profileForm: null, profileBaseline: '', automaticProfile: '', automaticLabel: '',
    references: [{ key: 0, file: null, pattern_type: 'CIRCLE', known_dimension_um: '', uniform: false }], nextKey: 1,
    review: null, created: false, selectedCalibration: null, shownReferences: [], disposed: false, generation: 0 }),
  computed: {
    hasUnsavedWork() { return this.busy || Boolean(this.profileForm && JSON.stringify(this.profileForm) !== this.profileBaseline)
      || (!this.created && Boolean(this.automaticLabel || this.references.some(ref => ref.file || ref.known_dimension_um))); },
  },
  mounted() { if (operator.ready) this.load(); window.addEventListener('beforeunload', this.beforeUnload); },
  beforeUnmount() { this.disposed = true; this.generation++; window.removeEventListener('beforeunload', this.beforeUnload); },
  methods: {
    statusLabel: status => ({ PROVISIONAL: 'Provisional', VALIDATED: 'Validada', RETIRED: 'Retirada' }[status] || status),
    formatDate: value => new Date(value).toLocaleDateString(),
    profileName(id) { return this.profiles.find(profile => profile.id === id)?.name || `#${id}`; },
    accessChanged(ready) { this.generation++; if (ready) this.load(); else { this.profiles = []; this.calibrations = []; } },
    async load() {
      const generation = ++this.generation; this.loading = true; this.error = '';
      try { const [profiles, calibrations] = await Promise.all([api.get('/api/acquisition-profiles/'), api.get('/api/calibrations/')]);
        if (!this.disposed && generation === this.generation) { this.profiles = profiles.data; this.calibrations = calibrations.data; }
      } catch (error) { if (!this.disposed && generation === this.generation) this.error = registrationErrorMessage(error, 'No se pudo cargar adquisición.'); }
      finally { if (generation === this.generation) this.loading = false; }
    },
    editProfile(profile, close = false) {
      if (this.profileForm && JSON.stringify(this.profileForm) !== this.profileBaseline && !window.confirm('¿Descartar cambios de configuración?')) return;
      this.profileForm = close ? null : profile ? { ...profile } : { ...Object.fromEntries(fields.map(field => [field.key, ''])), notes: '' };
      this.profileBaseline = JSON.stringify(this.profileForm);
    },
    async saveProfile() {
      if (this.busy) return; this.busy = true; this.error = '';
      try {
        const payload = this.profileForm.physical_fields_locked
          ? { name: this.profileForm.name, notes: this.profileForm.notes }
          : { ...Object.fromEntries(fields.map(field => [field.key, this.profileForm[field.key]])), notes: this.profileForm.notes };
        for (const key of ['objective_magnification', 'binning_x', 'binning_y']) if (payload[key] === '') payload[key] = null;
        if (this.profileForm.id) await api.patch(`/api/acquisition-profiles/${this.profileForm.id}/`, payload);
        else await api.post('/api/acquisition-profiles/', payload);
        this.profileForm = null; this.profileBaseline = ''; this.notice = 'Configuración guardada.'; await this.load();
      } catch (error) { this.error = registrationErrorMessage(error, 'No se pudo guardar la configuración.'); }
      finally { this.busy = false; }
    },
    addReference() { this.references.push({ key: this.nextKey++, file: null, pattern_type: 'CIRCLE', known_dimension_um: '', uniform: false }); this.review = null; this.created = false; },
    async showReferences(calibration) {
      this.selectedCalibration = calibration.id; this.shownReferences = []; this.error = '';
      try { const response = await api.get('/api/calibration-references/');
        if (!this.disposed && this.selectedCalibration === calibration.id) this.shownReferences = response.data.filter(ref => ref.calibration === calibration.id);
      } catch (error) { this.error = registrationErrorMessage(error, 'No se pudieron cargar las referencias.'); }
    },
    async measure() {
      if (this.busy) return; this.busy = true; this.error = ''; this.review = null; this.created = false;
      try { const response = await api.post('/api/calibrations/automatic-preview/', automaticPayload(this.automaticProfile, this.automaticLabel, this.references)); this.review = response.data.review; }
      catch (error) { this.error = registrationErrorMessage(error, 'No se pudo completar la medición. No se creó calibración.'); }
      finally { this.busy = false; }
    },
    async createCalibration() {
      if (this.busy || !this.review?.usable || this.created) return; this.busy = true; this.error = '';
      try { const response = await api.post('/api/calibrations/automatic/', automaticPayload(this.automaticProfile, this.automaticLabel, this.references, this.review.source_token));
        this.review = response.data.review; this.created = true; this.notice = 'Calibración provisional guardada.'; await this.load();
      } catch (error) { this.error = registrationErrorMessage(error, 'No se pudo confirmar la creación. Consulte la lista antes de reintentar para evitar duplicados.'); }
      finally { this.busy = false; }
    },
    confirmLeave() { if (this.busy) { this.error = 'Espere a que termine la operación.'; return false; } return !this.hasUnsavedWork || window.confirm('Hay trabajo sin guardar en Adquisición. ¿Desea continuar?'); },
    beforeUnload(event) { if (this.hasUnsavedWork) { event.preventDefault(); event.returnValue = ''; } },
  },
};
</script>
<style scoped>
.acquisition-content { flex: 1; min-width: 0; padding: 24px; }
.acquisition-shell { max-width: 1080px; margin: auto; }
header { margin-bottom: 24px; } h2, h3 { margin-top: 0; } p { line-height: 1.5; }
.tabs, .actions, .heading { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; margin: 16px 0; }
.heading { justify-content: space-between; }.heading h3 { margin: 0; }
.card { background: white; border: 1px solid #dce3eb; border-radius: 12px; padding: 24px; }
.cards { list-style: none; padding: 0; display: grid; gap: 12px; }.cards > li, .reference, .review { border: 1px solid #dce3eb; padding: 16px; border-radius: 8px; margin-bottom: 12px; }
.cards p { font-size: 13px; margin: 8px 0; overflow-wrap: anywhere; }
.field-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }.wide { grid-column: 1 / -1; }
label { display: flex; flex-direction: column; gap: 6px; font-size: 14px; } input, select, textarea { padding: 10px; border: 1px solid #aebdcd; border-radius: 6px; max-width: 100%; min-width: 0; }
fieldset { border: 0; padding: 0; margin: 0; min-width: 0; } form { margin-top: 28px; } .reference { margin-top: 16px; }
button { padding: 9px 14px; border: 1px solid #62748c; background: #fff; color: #263b56; border-radius: 7px; cursor: pointer; }button[aria-pressed=true], button[type=submit] { background: #315da3; color: white; }button:disabled { opacity: .55; cursor: default; }
.badge { display: inline-block; background: #fff0c2; padding: 4px 8px; border-radius: 6px; font-size: 12px; }.pending { padding: 12px; background: #fff8df; border-radius: 8px; }.error { color: #a51f2c; overflow-wrap: anywhere; }
@media(max-width: 650px) { .field-grid { grid-template-columns: 1fr; }.acquisition-content, .card { padding: 16px; } }
</style>
