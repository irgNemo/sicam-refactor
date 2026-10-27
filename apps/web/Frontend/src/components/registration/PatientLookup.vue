<template>
  <div class="patient-lookup">
    <label>Paciente
      <input :value="query" placeholder="Iniciales o identificador" :disabled="disabled" @input="search($event.target.value)" />
    </label>
    <div v-if="modelValue" class="chosen">
      <strong v-if="modelValue.initials">{{ modelValue.initials }}</strong><small>ID técnico: <CompactValue :value="modelValue.identificacion" /></small>
      <small>{{ patientIdentityMode(modelValue) }}</small>
      <button type="button" :disabled="disabled" @click="clear">Limpiar selección</button>
    </div>
    <p v-if="loading" role="status">Buscando pacientes…</p>
    <p v-if="error" role="alert">{{ error }}</p>
    <template v-if="query.trim() && !loading && !error">
      <p v-if="!results.length" role="status">No se encontraron pacientes.</p>
      <template v-else>
        <p>Seleccione un paciente ({{ countLabel(count, 'coincidencia', 'coincidencias') }}).</p>
        <ul><li v-for="patient in results" :key="patient.id">
          <button type="button" :disabled="disabled" :title="patient.identificacion" :aria-label="[patient.initials, patientIdentityMode(patient), patient.identificacion, patient.external_id_namespace, patient.external_patient_id].filter(Boolean).join(' · ')" @click="select(patient)">
            <strong v-if="patient.initials">{{ patient.initials }}</strong><strong v-else><CompactValue :focusable="false" :value="patient.identificacion" :peers="results.map(p=>p.identificacion)" /></strong>
            <small>{{ patientIdentityMode(patient) }}<span v-if="patient.initials"> · ID técnico: <CompactValue :focusable="false" :value="patient.identificacion" :peers="results.map(p=>p.identificacion)" /></span></small>
            <small v-if="patient.external_patient_id"><CompactValue :focusable="false" :value="patient.external_id_namespace" /> / <CompactValue :focusable="false" :value="patient.external_patient_id" /></small>
          </button>
        </li></ul>
        <div class="pages">
          <button type="button" :disabled="disabled || page === 1" @click="load(page-1)">Anterior</button>
          <span>Página {{ page }}</span>
          <button type="button" :disabled="disabled || page * 20 >= count" @click="load(page+1)">Siguiente</button>
        </div>
      </template>
    </template>
  </div>
</template>
<script>
import CompactValue from './CompactValue.vue';
import api from '../../services/apiClient';
import { countLabel } from '../../domain/compactPresentation';
import { patientIdentityMode } from '../../domain/patientPresentation';
export default {
  components: { CompactValue },
  props: { modelValue: { type:Object, default:null }, disabled:Boolean, includeArchived:Boolean },
  emits: ['update:modelValue'],
  data: () => ({ query:'', results:[], count:0, page:1, loading:false, error:'', generation:0, disposed:false }),
  watch: { includeArchived() { this.clear(); } },
  beforeUnmount() { this.disposed=true; this.generation++; },
  methods: {
    patientIdentityMode, countLabel,
    search(value) {
      if(this.disabled)return;
      this.query=value;
      if(this.modelValue)this.$emit('update:modelValue',null);
      return this.load(1);
    },
    clear() {
      this.generation++;this.query='';this.results=[];this.count=0;this.error='';this.loading=false;
      this.$emit('update:modelValue',null);
    },
    select(patient) {
      if(this.disabled)return;
      this.generation++;this.query='';this.results=[];this.loading=false;
      this.$emit('update:modelValue',patient);
    },
    async load(page) {
      const generation=++this.generation;this.page=page;this.results=[];this.error='';
      if(!this.query.trim()){this.loading=false;this.count=0;return;}
      this.loading=true;
      try {
        const {data}=await api.get('/api/pacientes/lookup/',{params:{q:this.query,page,include_archived:this.includeArchived?'true':'false'}});
        if(!this.disposed && generation===this.generation){this.results=data.results;this.count=data.count;}
      } catch(e) { if(!this.disposed && generation===this.generation)this.error='No se pudieron buscar pacientes.'; }
      finally { if(generation===this.generation)this.loading=false; }
    },
  },
};
</script>
<style scoped>
.patient-lookup{min-width:0;width:240px;max-width:100%}label,small{display:block}input{box-sizing:border-box;width:100%;margin-top:6px}input,button{font:inherit;padding:9px;border:1px solid #bcccdc;border-radius:8px;background:white}button{cursor:pointer;text-align:left}button:disabled{opacity:.55;cursor:not-allowed}input:focus-visible,button:focus-visible{outline:3px solid #90caf9}ul{list-style:none;padding:0;max-height:260px;overflow:auto}li button{width:100%;overflow-wrap:anywhere;margin-bottom:5px}small{color:#486581;margin-top:4px}.chosen{padding:8px;background:#f0f6fa;margin-top:8px}.chosen button{margin-top:6px}.pages{display:flex;align-items:center;justify-content:space-between;gap:8px}p{font-size:13px}
</style>
