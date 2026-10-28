<template>
 <main class="datasets">
  <header><h2>Conjuntos de datos</h2><p>Características nucleares SALIVA · Una fila por relación núcleo–MN; sin MN, una fila con campos MN vacíos.</p></header>
  <p class="notice">{{ options.split_warning || splitWarning }}</p>
  <p v-if="error" role="alert">{{ error }}</p><p v-if="busy" role="status">Procesando…</p>
  <section class="card">
   <div class="bar"><h3>Datasets guardados</h3><button v-if="can('register')" :disabled="busy" @click="newDraft">Nuevo conjunto</button></div>
   <p v-if="!list.results.length">No hay conjuntos de datos.</p>
   <div class="table-wrap" v-else><table><thead><tr><th>Nombre / Tipo</th><th>Estado</th><th>Pacientes / Filas</th><th>Versión / Unidades</th><th>Fecha / Autor</th><th>Acciones</th></tr></thead><tbody>
    <tr v-for="item in list.results" :key="item.id"><td>{{ item.name }}<small>SALIVA · Características nucleares</small></td><td>{{ item.status === 'GENERATED' ? 'Generado' : 'Borrador' }}</td><td>Seleccionados: {{ item.selected_patient_count ?? item.patient_count }}<small>Incluidos: {{ item.included_patient_count ?? 'No registrado' }} · Sin datos elegibles: {{ item.zero_row_patient_count ?? 'No registrado' }}</small>Filas: {{ item.row_count }}</td><td>{{ item.characterization_version }} · {{ unitLabel(item.units_mode) }}</td><td>{{ formatDate(item.generated_at || item.created_at) }}<small>Usuario #{{ item.created_by_id }}</small></td><td><button :disabled="busy" @click="open(item.id)">Abrir</button></td></tr>
   </tbody></table></div>
   <div class="bar"><button :disabled="busy || page===1" @click="loadList(page-1)">Anterior</button><span>Página {{ page }} · {{ list.count }} conjuntos</span><button :disabled="busy || !list.next" @click="loadList(page+1)">Siguiente</button></div>
  </section>
  <template v-if="current">
   <section v-if="current.status==='DRAFT'" class="card">
    <h3>1. Configuración</h3><fieldset :disabled="busy || !can('register')">
     <label v-if="auth.user?.is_superuser && !current.id">Institución<select v-model="form.institution" @change="form.patients=[]"><option value="">Seleccione</option><option v-for="institution in options.institutions" :key="institution.id" :value="institution.id">{{ institution.code }}</option></select></label>
     <label>Nombre<input v-model="form.name" maxlength="160" required /></label><label>Descripción<textarea v-model="form.description" maxlength="4000" /></label>
     <div class="bar"><label>Characterization<select v-model="form.characterization_version" @change="versionChanged"><option v-for="v in options.versions" :key="v">{{ v }}</option></select></label><label>Unidades<select v-model="form.units_mode"><option value="PIXELS">Píxeles</option><option value="PHYSICAL" :disabled="form.characterization_version==='2.1'">Físicas</option><option value="BOTH" :disabled="form.characterization_version==='2.1'">Ambas</option></select></label></div>
     <label>Segmentación<select v-model="form.validated_only"><option :value="true">Solo VALIDADA</option><option :value="false">Permitir efectiva automática</option></select></label><p>Se excluyen registros archivados. BORRADOR nunca es efectivo. Se usan resultados guardados; no se recalcula Characterization.</p>
    </fieldset>
    <h3>2. Pacientes y clases</h3>
    <fieldset :disabled="busy || !can('register')"><h4>Clases del conjunto</h4>
     <ul><li v-for="label in form.classes" :key="label">{{ label }}</li></ul>
     <div class="bar"><label>Nueva clase<input v-model="newClass" maxlength="100" @keydown.enter.prevent="addClass" /></label><button @click="addClass">+ Agregar clase</button></div>
    </fieldset>
    <PatientLookup v-if="can('register')" :model-value="null" :disabled="busy" @update:model-value="addPatient" />
    <p v-if="!form.patients.length">Seleccione pacientes y asigne una clase explícita a cada uno. La clase pertenece sólo a este dataset; no se infiere un diagnóstico.</p>
    <div v-for="p in form.patients" :key="p.patient_id" class="member"><div><strong>{{ p.identity.initials }}</strong><small>ID <CompactValue :value="p.identity.identificacion" :peers="form.patients.map(p=>p.identity.identificacion)" /></small></div><label>Clase<select v-model="p.class_label" :disabled="busy || !can('register')"><option value="">Seleccione clase</option><option v-for="label in form.classes" :key="label" :value="label">{{ label }}</option></select></label><button v-if="can('register')" :disabled="busy" @click="removePatient(p.patient_id)">Quitar</button></div>
    <h3>3. Datos y variables</h3>
    <fieldset :disabled="busy || !can('register')"><div v-for="group in groups" :key="group" class="feature-group"><h4>{{ group }}</h4><label v-for="feature in options.features.filter(f=>f.group===group)" :key="feature.key" class="check"><input type="checkbox" v-model="form.features" :value="feature.key" /> {{ featureLabel(feature.key, form.units_mode) }}<small>{{ feature.entity === 'nucleus' ? 'Núcleo' : feature.entity === 'mn' ? 'MN' : 'Relación' }}</small></label></div></fieldset>
    <details><summary>Variables del Excel no disponibles</summary><ul><li v-for="name in options.unavailable" :key="name">{{ name }}</li></ul><p>La distancia exportable es entre centroides, no entre bordes. La textura GLCM conserva su contrato en píxeles.</p></details>
    <div class="bar"><button v-if="can('register')" :disabled="busy" @click="save">Guardar borrador</button><button :disabled="busy || (!can('register') && dirty)" @click="previewDataset">4. Vista previa</button><small v-if="dirty">Cambios sin guardar</small></div>
   </section>
   <section v-else class="card"><h3>{{ current.name }} · Snapshot generado</h3><p>Generado: {{ formatDate(current.generated_at) }}</p><p>Configuración inmutable. Para otro experimento cree un nuevo borrador.</p><p>Characterization {{ current.characterization_version }} · {{ unitLabel(current.units_mode) }}</p><p>Variables: {{ current.config.features.map(key=>featureLabel(key, current.units_mode)).join(', ') }}</p><div class="bar"><button v-for="kind in ['csv','xlsx','manifest']" :key="kind" :disabled="busy" @click="download(kind)">Descargar {{ kind==='xlsx'?'Excel':kind==='csv'?'CSV':'manifiesto' }}</button></div><details><summary>Manifiesto</summary><pre>{{ JSON.stringify(current.manifest,null,2) }}</pre></details></section>
   <section v-if="shownSummary" class="card" aria-label="Vista previa del dataset">
    <h3>{{ current.status==='GENERATED'?'Resumen congelado':'4. Vista previa' }}</h3>
    <p>Pacientes seleccionados: {{ shownSummary.selected_patient_count ?? shownSummary.patients }} · Pacientes incluidos: {{ shownSummary.included_patient_count ?? 'No registrado' }} · Pacientes sin datos elegibles: {{ shownSummary.zero_row_patient_count ?? 'No registrado' }} · {{ shownSummary.samples }} imágenes elegibles · {{ shownSummary.excluded_samples }} excluidas · {{ shownSummary.rows }} filas · {{ shownSummary.nuclei }} núcleos · {{ shownSummary.mn_associations }} asociaciones MN</p>
    <p>{{ current.characterization_version }} · {{ unitLabel(current.units_mode) }} · {{ current.config.validated_only?'Solo VALIDADA':'Permitir efectiva automática' }}</p>
    <p v-if="shownSummary.zero_row_patient_count" class="notice" role="alert">{{ shownSummary.zero_row_patient_count }} paciente(s) seleccionado(s) no aporta(n) datos elegibles al conjunto. Se conservarán en el snapshot para auditoría. Confirme esta advertencia antes de generar.</p>
    <p v-if="shownSummary.provisional_count" class="notice">{{ shownSummary.provisional_count }} resultados basados en calibración PROVISIONAL. <strong v-if="current.units_mode!=='PIXELS'">Las unidades físicas incluyen resultados basados en calibración provisional.</strong></p>
    <ul><li v-for="(counts,label) in shownSummary.class_counts" :key="label">{{ label }}: {{ counts.selected_patients ?? counts.patients }} pacientes seleccionados · {{ counts.included_patients ?? 'No registrado' }} pacientes incluidos · {{ counts.samples }} imágenes · {{ counts.row_count ?? counts.rows }} filas</li></ul>
    <ul><li v-for="(count,reason) in shownSummary.exclusion_counts" :key="reason">{{ reason }}: {{ count }}</li></ul>
    <p v-if="shownSummary.excluded_rows">Relaciones excluidas por valores físicos nulos: {{ shownSummary.excluded_rows }}</p>
    <details><summary>Exclusiones detalladas</summary><ul><li v-for="(e,i) in shownExclusions" :key="i">{{ e.sample }} · {{ e.reason }} · {{ e.description }}</li></ul></details>
    <details v-if="preview?.patients"><summary>Elegibilidad por paciente</summary><ul><li v-for="p in preview.patients" :key="p.ID_paciente">{{ p.ID_paciente }} · {{ p.Clase }} · {{ p.samples }} imágenes · {{ p.rows }} filas</li></ul></details>
    <details v-if="preview?.columns"><summary>Columnas de exportación</summary><p>{{ preview.columns.join(', ') }}</p></details>
    <template v-if="current.status==='DRAFT' && can('register')"><h3>5. Generar</h3><label class="check"><input type="checkbox" v-model="confirmed" :disabled="busy || dirty" /> Confirmo clases, fuentes, exclusiones y advertencias. El snapshot generado será inmutable.</label><button :disabled="busy || dirty || !confirmed || !shownSummary.rows" @click="generate">Generar snapshot</button></template>
   </section>
  </template>
 </main>
