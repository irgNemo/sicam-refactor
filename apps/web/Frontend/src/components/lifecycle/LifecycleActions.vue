<template>
  <span v-if="canManageLifecycle(auth.user)" class="lifecycle-actions">
    <button type="button" :disabled="disabled || busy" @click="open">Más acciones</button>
    <div v-if="opened" class="lifecycle-backdrop" @keydown.esc="close">
      <section role="dialog" aria-modal="true" :aria-labelledby="titleId" class="lifecycle-dialog" tabindex="-1" ref="dialog" @keydown.tab="trapFocus">
        <h3 :id="titleId">{{ label || preview?.display || 'Registro' }}</h3>
        <p v-if="busy" role="status">Comprobando…</p>
        <p v-if="error" role="alert">{{ error }}</p>
        <template v-if="preview">
          <h4>Dependencias</h4>
          <dl v-if="Object.keys(preview.dependencies).length"><template v-for="(count, name) in preview.dependencies" :key="name"><dt>{{ dependencyLabels[name] || name }}</dt><dd>{{ count }}</dd></template></dl>
          <p v-else>Sin dependencias registradas.</p>
          <p v-for="file in preview.media_files" :key="file.filename">Archivo: {{ file.filename }}</p>
          <p v-for="warning in preview.warnings" :key="warning.code">{{ warningText(warning) }}</p>
          <p v-if="!preview.allowed_actions.length">No hay acciones disponibles para su rol y el estado actual.</p>
          <form v-else @submit.prevent="execute">
            <label>Acción<select v-model="action" :disabled="busy" @change="confirmed = false"><option v-for="value in preview.allowed_actions" :key="value" :value="value">{{ actionLabels[value] || value }}{{ value === preview.recommended_action ? ' (recomendada)' : '' }}</option></select></label>
            <p>{{ consequences[action] }}</p>
            <label>Motivo<select v-model="reason" :disabled="busy" required><option value="">Seleccione</option><option>Creado/subido por error</option><option>Duplicado</option><option>Configuración incorrecta</option><option>Ya no debe utilizarse</option><option>Restauración autorizada</option><option>Otro</option></select></label>
            <label>Comentario {{ reason === 'Otro' ? '(obligatorio)' : '(opcional)' }}<textarea v-model="comment" :required="reason === 'Otro'" :disabled="busy" maxlength="1800" /></label>
            <label class="confirmation"><input v-model="confirmed" type="checkbox" :disabled="busy" /> Confirmo: {{ actionLabels[action] }} {{ label || preview.display }}</label>
            <button type="submit" :disabled="busy || !confirmed || !reason || (reason === 'Otro' && !comment.trim())">{{ actionLabels[action] }}</button>
          </form>
        </template>
        <button type="button" :disabled="busy" @click="close">Cerrar</button>
      </section>
    </div>
  </span>
</template>
<script>
import { auth } from '../../services/auth';
import { actionLabels, consequences, dependencyLabels, canManageLifecycle, inspectLifecycle, applyLifecycle, lifecycleError } from '../../services/lifecycle';
export default {
  props: { resource: { type: String, required: true }, id: { type: [Number, String], required: true }, label: { type: String, default: '' }, disabled: Boolean },
  emits: ['changed', 'busy'],
  data: () => ({ auth, actionLabels, consequences, dependencyLabels, opened: false, busy: false, error: '', preview: null, action: '', reason: '', comment: '', confirmed: false, previousFocus: null }),
  computed: { titleId() { return `lifecycle-${this.resource}-${this.id}`; } },
  methods: {
    canManageLifecycle,
    warningText(warning) { return lifecycleError({ response: { data: warning } }); },
    async open() {
      if (this.disabled || this.busy) return;
      this.previousFocus = typeof document !== 'undefined' ? document.activeElement : null;
      this.opened = true; this.reason = ''; this.comment = ''; this.confirmed = false; this.error = ''; this.preview = null;
      await this.load(); await this.$nextTick(); this.$refs.dialog?.focus();
    },
    async load() {
      this.busy = true;
      try { this.preview = await inspectLifecycle(this.resource, this.id); this.action = this.preview.recommended_action || ''; }
      catch (error) { this.error = lifecycleError(error); }
      finally { this.busy = false; }
    },
    async execute() {
      if (this.busy || !this.confirmed || !this.reason || (this.reason === 'Otro' && !this.comment.trim()) || !this.preview?.allowed_actions.includes(this.action)) return;
      this.busy = true; this.error = ''; this.$emit('busy', true);
      try {
        await applyLifecycle(this.resource, this.id, this.action, [this.reason, this.comment.trim()].filter(Boolean).join(': '), this.confirmed);
        this.opened = false; this.previousFocus?.focus(); this.$emit('changed');
      } catch (error) {
        const message = lifecycleError(error); this.confirmed = false;
        if (error.response?.status === 409) await this.load();
        this.error = message;
      } finally { this.busy = false; this.$emit('busy', false); }
    },
    close() { if (!this.busy) { this.opened = false; this.previousFocus?.focus(); } },
    trapFocus(event) {
      const elements = [...this.$refs.dialog.querySelectorAll('button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled)')];
      const first = elements[0], last = elements.at(-1);
      if (!first) { event.preventDefault(); return; }
      if (event.shiftKey && (document.activeElement === first || document.activeElement === this.$refs.dialog)) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    },
  },
};
</script>
<style scoped>
button { padding:8px 12px; border:1px solid #9aabba; border-radius:6px; background:white; cursor:pointer; } button:disabled { opacity:.5; cursor:default; }
.lifecycle-backdrop { position:fixed; inset:0; z-index:2000; background:#10243788; display:grid; place-items:center; padding:16px; }
.lifecycle-dialog { background:white; color:#183047; width:min(560px,100%); max-height:85vh; overflow:auto; padding:24px; border-radius:12px; box-shadow:0 12px 48px #0004; }
label { display:grid; gap:6px; margin:14px 0; } input,select,textarea { padding:8px; } .confirmation { display:flex; align-items:center; gap:8px; }
dl { display:grid; grid-template-columns:1fr auto; } dd { margin:0; } [role=alert] { color:#a32323; } h3 { overflow-wrap:anywhere; }
</style>
