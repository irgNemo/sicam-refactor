<template>
  <p v-if="!auth.ready" role="status">Comprobando sesión…</p>
  <main v-else-if="!auth.user || auth.user.must_change_password" class="auth-page">
    <form @submit.prevent="submit" class="auth-card">
      <h1>SICAM</h1><h2>{{ auth.user ? 'Cambie su contraseña' : 'Iniciar sesión' }}</h2>
      <p v-if="auth.user">Debe cambiar la contraseña temporal antes de continuar.</p>
      <label v-if="!auth.user">Usuario<input v-model="username" required autocomplete="username" /></label>
      <label>{{ auth.user ? 'Contraseña actual' : 'Contraseña' }}<input v-model="password" type="password" required autocomplete="current-password" /></label>
      <template v-if="auth.user"><label>Nueva contraseña<input v-model="newPassword" type="password" required autocomplete="new-password" /></label><label>Confirmación<input v-model="confirmation" type="password" required autocomplete="new-password" /></label></template>
      <p v-if="error || auth.error" role="alert">{{ error || auth.error }}</p>
      <button :disabled="busy">{{ busy ? 'Procesando…' : auth.user ? 'Cambiar contraseña' : 'Entrar' }}</button>
      <button v-if="auth.user" type="button" @click="leave">Cerrar sesión</button>
    </form>
  </main>
  <App v-else :key="`${auth.user.id}:${auth.user.institution?.id}`" />
</template>
<script setup>
import { ref } from 'vue';
import App from './App.vue';
import { auth, authErrorMessage, initializeSession, login, logout, changePassword } from './services/auth';
const username = ref(''), password = ref(''), newPassword = ref(''), confirmation = ref(''), error = ref(''), busy = ref(false);
initializeSession();
async function submit() {
  if (busy.value) return;
  busy.value = true; error.value = '';
  try {
    if (auth.user) await changePassword(password.value, newPassword.value, confirmation.value);
    else await login(username.value, password.value);
  } catch (e) { error.value = authErrorMessage(e); }
  finally { password.value = ''; newPassword.value = ''; confirmation.value = ''; busy.value = false; }
}
async function leave() { try { await logout(); } catch { error.value = 'No se pudo cerrar la sesión.'; } }
</script>
<style scoped>
.auth-page { min-height: 100vh; display:grid; place-items:center; background:#f1f5f9; font-family:system-ui; }
.auth-card { width:min(380px,85vw); padding:32px; background:white; border:1px solid #cbd5e1; border-radius:14px; }
label { display:grid; gap:6px; margin:16px 0; } input,button { padding:10px; border:1px solid #94a3b8; border-radius:6px; } button { cursor:pointer; margin-right:8px; } [role=alert] { color:#991b1b; }
</style>
