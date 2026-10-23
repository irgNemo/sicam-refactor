<template><label v-if="auth.user?.is_superuser">Institución operativa *<select :value="modelValue" required @change="$emit('update:modelValue', Number($event.target.value) || null)"><option value="">Seleccione</option><option v-for="institution in institutions" :key="institution.id" :value="institution.id">{{ institution.name }} ({{ institution.code }})</option></select><small v-if="error" role="alert">{{ error }}</small></label></template>
<script setup>
import { onMounted, ref } from 'vue';
import api from '../services/apiClient';
import { auth } from '../services/auth';
defineProps({ modelValue: [Number, String] }); defineEmits(['update:modelValue']);
const institutions = ref([]), error = ref('');
onMounted(async () => { if (auth.user?.is_superuser) { try { institutions.value = (await api.get('/api/institutions/')).data.filter(item => item.active); } catch { error.value = 'No se pudieron cargar las instituciones.'; } } });
</script>
<style scoped>label { display:grid; gap:6px; margin:12px 0; } select { padding:9px; } small { color:#991b1b; }</style>