</template>
<script>
import api from '../services/apiClient';
import {auth,can,authErrorMessage} from '../services/auth';
import PatientLookup from '../components/registration/PatientLookup.vue';
import CompactValue from '../components/registration/CompactValue.vue';
const fresh=()=>({name:'',description:'',characterization_version:'2.2',units_mode:'PIXELS',validated_only:true,classes:[],features:['nucleus_area','nucleus_perimeter','nucleus_eccentricity','area_ratio'],patients:[],institution:''});
export default {
 components:{PatientLookup,CompactValue},
 data:()=>({auth,options:{features:[],versions:['2.1','2.2'],institutions:[],unavailable:[]},list:{results:[],count:0,next:null},page:1,current:null,form:fresh(),saved:'',busy:false,error:'',newClass:'',preview:null,confirmed:false,splitWarning:'Las particiones de entrenamiento/validación/prueba deben realizarse por paciente, no por fila, núcleo ni imagen.'}),
 computed:{dirty(){return this.current?.status==='DRAFT' && JSON.stringify(this.form)!==this.saved;},groups(){return [...new Set(this.options.features.map(f=>f.group))];},shownSummary(){return this.current?.status==='GENERATED'?this.current.summary:!this.dirty?this.preview?.summary:null;},shownExclusions(){return this.current?.status==='GENERATED'?this.current.exclusions:this.preview?.exclusions || []; }},
 watch:{form:{deep:true,handler(){this.confirmed=false;}}},
 async mounted(){window.addEventListener('beforeunload',this.beforeUnload);try{this.options=(await api.get('/api/datasets/options/')).data;await this.loadList();}catch(e){this.error=authErrorMessage(e);}},
 beforeUnmount(){window.removeEventListener('beforeunload',this.beforeUnload);},
 methods:{can,
  unitLabel(value){return {PIXELS:'Píxeles',PHYSICAL:'Físicas',BOTH:'Ambas'}[value] || value;},
  formatDate(value){if(!value || Number.isNaN(new Date(value).getTime()))return 'sin fecha';return new Date(value).toLocaleString('es-MX',{dateStyle:'short',timeStyle:'short'});},
  featureLabel(key, units){
   const entity=key.startsWith('nucleus_')?'núcleo':key.startsWith('mn_')?'micronúcleo':'';
   const metric=key.replace(/^(nucleus|mn)_/,'');
   const labels={area:'Área',perimeter:'Perímetro',eccentricity:'Excentricidad',circularity:'Circularidad',intensity:'Intensidad media',std:'Desviación estándar de intensidad',contrast:'GLCM contraste',homogeneity:'GLCM homogeneidad',energy:'GLCM energía',correlation:'GLCM correlación',area_ratio:'Proporción de área MN/núcleo',centroid_distance:'Distancia entre centroides MN–núcleo'};
   let label=(labels[metric] || key)+(entity?' '+entity:'');
   if(['area','perimeter','centroid_distance'].includes(metric)){
    const area=metric==='area';const px=area?'px²':'px',physical=area?'µm²':'µm';
    label+=' ('+(units==='BOTH'?px+' / '+physical:units==='PHYSICAL'?physical:px)+')';
   }
   return label;
  },
  addClass(){
   if(this.busy||!can('register'))return;
   const label=this.newClass.trim();
   if(!label){this.error='El nombre de clase no puede estar vacío.';return;}
   if(this.form.classes.some(value=>value.toLowerCase()===label.toLowerCase())){this.error='Ya existe una clase equivalente con ese nombre.';return;}
   this.form.classes.push(label);this.newClass='';this.error='';
  },
  beforeUnload(e){if(this.dirty||this.busy){e.preventDefault();e.returnValue='';}},
  confirmLeave(){return !this.busy && (!this.dirty || window.confirm('Hay cambios sin guardar. ¿Salir?'));},
  async loadList(page=1){this.busy=true;try{this.list=(await api.get('/api/datasets/',{params:{page}})).data;this.page=page;}catch(e){this.error=authErrorMessage(e);}finally{this.busy=false;}},
  newDraft(){if(!can('register')||!this.confirmLeave())return;this.current={status:'DRAFT'};this.form=fresh();this.newClass='';this.saved=JSON.stringify(this.form);this.preview=null;this.confirmed=false;this.error='';},
  accept(data){
   this.current=data;
   const classes=[...(data.config.classes || [])];
   if(!data.config.classes){
    for(const p of data.patients){
     const label=p.class_label.trim();
     if(label && !classes.some(value=>value.toLowerCase()===label.toLowerCase()))classes.push(label);
    }
   }
   const patients=data.patients.map(p=>({...p,class_label:data.status==='DRAFT'?
    classes.find(label=>label.toLowerCase()===p.class_label.trim().toLowerCase()) || '':p.class_label}));
   this.form={name:data.name,description:data.description,characterization_version:data.characterization_version,
    units_mode:data.units_mode,validated_only:data.config.validated_only,features:[...data.config.features],
    classes,patients,institution:data.institution_id};
   this.saved=JSON.stringify(this.form);this.preview=null;this.confirmed=false;this.newClass='';
  },
  async open(id){if(!this.confirmLeave())return;this.busy=true;this.error='';try{this.accept((await api.get(`/api/datasets/${id}/`)).data);}catch(e){this.error=authErrorMessage(e);}finally{this.busy=false;}},
  addPatient(patient){if(!patient||this.busy||!can('register')||this.form.patients.some(p=>p.patient_id===patient.id))return;this.form.patients.push({patient_id:patient.id,identity:patient,class_label:''});this.preview=null;},
  removePatient(id){this.form.patients=this.form.patients.filter(p=>p.patient_id!==id);this.preview=null;},
  versionChanged(){if(this.form.characterization_version==='2.1')this.form.units_mode='PIXELS';this.preview=null;},
  payload(){return {...this.form,institution:this.form.institution||auth.user?.institution?.id,patients:this.form.patients.map(p=>({patient_id:p.patient_id,class_label:p.class_label})),version:this.current?.version};},
  async save(){if(this.busy||!can('register')||this.current?.status!=='DRAFT')return false;this.busy=true;this.error='';try{const response=this.current.id?await api.put(`/api/datasets/${this.current.id}/`,this.payload()):await api.post('/api/datasets/',this.payload());this.accept(response.data);await this.loadList(this.page);return true;}catch(e){this.error=authErrorMessage(e);return false;}finally{this.busy=false;}},
  async previewDataset(){if(this.busy)return;if((this.dirty||!this.current.id)&&!await this.save())return;this.busy=true;this.error='';this.confirmed=false;try{this.preview=(await api.get(`/api/datasets/${this.current.id}/preview/`)).data;}catch(e){this.preview=null;this.error=authErrorMessage(e);}finally{this.busy=false;}},
  async generate(){if(this.busy||this.dirty||!this.confirmed||!this.preview||!can('register'))return;this.busy=true;this.error='';try{const {data}=await api.post(`/api/datasets/${this.current.id}/generate/`,{version:this.preview.version,preview_hash:this.preview.preview_hash,confirm:true});this.accept(data);await this.loadList(this.page);}catch(e){this.preview=null;this.confirmed=false;this.error=authErrorMessage(e);}finally{this.busy=false;}},
  async download(kind){this.busy=true;this.error='';try{const {data}=await api.get(`/api/datasets/${this.current.id}/download/${kind}/`,{responseType:'blob'});const url=URL.createObjectURL(data),link=document.createElement('a');link.href=url;link.download=`dataset-${this.current.id}.${kind==='manifest'?'json':kind}`;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}catch(e){this.error=authErrorMessage(e);}finally{this.busy=false;}},
 },
};
</script>
<style scoped>
.datasets{padding:24px;max-width:1100px;min-width:0;width:100%;margin:auto;box-sizing:border-box;color:#243b53}.card{padding:24px;background:white;border:1px solid #d9e2ec;border-radius:12px;margin:20px 0}.bar,.member{display:flex;gap:16px;align-items:center;flex-wrap:wrap;margin:16px 0}.member{padding:12px;background:#f4f7fb}.member>div{min-width:140px}label{display:flex;flex-direction:column;gap:6px;margin:12px 0}.check{flex-direction:row;align-items:center}input,select,textarea,button{font:inherit;padding:9px;border:1px solid #bcccdc;border-radius:7px;box-sizing:border-box;max-width:100%}button{background:#edf5fc;color:#15558a;cursor:pointer}button:disabled{opacity:.5;cursor:not-allowed}button:focus-visible,input:focus-visible,select:focus-visible{outline:3px solid #90caf9}fieldset{border:0;padding:0;min-width:0}.feature-group{display:inline-block;vertical-align:top;margin-right:24px}small{display:block;color:#627d98}.notice{padding:12px;background:#fff3cd;color:#674d00;border-radius:6px}[role=alert]{color:#a32323}table{border-collapse:collapse;width:100%;font-size:14px}td,th{text-align:left;padding:10px;border-bottom:1px solid #d9e2ec;overflow-wrap:anywhere}.table-wrap{overflow:auto}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}h3{margin-top:12px}@media(max-width:600px){.datasets,.card{padding:12px}}
</style>
