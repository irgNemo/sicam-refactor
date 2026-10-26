<template>
  <section v-if="can('administer')" class="audit-panel">
    <h3>{{ mode === 'events' ? 'Auditoría' : mode === 'archived' ? 'Archivados' : 'Diagnóstico operativo' }}</h3>
    <p v-if="error" role="alert">{{ error }}</p>
    <form v-if="mode !== 'health'" class="filters" @submit.prevent="search">
      <label v-if="auth.user.is_superuser">Institución<select v-model="filters.institution"><option value="">Todas</option><option v-for="i in institutions" :key="i.id" :value="i.id">{{ i.code }}</option></select></label>
      <label>Desde<input v-model="filters.date_from" type="date" /></label><label>Hasta<input v-model="filters.date_to" type="date" /></label>
      <label>{{ mode === 'events' ? 'Usuario' : 'Archivado/retirado por' }}<select v-model="filters.actor"><option value="">Todos</option><option v-for="u in options.actors" :key="u.id" :value="u.id">{{ u.username }}</option></select></label>
      <template v-if="mode === 'events'">
        <label>Acción<select v-model="filters.action"><option value="">Todas</option><option v-for="a in options.actions" :key="a" :value="a">{{ auditLabels[a] || a }}</option></select></label>
        <label>Tipo de recurso<select v-model="filters.target_type"><option value="">Todos</option><option v-for="t in options.target_types" :key="t">{{ t }}</option></select></label>
      </template>
      <template v-else>
        <label>Tipo<select v-model="filters.type"><option v-for="(label, value) in archiveLabels" :key="value" :value="value">{{ label }}</option></select></label>
        <label>ID o tipo técnico<input v-model="filters.search" placeholder="ID del recurso" /></label>
      </template>
      <button :disabled="loading || actionBusy">Buscar</button>
    </form>
    <template v-if="mode === 'health'">
      <p>Consulta de sólo lectura. No repara datos ni certifica el despliegue.</p>
      <button :disabled="loading" @click="loadHealth(false)">Comprobar estado</button>
      <button :disabled="loading" @click="loadHealth(true)">Verificar archivos</button>
      <p>La verificación de archivos comprueba referencias; no recalcula hashes ni elimina archivos huérfanos.</p>
      <p v-if="health">Estado: <strong>{{ health.status }}</strong> · {{ health.scope === 'GLOBAL' ? 'Plataforma' : 'Institución' }}</p>
      <ul v-if="health"><li v-for="check in health.checks" :key="check.code"><strong>{{ check.code }}: {{ check.status }}</strong><span v-if="check.count"> · {{ check.count }} incidencias</span><details v-if="check.issues?.length"><summary>Ver IDs afectados (máximo {{ health.issue_limit }})</summary><ul><li v-for="(issue, index) in check.issues" :key="index">{{ issue.resource_type }} #{{ issue.id }} {{ issue.field || issue.issue || '' }}</li></ul></details><p v-if="check.migrations?.length">Migraciones pendientes: {{ check.migrations.join(', ') }}</p></li></ul>
    </template>
    <template v-else>
      <p>{{ result.count }} registros</p>
      <div class="table-scroll"><table v-if="mode === 'events'"><thead><tr><th>Fecha/hora</th><th>Usuario</th><th>Institución</th><th>Acción</th><th>Recurso</th><th>Motivo</th><th>Detalle</th></tr></thead>
        <tbody><tr v-for="row in result.results" :key="row.id"><td>{{ displayDate(row.created_at) }}</td><td>{{ row.actor?.username || 'No disponible' }}</td><td>{{ row.institution?.code || 'Sin institución' }}</td><td>{{ auditLabels[row.action] || row.action }}</td><td>{{ row.description }} <span v-if="row.is_test" class="badge">TEST</span><p v-if="row.target_deleted">Recurso eliminado</p></td><td>{{ row.reason }}</td><td><button :disabled="loading" @click="openEvent(row.id)">Ver evento {{ row.id }}</button></td></tr></tbody>
      </table>
      <table v-else><thead><tr><th>Recurso</th><th>Institución</th><th>Estado</th><th>Fecha de archivo/retiro</th><th>Usuario ID</th><th>Acciones</th></tr></thead><tbody><tr v-for="row in result.results" :key="`${row.resource}:${row.id}`"><td>{{ row.description }} <span v-if="row.is_test" class="badge">TEST</span></td><td>{{ row.institution_id || 'Sin institución' }}</td><td>{{ row.status }}</td><td>{{ displayDate(row.archived_at) }}</td><td>{{ row.archived_by || '—' }}</td><td><LifecycleActions v-if="row.status !== 'RETIRED'" :resource="row.resource" :id="row.id" :label="row.description" :disabled="loading || actionBusy" @busy="setBusy" @changed="load" /><span v-else>Sin reactivación administrativa</span></td></tr></tbody></table></div>
      <p v-if="!loading && !result.results.length">Sin registros para estos filtros.</p>
      <div class="pagination"><button :disabled="!result.previous || loading || actionBusy" @click="changePage(-1)">Anterior</button><span>Página {{ page }}</span><button :disabled="!result.next || loading || actionBusy" @click="changePage(1)">Siguiente</button></div>
    </template>
    <p v-if="loading" role="status">Consultando…</p>
    <article v-if="detail && mode === 'events'" class="event-detail">
      <h4>Evento {{ detail.id }}</h4><button @click="detail = null">Cerrar detalle</button>
      <p>{{ displayDate(detail.created_at) }} · {{ auditLabels[detail.action] }} · {{ detail.description }}</p>
      <p>{{ detail.actor?.username || 'Actor no disponible' }} · Rol actual: {{ detail.actor?.current_role || 'No disponible' }} · {{ detail.institution?.code }}</p>
      <p v-if="detail.target_deleted">Recurso eliminado</p><p v-if="detail.is_test">TEST</p><p>Motivo: {{ detail.reason }}</p>
      <h5>Dependencias al ejecutar</h5><ul><li v-for="(count, name) in detail.metadata.dependencies" :key="name">{{ name }}: {{ count }}</li></ul>
      <p v-if="!Object.keys(detail.metadata.dependencies).length">Sin dependencias registradas.</p>
      <ul><li v-for="(file, index) in detail.metadata.media_cleanup" :key="index">{{ file.filename }} · {{ file.status }}<p v-if="file.sha256">SHA-256: <code>{{ file.sha256 }}</code></p></li></ul>
    </article>
  </section><p v-else role="alert">No tiene acceso administrativo.</p>
