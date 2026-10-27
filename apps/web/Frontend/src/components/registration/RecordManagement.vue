<template>
  <section class="management" aria-label="Gestionar registros">
    <nav class="tabs" aria-label="Tipos de registros">
      <button v-for="tab in tabs" :key="tab.key" type="button" :class="{active: resource === tab.key}" :aria-pressed="resource === tab.key" :disabled="busy" @click="changeTab(tab.key)">{{ tab.label }}</button>
    </nav>
    <section class="card">
      <header><h3>{{ title }}</h3><p>Consulte registros de su institución y sus acciones disponibles.</p></header>
      <form class="filters" @submit.prevent="filter">
        <label>{{ resource === 'patients' ? 'Buscar paciente' : 'Buscar' }}<input v-model="search" :placeholder="resource === 'patients' ? 'Iniciales o identificador' : resource === 'images' ? 'Nombre de archivo o ID' : 'ID de caso'" :disabled="busy" /></label>
        <PatientLookup v-if="resource !== 'patients'" :model-value="selectedPatient" :disabled="busy" :include-archived="includeArchived" @update:model-value="selectPatient" />
        <template v-if="resource === 'images'">
          <label>Caso<select v-model="caseId" :disabled="busy || !patient || casesLoading" @change="filter"><option value="">Todos los casos</option><option v-if="caseId && !caseOptions.some(c=>c.id===Number(caseId))" :value="caseId">Caso #{{ caseId }}</option><option v-for="item in caseOptions" :key="item.id" :value="item.id">{{ item.label }}</option></select></label>
          <span v-if="casesLoading" role="status">Cargando casos…</span>
          <button v-if="caseOptions.length < caseCount" type="button" :disabled="busy || casesLoading" @click="loadCases(casePage+1)">Más casos</button>
          <p v-if="caseError" role="alert">{{ caseError }} <button type="button" :disabled="busy" @click="loadCases(1)">Reintentar</button></p>
          <label>Serie<select v-model="seriesFilter" :disabled="busy"><option value="">Cualquiera</option><option value="none">Sin serie</option><option value="specific">Serie específica</option></select></label>
          <label v-if="seriesFilter === 'specific'">ID de serie<input v-model="seriesIdFilter" type="number" min="1" :disabled="busy" /></label>
          <label>Tipo<select v-model="type" :disabled="busy"><option value="">Todos</option><option>SALIVA</option><option>SANGRE</option></select></label>
          <label>Estado físico (página)<select v-model="physical" :disabled="busy" @change="clearSelection"><option value="">Todos</option><option v-for="code in physicalStates" :key="code" :value="code">{{ compatibilityText(code) }}</option></select></label>
        </template>
        <label v-if="canSeeArchived(auth.user)" class="check"><input v-model="includeArchived" type="checkbox" :disabled="busy" /> Incluir archivados</label>
        <button type="submit" :disabled="busy || loading">Buscar</button>
      </form>
      <p v-if="error" role="alert" class="error">{{ error }}</p>
      <p v-if="message" role="status">{{ message }}</p>
      <p v-if="loading" role="status">Cargando registros…</p>
      <template v-else>
        <div v-if="resource === 'images' && can('register')" class="selection">
          <strong>{{ countLabel(selected.length, 'imagen seleccionada', 'imágenes seleccionadas') }}.</strong>
          <button type="button" :disabled="busy || !visibleRows.length" @click="selectPage">Seleccionar página visible</button>
          <button type="button" :disabled="busy || !selected.length" @click="clearSelection">Limpiar selección</button>
          <button type="button" :disabled="busy || !selected.length || mixedPatients" @click="openAssignment">Asignar a serie</button>
          <p v-if="mixedPatients" role="alert">Las imágenes seleccionadas pertenecen a pacientes diferentes. Selecciona imágenes de un solo paciente para asignarlas a una serie.</p>
        </div>
        <p v-if="!visibleRows.length" class="empty">{{ emptyText }}</p>
        <div v-else class="table-wrap"><table>
          <colgroup><col v-if="resource === 'images' && can('register')" class="select-column" /><col /><col v-if="resource !== 'patients'" /><col /><col /><col class="actions-column" /></colgroup>
          <thead><tr><th v-if="resource === 'images' && can('register')" aria-label="Seleccionar" title="Seleccionar">Sel.</th><th>Registro</th><th v-if="resource !== 'patients'">Contexto</th><th>Información</th><th>Estado</th><th>Acciones</th></tr></thead>
          <tbody><tr v-for="row in visibleRows" :key="key(row)">
            <td v-if="resource === 'images' && can('register')"><input type="checkbox" :aria-label="`Seleccionar ${row.filename}`" :checked="selected.includes(key(row))" :disabled="busy || row.archived" @change="toggle(row)" /></td>
            <td>
              <template v-if="resource === 'patients'"><strong v-if="row.initials">{{ row.initials }}</strong><strong v-else><CompactValue :value="row.identificacion" :peers="identityPeers" /></strong><small v-if="row.initials">ID técnico: <CompactValue :value="row.identificacion" :peers="identityPeers" /></small></template>
              <template v-else-if="resource === 'cases'"><strong>{{ row.label }}</strong></template>
              <template v-else><strong><CompactValue :value="row.filename" format="filename" /></strong><small>ID {{ row.id }} · {{ row.type }}</small></template>
            </td>
            <td v-if="resource !== 'patients'">
              <template v-if="row.patient_identity"><strong v-if="row.patient_identity.initials">{{ row.patient_identity.initials }}</strong><small>ID <CompactValue :value="row.patient_identity.identificacion" :peers="identityPeers" /></small></template><template v-else>{{ row.patient }}</template>
              <small v-if="row.analysis_id">Caso #{{ row.case_id }} · Análisis #{{ row.analysis_id }}</small>
            </td>
            <td v-if="resource === 'patients'">{{ patientIdentityMode(row) }}<small>{{ countLabel(row.case_count, 'caso', 'casos') }} · {{ countLabel(row.image_count, 'imagen', 'imágenes') }}</small></td>
            <td v-else-if="resource === 'cases'">{{ countLabel(row.analysis_count, 'análisis', 'análisis') }} · {{ countLabel(row.image_count, 'imagen', 'imágenes') }}</td>
            <td v-else><span v-if="row.dimensions">{{ row.dimensions.width }} × {{ row.dimensions.height }} · {{ row.mode }}</span><span v-else>Resolución no disponible</span><small v-if="row.series">{{ row.series.profile?.name }} · {{ row.series.label }}</small><small v-else>Sin serie</small><small>{{ row.characterization_count ? countLabel(row.characterization_count, 'caracterización', 'caracterizaciones') : 'Sin caracterización' }}</small></td>
            <td><span class="badge" :class="{warning:row.archived}">{{ row.archived ? 'ARCHIVADA' : 'ACTIVA' }}</span><span v-if="row.compatibility" class="badge" :class="{warning: !row.compatibility.compatible_for_physical_units}">{{ compatibilityText(row.compatibility.status) }}</span></td>
            <td class="actions">
              <template v-if="resource === 'patients'"><button type="button" :disabled="busy" @click="related(row, 'cases')">Ver casos</button><button type="button" :disabled="busy" @click="related(row, 'images')">Ver imágenes</button></template>
              <button v-if="resource === 'cases'" type="button" :disabled="busy" @click="related(row, 'images')">Ver imágenes</button>
              <LifecycleActions :resource="row.resource || (resource === 'patients' ? 'pacientes' : 'casos')" :id="row.id" :label="row.label || row.filename" :disabled="busy" @busy="busy = $event" @changed="changed" />
            </td>
          </tr></tbody>
        </table></div>
        <footer class="pagination"><button :disabled="busy || page <= 1" @click="goPage(page-1)">Anterior</button><span>Página {{ page }} · {{ countLabel(count, 'registro', 'registros') }}</span><button :disabled="busy || page * 20 >= count" @click="goPage(page+1)">Siguiente</button></footer>
      </template>
      <section v-if="assignmentOpen" class="assignment" aria-label="Asignar a serie">
        <h4>Asignar a serie</h4>
        <p>La serie debe corresponder a la adquisición real. La coincidencia de resolución no demuestra su origen.</p>
        <p v-if="!busy && !series.length">No hay series válidas disponibles para este paciente.</p>
        <label>Serie<select v-model="target" :disabled="busy" @change="invalidatePreview"><option value="">Seleccione explícitamente</option><option v-for="s in series" :key="s.id" :value="s.id">{{ s.label }} · {{ s.profile.name }} · {{ s.profile.width }} × {{ s.profile.height }} {{ s.profile.mode }} · {{ s.calibration?.status || 'Sin calibración' }}</option></select></label>
        <p v-if="targetSeries">Objetivo: {{ targetSeries.profile.objective || 'No indicado' }} · Calibración: {{ targetSeries.calibration?.label || 'Sin calibración' }}</p>
        <button :disabled="busy || !target" @click="previewAssignment">Comprobar compatibilidad</button>
        <div v-if="preview">
          <p>{{ countLabel(preview.results.length, 'imagen', 'imágenes') }} · {{ countLabel(preview.compatible_count, 'compatible', 'compatibles') }} · {{ preview.results.length-preview.compatible_count }} sin unidades físicas disponibles</p>
          <p v-if="preview.series.calibration?.status === 'PROVISIONAL'" class="warning">Calibración PROVISIONAL: las medidas físicas no representan metrología validada definitiva.</p>
          <ul><li v-for="row in preview.results" :key="key(row)">{{ selectedRows.find(s => key(s) === key(row))?.filename || row.id }} · {{ compatibilityText(row.compatibility.status) }}<strong v-if="!row.compatibility.compatible_for_physical_units"> — Los valores físicos permanecerán no disponibles.</strong><span v-if="row.already_assigned"> · Ya asignada, sin cambios</span></li></ul>
          <label class="check"><input v-model="confirmed" type="checkbox" :disabled="busy" /> Confirmo la serie y la asociación de las imágenes seleccionadas.</label>
          <button :disabled="busy || !confirmed" @click="assign">{{ busy ? 'Procesando…' : 'Confirmar asociación' }}</button>
        </div>
        <button :disabled="busy" @click="closeAssignment">Cancelar</button>
      </section>
    </section>
  </section>
