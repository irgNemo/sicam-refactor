<template>
  <span class="compact-value" :title="String(value ?? '')" :aria-label="String(value ?? '')" :tabindex="focusable ? 0 : undefined">{{ display }}</span>
</template>
<script>
import { compactIdentifier, compactFilename } from '../../domain/compactPresentation';
export default {
  props: { focusable: { type:Boolean, default:true }, value: { type:[String,Number], default:'' }, format: { type:String, default:'identifier' }, peers: { type:Array, default:()=>[] } },
  computed: { display() { return this.format==='filename' ? compactFilename(this.value) : compactIdentifier(this.value,this.peers); } },
};
</script>
<style scoped>
.compact-value{overflow-wrap:anywhere;max-width:100%}.compact-value:focus-visible{outline:2px solid #1565c0;outline-offset:2px}
/* Keyboard users can reveal the full string without relying on hover. */
.compact-value:focus::after{content:attr(title);display:block;white-space:normal;overflow-wrap:anywhere;background:#eef5fb;color:#183047;padding:4px;border-radius:4px;font-size:12px}
</style>
