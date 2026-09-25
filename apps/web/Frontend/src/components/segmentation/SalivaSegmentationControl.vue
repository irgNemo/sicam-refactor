<template>
  <form class="saliva-segmentation-control" @submit.prevent="runSegmentation">
    <fieldset :disabled="loading">
      <legend>Método de segmentación</legend>
      <p class="method-help">Para una nueva segmentación.</p>
      <label v-for="option in options" :key="option.value" class="method-option">
        <input
          v-model="selectedStrategy"
          type="radio"
          name="saliva-segmentation-strategy"
          :value="option.value"
        >
        <span>
          <strong>{{ option.label }}</strong>
          <small>{{ option.description }}</small>
        </span>
      </label>
    </fieldset>
    <button class="btn-segment" :disabled="loading" type="submit">
      {{ buttonText }}
    </button>
  </form>
</template>

<script>
import {
  SALIVA_STRATEGIES,
  SALIVA_STRATEGY_OPTIONS,
} from "../../domain/segmentationStrategies";

export default {
  name: "SalivaSegmentationControl",
  props: {
    loading: { type: Boolean, required: true },
    buttonText: { type: String, required: true },
  },
  emits: ["run-segmentation"],
  data() {
    return {
      selectedStrategy: SALIVA_STRATEGIES.CURRENT,
      options: SALIVA_STRATEGY_OPTIONS,
    };
  },
  methods: {
    runSegmentation() {
      if (!this.loading) this.$emit("run-segmentation", this.selectedStrategy);
    },
  },
};
</script>

<style scoped>
.saliva-segmentation-control {
  display: grid;
  gap: 10px;
}

fieldset {
  margin: 0;
  min-width: 0;
  padding: 10px;
  border: 1px solid #d9e2ec;
  border-radius: 8px;
}

legend, .method-option strong {
  font-size: 12px;
  font-weight: 600;
}

.method-help, .method-option small {
  display: block;
  color: #526477;
  font-size: 11px;
  line-height: 1.4;
}

.method-help {
  margin: 0 0 8px;
}

.method-option {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  padding: 6px 0;
  cursor: pointer;
}

.method-option input {
  flex-shrink: 0;
  accent-color: #1e88e5;
}

fieldset:disabled .method-option {
  cursor: wait;
  opacity: 0.7;
}

.btn-segment {
  background: #1e88e5;
  border: 2px solid #1e88e5;
  border-radius: 10px;
  color: white;
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  padding: 12px;
  width: 100%;
}

.btn-segment:hover:not(:disabled) {
  background: #1976d2;
  border-color: #1976d2;
}

.btn-segment:disabled {
  cursor: wait;
  opacity: 0.7;
}
</style>