</template>
<script>
import api from '../../services/apiClient';
import { auth, can } from '../../services/auth';
import { canSeeArchived, lifecycleError } from '../../services/lifecycle';
import { compatibilityText } from '../../services/acquisitionService';
import { registrationErrorMessage } from '../../services/registrationErrors';
import { countLabel } from '../../domain/compactPresentation';
import CompactValue from './CompactValue.vue';
import PatientLookup from './PatientLookup.vue';
import { patientIdentityContext, patientIdentityMode } from '../../domain/patientPresentation';
import LifecycleActions from '../lifecycle/LifecycleActions.vue';
export default {
  components: { LifecycleActions, PatientLookup, CompactValue }, emits: ['busy','dirty','changed'],
  data: () => ({ auth, tabs:[{key:'patients',label:'Pacientes'},{key:'cases',label:'Casos'},{key:'images',label:'Imágenes'}],
    resource:'patients', search:'', patient:'', selectedPatient:null, caseId:'', caseOptions:[], caseCount:0, casePage:1, casesLoading:false, caseError:'', caseGeneration:0, seriesFilter:'', seriesIdFilter:'', type:'', physical:'', includeArchived:false,
    rows:[], count:0, page:1, loading:false, busy:false, error:'', message:'', generation:0, disposed:false,
    selected:[], assignmentOpen:false, series:[], target:'', preview:null, confirmed:false }),
  computed: {
    identityPeers() { return this.rows.map(r=>r.patient_identity?.identificacion || r.identificacion); },
    title() { return this.tabs.find(t=>t.key===this.resource)?.label; },
    visibleRows() { return this.rows.filter(r=>!this.physical || r.compatibility?.status===this.physical); },
    physicalStates() { return [...new Set(this.rows.map(r=>r.compatibility?.status).filter(Boolean))]; },
    selectedRows() { return this.rows.filter(r=>this.selected.includes(this.key(r))); },
    mixedPatients() { return new Set(this.selectedRows.map(r=>r.patient_id)).size>1; },
    targetSeries() { return this.series.find(s=>s.id===Number(this.target)); },
    emptyText() { return this.resource==='patients'?'No se encontraron pacientes.':this.resource==='cases'?'No se encontraron casos.':this.seriesFilter==='none'?'No hay imágenes sin serie.':'No se encontraron imágenes.'; },
  },
  watch: { busy(value) { this.$emit('busy',value); }, selected: { deep:true, handler(value) { this.$emit('dirty',value.length>0); } } },
  mounted() { this.load(); },
  beforeUnmount() { this.disposed=true;this.generation++;this.caseGeneration++;this.$emit('dirty',false); },
  methods: {
    can, canSeeArchived, compatibilityText, patientIdentityContext, patientIdentityMode, countLabel,
    assignmentError(error) {
      const messages = {
        SERIES_ALREADY_ASSIGNED: 'Esta imagen ya pertenece a otra serie.',
        MIXED_PATIENTS: 'Las imágenes seleccionadas pertenecen a pacientes diferentes. Selecciona imágenes de un solo paciente para asignarlas a una serie.',
        PATIENT_MISMATCH: 'La serie no pertenece al paciente de las imágenes.',
        PREVIEW_CHANGED: 'Los datos cambiaron. Compruebe nuevamente la compatibilidad y confirme.',
        PREVIEW_EXPIRED: 'La comprobación caducó. Genere una nueva vista previa.',
      };
      return messages[error.response?.data?.code] || lifecycleError(error);
    },
    key: row=>`${row.type || 'record'}:${row.id}`,
    invalidatePreview() { this.preview=null;this.confirmed=false; },
    closeAssignment() { this.assignmentOpen=false;this.target='';this.invalidatePreview(); },
    clearSelection() { this.selected=[];this.closeAssignment(); },
    toggle(row) { if(this.busy || row.archived)return;this.closeAssignment();const key=this.key(row);this.selected=this.selected.includes(key)?this.selected.filter(k=>k!==key):[...this.selected,key]; },
    selectPage() { if(this.busy)return;this.closeAssignment();this.selected=this.visibleRows.filter(r=>!r.archived).map(this.key); },
    changeTab(tab) { if(this.busy)return;this.resource=tab;this.search='';this.physical='';this.caseId='';this.filter(); },
    related(row,tab) {
      if(this.busy)return;
      const patient=this.resource==='patients'?row:row.patient_identity;
      const caseId=this.resource==='cases'?row.id:'';
      this.resource=tab;this.search='';this.physical='';
      this.selectPatient(patient,caseId);
    },
    selectPatient(patient,caseId='') {
      if(this.busy)return;
      this.selectedPatient=patient;this.patient=patient?.id || '';this.caseId=caseId;
      this.caseGeneration++;this.caseOptions=[];this.caseCount=0;this.casePage=1;this.caseError='';this.casesLoading=false;
      if(this.patient)this.loadCases(1);
      this.filter();
    },
    async loadCases(page=1) {
      if(!this.patient)return;
      const generation=++this.caseGeneration;this.casesLoading=true;this.caseError='';
      try {
        const {data}=await api.get('/api/record-management/cases/',{params:{patient:this.patient,page,include_archived:this.includeArchived?'true':'false'}});
        if(!this.disposed && generation===this.caseGeneration){this.caseOptions=page===1?data.results:[...this.caseOptions,...data.results];this.caseCount=data.count;this.casePage=page;}
      } catch(e){if(!this.disposed && generation===this.caseGeneration)this.caseError='No se pudieron cargar los casos.';}
      finally{if(generation===this.caseGeneration)this.casesLoading=false;}
    },
    filter() { if(this.busy)return;this.page=1;this.load(); },
    goPage(page) { if(this.busy)return;this.page=page;this.load(); },
    async load() {
      const generation=++this.generation;this.loading=true;this.error='';this.clearSelection();this.rows=[];
      try { const {data}=await api.get(`/api/record-management/${this.resource}/`,{params:{page:this.page,search:this.search,patient:this.patient,case:this.caseId,
        series:this.seriesFilter==='specific'?this.seriesIdFilter:this.seriesFilter,type:this.type,include_archived:this.includeArchived?'true':'false'}});
        if(!this.disposed && generation===this.generation){this.rows=data.results;this.count=data.count;}
      } catch(e){if(generation===this.generation)this.error=registrationErrorMessage(e,'No se pudieron consultar los registros.');}
      finally{if(generation===this.generation)this.loading=false;}
    },
    async changed() { await this.load();this.$emit('changed'); },
    async openAssignment() {
      if(this.busy || !this.selectedRows.length || this.mixedPatients || !can('register'))return;
      this.busy=true;this.error='';this.series=[];this.target='';this.invalidatePreview();this.assignmentOpen=true;
      try { const {data}=await api.get('/api/record-management/series/',{params:{patient:this.selectedRows[0].patient_id}});if(!this.disposed)this.series=data; }
      catch(e){this.error=registrationErrorMessage(e,'No se pudieron cargar las series.');}finally{this.busy=false;}
    },
    payload() { return {series_id:Number(this.target),samples:this.selectedRows.map(r=>({type:r.type,id:r.id}))}; },
    async previewAssignment() {
      if(this.busy || !this.target || !this.selected.length)return;
      this.busy=true;this.error='';this.invalidatePreview();
      try { const {data}=await api.post('/api/record-management/series/preview/',this.payload());if(!this.disposed)this.preview=data; }
      catch(e){this.error=this.assignmentError(e);}finally{this.busy=false;}
    },
    async assign() {
      if(this.busy || !this.confirmed || !this.preview)return;
      this.busy=true;this.error='';
      try { const {data}=await api.post('/api/record-management/series/assign/',{...this.payload(),confirm:true,preview_token:this.preview.preview_token});
        this.message=`Serie asignada. ${countLabel(data.compatible_count, 'imagen compatible', 'imágenes compatibles')} para unidades físicas${data.series.calibration?.status==='PROVISIONAL'?' basada en calibración provisional':''}. En SALIVA, una segmentación completa permite generar caracterización con unidades físicas. SANGRE conserva sus conteos. No se ha calculado ninguna caracterización. Abra Caracterización desde el menú habitual.`;
        await this.load();this.$emit('changed');
      } catch(e){this.invalidatePreview();this.error=this.assignmentError(e);}finally{this.busy=false;}
    },
  },
};
</script>
<style scoped>
.tabs {display:flex;gap:8px;flex-wrap:wrap;margin-bottom:16px}.tabs button{padding:10px 24px;font-weight:600;border-width:2px}.tabs .active{background:#e3f2fd;border-color:#1e88e5;color:#1565c0}.card{background:#fff;border:1px solid #d9e2ec;border-radius:12px;overflow:hidden}header{padding:20px 24px;border-bottom:1px solid #e5eaf0}h3,h4{margin:0 0 8px}p{line-height:1.5}header p{margin:0;color:#627d98}.filters,.selection,.pagination{display:flex;gap:12px;flex-wrap:wrap;align-items:end;padding:16px 24px}label{display:flex;flex-direction:column;gap:6px;font-size:14px}.check{flex-direction:row;align-items:center}input,select,button{font:inherit;padding:9px;border:1px solid #bcccdc;border-radius:8px}button{background:white;color:#334e68;cursor:pointer}button:disabled{opacity:.55;cursor:not-allowed}button:focus-visible,input:focus-visible,select:focus-visible{outline:3px solid #90caf9;outline-offset:2px}.table-wrap{overflow-x:auto}table{width:100%;border-collapse:collapse;text-align:left;font-size:14px}th{background:#f4f7fb;color:#486581}td,th{padding:12px 16px;border-bottom:1px solid #e5eaf0}small{display:block;color:#627d98;margin-top:5px}.badge{display:block;width:fit-content;border-radius:6px;padding:4px 7px;background:#e8f3ef;margin:3px 0;font-size:12px}.warning{background:#fff3cd;color:#795600}.actions{min-width:155px}.actions button{margin:3px}.empty,.error,[role=status]{padding:12px 24px}.error{color:#a32323}.assignment{margin:20px;padding:20px;border:1px solid #90caf9;border-radius:10px;background:#f5f9ff}.assignment button,.assignment label{margin-top:12px}.selection p{width:100%;margin:0;color:#a32323}.pagination{justify-content:space-between;align-items:center}@media(max-width:640px){.filters label{width:100%}.tabs button{flex:1;padding:10px}.assignment{margin:12px}}
/* Fixed layout gives actions space independently of long content. Small screens may scroll. */
.management{min-width:0;max-width:100%}.table-wrap{width:100%}table{table-layout:fixed;min-width:760px}.select-column{width:52px}.actions-column{width:140px}td,th{padding:10px;vertical-align:top;overflow-wrap:anywhere}.actions{min-width:0}.actions button{max-width:100%;margin:3px 0}.actions :deep(.lifecycle-actions > button){white-space:nowrap}.badge{max-width:100%;box-sizing:border-box}.filters label{min-width:0}.filters input,.filters select{max-width:100%;box-sizing:border-box}.filters select{width:220px}.check input{width:auto}.filters .check{width:auto}.assignment{overflow-wrap:anywhere}
</style>
