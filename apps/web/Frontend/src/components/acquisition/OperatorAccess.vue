<template><p v-if="auth.user" class="operator-access">Sesión: {{ auth.user.username }} · {{ auth.user.institution?.code || 'Plataforma' }}</p></template>
<script setup>
import { auth } from '../../services/auth';
defineProps({ disabled: Boolean });
defineEmits(['change']);
</script>
<style scoped>.operator-access { color:#475569; font-size:13px; }</style>
