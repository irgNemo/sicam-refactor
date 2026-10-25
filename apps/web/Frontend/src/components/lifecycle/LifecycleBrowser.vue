<template>
  <section v-if="canManageLifecycle(auth.user)" class="lifecycle-browser">
    <button type="button" :disabled="disabled || busy" :aria-expanded="opened" @click="toggle">Gestionar registros existentes</button>
    <div v-if="opened">
      <label>Tipo de registro<select v-model="resource" :disabled="disabled || busy" @change="load"><option v-for="entry in resources" :key="entry[0]" :value="entry[0]">{{ entry[1] }}</option></select></label>
      <label v-if="canSeeArchived(auth.user)"><input v-model="includeArchived" type="checkbox" :disabled="disabled || busy" @change="load" /> Incluir archivados</label>
      <p v-if="error" role="alert">{{ error }}</p><p v-if="loading" role="status">Cargando…</p>
      <p v-else-if="!rows.length">No hay registros disponibles.</p>
      <ul><li v-for="row in rows" :key="rowId(row)"><span>{{ rowLabel(row) }} <strong v-if="row.archived_at">Archivado</strong><em v-else-if="row.operationally_active === false">Oculto por archivo de un superior</em></span>
        <LifecycleActions :resource="resource" :id="rowId(row)" :label="rowLabel(row)" :disabled="disabled || busy" @busy="busy = $event; $emit('busy', $event)" @changed="changed" />
      </li></ul>
    </div>
  </section>
</template>
<script>
import { auth } from '../../services/auth';
import api from '../../services/apiClient';
import LifecycleActions from './LifecycleActions.vue';
import { canManageLifecycle, canSeeArchived, archivedParams, lifecycleError } from '../../services/lifecycle';
export default {
  components: { LifecycleActions }, props: { disabled: Boolean }, emits: ['changed', 'busy'],
  data: () => ({ auth, opened: false, loading: false, busy: false, resource: 'pacientes', includeArchived: false, rows: [], error: '', generation: 0,
    resources: [['pacientes','Pacientes'],['casos','Casos'],['analisis','Análisis'],['muestras','Imágenes SALIVA'],['muestras-sangre','Imágenes SANGRE'],['acquisition-series','Series']] }),
  beforeUnmount() { this.generation++; },
  methods: {
    canManageLifecycle, canSeeArchived,
    rowId: row => row.id_paciente || row.id_caso || row.id_analisis || row.id_muestra || row.id,
    rowLabel(row) { return row.display_name || row.titulo || row.label || `${this.resources.find(entry => entry[0] === this.resource)?.[1]} #${this.rowId(row)}`; },
    async toggle() { this.opened = !this.opened; if (this.opened) await this.load(); },
    async load() {
      const generation = ++this.generation; this.loading = true; this.rows = []; this.error = '';
      try { const response = await api.get(`/api/${this.resource}/`, { params: archivedParams(auth.user, this.includeArchived) }); if (generation === this.generation) this.rows = response.data; }
      catch (error) { if (generation === this.generation) this.error = lifecycleError(error); }
      finally { if (generation === this.generation) this.loading = false; }
    },
    async changed() { await this.load(); this.$emit('changed'); },
  },
};
</script>
<style scoped>
.lifecycle-browser { margin:24px 0; padding:20px; background:white; border:1px solid #d5dfe8; border-radius:10px; }
label { display:inline-flex; align-items:center; gap:8px; margin:14px 16px 14px 0; } button,select { padding:8px 12px; } ul { list-style:none; padding:0; max-height:460px; overflow:auto; } li { display:flex; justify-content:space-between; align-items:center; gap:12px; padding:12px 0; border-bottom:1px solid #e3e9f0; } span { overflow-wrap:anywhere; } strong,em { display:block; font-size:12px; color:#775c16; } [role=alert] { color:#a32323; }
</style>
