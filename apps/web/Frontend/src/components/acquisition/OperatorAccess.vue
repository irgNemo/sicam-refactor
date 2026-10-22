<template>
  <section class="operator-access" aria-label="Acceso de operador">
    <div v-if="operator.ready"><span>Acceso de operador activo</span> <button type="button" :disabled="disabled" @click="disconnect">Desconectar</button></div>
    <div v-else>
      <p>Inicie el acceso de operador para gestionar adquisición y calibración. El procesamiento en píxeles sigue disponible sin este acceso.</p>
      <div class="operator-fields">
        <label>Usuario <input v-model="username" autocomplete="username" :disabled="busy || disabled" @keydown.enter.prevent="connect" /></label>
        <label>Contraseña <input v-model="password" type="password" autocomplete="current-password" :disabled="busy || disabled" @keydown.enter.prevent="connect" /></label>
        <button type="button" :disabled="busy || disabled || !username || !password" @click="connect">{{ busy ? 'Conectando…' : 'Conectar' }}</button>
      </div>
    </div>
    <p v-if="error" role="alert">{{ error }}</p>
  </section>
</template>
<script>
import { operator, connectOperator, disconnectOperator } from '../../services/acquisitionService';
export default {
  props: { disabled: Boolean }, emits: ['change'],
  data: () => ({ operator, username: '', password: '', busy: false, error: '' }),
  methods: {
    async connect() {
      if (this.busy || this.disabled || !this.username || !this.password) return;
      this.busy = true; this.error = '';
      try { await connectOperator(this.username, this.password); this.$emit('change', true); }
      catch { this.error = 'No fue posible conectar. Compruebe las credenciales y la conexión segura al servidor.'; }
      finally { this.password = ''; this.busy = false; }
    },
    disconnect() { disconnectOperator(); this.$emit('change', false); },
  },
};
</script>
<style scoped>
.operator-access { padding: 16px; border: 1px solid #cbd5e1; border-radius: 10px; background: #f8fafc; margin-bottom: 20px; }
.operator-access p { font-size: 13px; margin: 0 0 12px; }
.operator-fields { display: flex; flex-wrap: wrap; gap: 12px; align-items: end; }
label { display: flex; flex-direction: column; gap: 5px; font-size: 13px; }
input, button { padding: 8px; border: 1px solid #94a3b8; border-radius: 6px; }
button { cursor: pointer; background: white; }
</style>
