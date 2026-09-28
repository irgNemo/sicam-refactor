<template>
  <div class="object-metric-groups">
    <section
      v-for="group in groups"
      :key="group.key"
      class="metric-group"
    >
      <h6>{{ group.label }}</h6>
      <dl class="metric-values">
        <div v-for="metric in group.rows" :key="metric.key">
          <dt>{{ metric.label }}</dt>
          <dd>{{ metric.value }}</dd>
        </div>
      </dl>
      <div v-if="group.quality" class="texture-quality">
        <p>Computabilidad</p>
        <dl class="metric-values">
          <div v-for="metric in group.quality" :key="metric.key">
            <dt>{{ metric.label }}</dt>
            <dd>{{ metric.value }}</dd>
          </div>
        </dl>
      </div>
    </section>
  </div>
</template>

<script>
import { objectMetricGroups } from "../../domain/characterizationPresentation";

export default {
  name: "SalivaObjectMetrics",
  props: {
    metrics: { type: Object, default: null },
    extended: { type: Boolean, default: false },
    includeDependencyMetrics: { type: Boolean, default: false },
  },
  computed: {
    groups() {
      return objectMetricGroups(this.metrics, this.extended, this.includeDependencyMetrics);
    },
  },
};
</script>

<style scoped>
.object-metric-groups { display: grid; gap: 12px; min-width: 0; }
.metric-group { border-top: 1px solid #e4e7ec; padding-top: 9px; min-width: 0; }
.metric-group h6 { color: #344054; font-size: 12px; margin: 0 0 8px; }
.metric-values { display: grid; gap: 6px; margin: 0; }
.metric-values > div { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 8px; align-items: baseline; }
.metric-values dt { color: #667085; font-size: 11px; overflow-wrap: anywhere; }
.metric-values dd { color: #344054; font-size: 12px; margin: 0; text-align: right; overflow-wrap: anywhere; max-width: 140px; }
.texture-quality { background: #f8fafc; border-radius: 6px; padding: 8px; margin-top: 10px; }
.texture-quality p { color: #667085; font-size: 10px; margin: 0 0 6px; }
</style>