</template>
<script>
import { auth, can } from '../../services/auth';
import { fetchAudit, fetchEvent, auditError, auditLabels, archiveLabels, displayDate } from '../../services/adminAudit';
import LifecycleActions from '../lifecycle/LifecycleActions.vue';
export default {
  components: { LifecycleActions }, props: { mode: {type:String, required:true}, institutions: {type:Array, default:()=>[]} }, emits:['busy'],
  data:()=>({auth,auditLabels,archiveLabels,loading:false,actionBusy:false,error:'',result:{count:0,results:[],next:null,previous:null},options:{actors:[],actions:[],target_types:[]},detail:null,health:null,page:1,generation:0,disposed:false,filters:{institution:'',actor:'',date_from:'',date_to:'',action:'',target_type:'',type:'pacientes',search:''}}),
  mounted(){ this.initialize(); }, beforeUnmount(){ this.disposed=true; this.generation++; },
  watch:{ mode(){this.page=1;this.detail=null;this.result={count:0,results:[]};this.initialize();} },
  methods:{
    can,displayDate,
    setBusy(value){this.actionBusy=value;this.$emit('busy',value);},
    async initialize(){ if(!can('administer'))return; try {this.options=await fetchAudit('options',{},auth.user);}catch(e){this.error=auditError(e);} if(!this.disposed)await this.load(); },
    search(){this.page=1;this.detail=null;return this.load();},
    changePage(delta){this.page+=delta;this.detail=null;return this.load();},
    async load(){
      if(this.mode==='health')return this.loadHealth(false);
      if(!can('administer'))return;
      const generation=++this.generation;this.loading=true;this.error='';
      const {institution,actor,date_from,date_to,type,search,action,target_type}=this.filters;
      const filters={institution,date_from,date_to,page:this.page,...(this.mode==='events'?{actor,action,target_type}:{type,search,archived_by:actor})};
      try{const result=await fetchAudit(this.mode,filters,auth.user);if(!this.disposed && generation===this.generation)this.result=result;}
      catch(e){if(generation===this.generation)this.error=auditError(e);}finally{if(generation===this.generation)this.loading=false;}
    },
    async openEvent(id){const generation=++this.generation;this.loading=true;try{const detail=await fetchEvent(id);if(!this.disposed && generation===this.generation)this.detail=detail;}catch(e){this.error=auditError(e);}finally{if(generation===this.generation)this.loading=false;}},
    async loadHealth(files){if(!can('administer'))return;const generation=++this.generation;this.loading=true;this.error='';try{const health=await fetchAudit('health',{check_files:files?'true':'false'},auth.user);if(!this.disposed && generation===this.generation)this.health=health;}catch(e){this.error=auditError(e);}finally{if(generation===this.generation)this.loading=false;}},
  },
};
</script>
<style scoped>
.filters{display:flex;flex-wrap:wrap;align-items:end;gap:12px;margin:16px 0}.filters label{display:grid;gap:4px}button,input,select{padding:8px;border:1px solid #94a3b8;border-radius:5px}button:disabled{opacity:.5}.table-scroll{overflow:auto}table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:10px;border-bottom:1px solid #e2e8f0;vertical-align:top}td{overflow-wrap:anywhere;max-width:320px}.badge{background:#fef3c7;color:#78350f;padding:2px 6px;border-radius:4px}.event-detail{background:#f8fafc;padding:18px;margin-top:20px}code{overflow-wrap:anywhere}.pagination{display:flex;gap:12px;align-items:center;margin:12px 0}[role=alert]{color:#991b1b}li{margin:10px 0}
</style>
