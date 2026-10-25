<template>
  <main v-if="can('administer')" class="administration">
    <h2>Administración</h2>
    <nav><button @click="tab = 'users'">Usuarios</button><button @click="tab = 'institutions'">{{ auth.user.is_superuser ? 'Instituciones' : 'Institución' }}</button></nav>
    <p v-if="error" role="alert">{{ error }}</p><p v-if="notice" role="status">{{ notice }}</p>
    <section v-if="tab === 'users'">
      <h3>Usuarios</h3><button @click="editUser()">Crear usuario</button>
      <table><thead><tr><th>Nombre</th><th>Usuario</th><th>Correo</th><th>Rol</th><th>Institución</th><th>Estado</th><th>Acciones</th></tr></thead>
        <tbody><tr v-for="user in users" :key="user.id"><td>{{ `${user.first_name} ${user.last_name}`.trim() || user.username }}</td><td>{{ user.username }}</td><td>{{ user.email }}</td><td>{{ user.is_superuser ? 'Plataforma' : user.role }}</td><td>{{ user.institution?.code || '—' }}</td><td>{{ user.is_active ? 'Activo' : 'Inactivo' }}</td><td><button v-if="!user.is_superuser" @click="editUser(user)">Editar</button></td></tr></tbody>
      </table>
      <form v-if="form" @submit.prevent="saveUser">
        <h3>{{ form.id ? 'Editar usuario' : 'Crear usuario' }}</h3>
        <label>Usuario<input v-model="form.username" required autocomplete="off" /></label>
        <label>Nombre<input v-model="form.first_name" /></label><label>Apellidos<input v-model="form.last_name" /></label><label>Correo<input v-model="form.email" type="email" /></label>
        <label>Rol<select v-model="form.role"><option>ADMIN</option><option>OPERATOR</option><option>REVIEWER</option></select></label>
        <label v-if="auth.user.is_superuser">Institución<select v-model="form.institution" required :disabled="Boolean(form.id)"><option v-for="institution in institutions.filter(i => i.active)" :key="institution.id" :value="institution.id">{{ institution.name }}</option></select></label>
        <p v-else>Institución: {{ auth.user.institution.name }}</p>
        <label><input v-model="form.is_active" type="checkbox" /> Activo</label>
        <template v-if="!form.id"><label>Contraseña temporal<input v-model="form.temporary_password" type="password" required autocomplete="new-password" /></label><label>Confirmación<input v-model="form.confirmation" type="password" required autocomplete="new-password" /></label></template>
        <button :disabled="busy">Guardar</button><button type="button" @click="form = null">Cancelar</button>
      </form>
    </section>
    <section v-else><h3>{{ auth.user.is_superuser ? 'Instituciones' : 'Institución' }}</h3>
      <button v-if="auth.user.is_superuser" @click="institutionForm = { code: '', name: '', notes: '', active: true }">Crear institución</button>
      <article v-for="institution in institutions" :key="institution.id"><h4>{{ institution.name }} ({{ institution.code }})</h4><p>{{ institution.active ? 'Activa' : 'Inactiva' }} · {{ institution.notes }}</p><button v-if="auth.user.is_superuser" @click="institutionForm = {...institution}">Editar</button></article>
      <form v-if="institutionForm && auth.user.is_superuser" @submit.prevent="saveInstitution"><label>Código<input v-model="institutionForm.code" required :disabled="Boolean(institutionForm.id)" /></label><label>Nombre<input v-model="institutionForm.name" required /></label><label>Notas<textarea v-model="institutionForm.notes" /></label><label><input v-model="institutionForm.active" type="checkbox" /> Activa</label><button :disabled="busy">Guardar</button><button type="button" @click="institutionForm = null">Cancelar</button></form>
    </section>
  </main><p v-else role="alert">No tiene acceso a Administración.</p>
</template>
<script setup>
import { ref, onMounted } from 'vue';
import api from '../services/apiClient';
import { auth, can, refreshSession } from '../services/auth';
const tab = ref('users'), users = ref([]), institutions = ref([]), form = ref(null), institutionForm = ref(null), busy = ref(false), error = ref(''), notice = ref('');
const message = e => e.response?.data ? Object.values(e.response.data).flat().join(' ') : 'No se pudo completar la operación.';
async function load() { if (!can('administer')) return; const [u, i] = await Promise.all([api.get('/api/users/'), api.get('/api/institutions/')]); users.value = u.data; institutions.value = i.data; }
onMounted(() => load().catch(e => { error.value = message(e); }));
function editUser(user) { form.value = user ? { id:user.id, username:user.username, first_name:user.first_name, last_name:user.last_name, email:user.email, role:user.role, institution:user.institution.id, is_active:user.is_active } : { username:'', first_name:'', last_name:'', email:'', role:'OPERATOR', institution:auth.user.institution?.id || '', is_active:true, temporary_password:'', confirmation:'' }; }
async function saveUser() { if (busy.value) return; busy.value = true; error.value = ''; const draft = form.value;
  try { const {id, ...payload} = draft; if (id) await api.patch(`/api/users/${id}/`, payload); else await api.post('/api/users/', payload); form.value = null; notice.value = id ? 'Usuario actualizado.' : 'El usuario deberá cambiar su contraseña al iniciar sesión.'; await refreshSession(); await load(); }
  catch(e) { error.value = message(e); } finally { if (draft) { delete draft.temporary_password; delete draft.confirmation; } busy.value = false; }
}
async function saveInstitution() { if (busy.value) return;
  const deactivating = institutionForm.value.id && !institutionForm.value.active && institutions.value.find(item => item.id === institutionForm.value.id)?.active;
  if (deactivating && !window.confirm(`Desactivar ${institutionForm.value.name} impedirá operar a todos sus usuarios, incluidas las sesiones abiertas. ¿Desactivar esta institución?`)) return;
  busy.value = true; error.value = ''; try { const {id, code, name, notes, active} = institutionForm.value; if(id) await api.patch(`/api/institutions/${id}/`, {code,name,notes,active,confirm_deactivation:Boolean(deactivating)}); else await api.post('/api/institutions/', {code,name,notes,active}); institutionForm.value = null; await load(); } catch(e) { error.value=message(e); } finally { busy.value=false; } }
function confirmLeave() { return !busy.value && (!(form.value || institutionForm.value) || window.confirm('¿Salir sin guardar el formulario administrativo?')); }
defineExpose({ confirmLeave });
</script>
<style scoped>
.administration { padding:24px; overflow:auto; width:100%; font-family:system-ui; } table { width:100%; border-collapse:collapse; margin:20px 0; } th,td { text-align:left; padding:10px; border-bottom:1px solid #e2e8f0; } button,input,select,textarea { padding:8px; margin:4px; border:1px solid #94a3b8; border-radius:5px; } form { max-width:580px; padding:20px; background:#f8fafc; } label { display:block; margin:8px 0; } [role=alert] { color:#991b1b; }
</style>
