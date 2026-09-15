<template>
  <div class="morphometric-result">
    <section class="result-section">
      <div class="section-heading">
        <div>
          <h4>Resumen morfometrico</h4>
          <p>Valores persistidos por la caracterizacion SALIVA v2.</p>
        </div>
        <span class="schema-badge">Esquema {{ resultJson.schema_version }}</span>
      </div>

      <div class="summary-grid">
        <article
          v-for="item in primarySummaryRows"
          :key="item.key"
          class="summary-card"
        >
          <span>{{ item.label }}</span>
          <strong>{{ item.value }}</strong>
        </article>
      </div>

      <div class="nuclear-class-panel">
        <h5>Clases nucleares</h5>
        <dl class="nuclear-class-grid">
          <div
            v-for="item in nuclearClassRows"
            :key="item.key"
          >
            <dt>{{ item.label }}</dt>
            <dd>{{ item.value }}</dd>
          </div>
        </dl>
      </div>
    </section>

    <section class="result-section">
      <div class="section-heading">
        <div>
          <h4>Indices cientificos</h4>
          <p>Indices y morfometria agregada persistidos por el backend.</p>
        </div>
      </div>

      <div class="science-grid">
        <article class="index-card">
          <div>
            <span>Genotoxicidad</span>
            <strong>{{ genotoxicityDisplay }}</strong>
          </div>
          <span
            class="science-status"
            :class="statusClass(summary.genotoxicity_status)"
          >
            {{ statusDisplay(summary.genotoxicity_status) }}
          </span>
          <small>Porcentaje visual derivado del indice persistido.</small>
        </article>
        <article class="index-card">
          <div>
            <span>Indice de citotoxicidad</span>
            <strong>{{ formatNumber(summary.cytotoxicity_index, 4) }}</strong>
          </div>
          <span
            class="science-status"
            :class="statusClass(summary.cytotoxicity_status)"
          >
            {{ statusDisplay(summary.cytotoxicity_status) }}
          </span>
          <small>Indice persistido; no se recalcula en esta vista.</small>
        </article>
        <article class="science-metric-card">
          <span>Area nuclear promedio</span>
          <strong>{{ formatNumber(summary.mean_nucleus_area_px2, 2, " px²") }}</strong>
        </article>
        <article class="science-metric-card">
          <span>Circularidad nuclear promedio</span>
          <strong>{{ formatNumber(summary.mean_nucleus_circularity, 4) }}</strong>
        </article>
      </div>
    </section>

    <section class="result-section">
      <div class="section-heading">
        <div>
          <h4>Calidad de asociaciones</h4>
          <p>Conteos y tasas entregados por el backend.</p>
        </div>
      </div>
      <div class="association-grid">
        <article class="association-card">
          <h5>Nucleos</h5>
          <dl>
            <div>
              <dt>Asociados a membrana</dt>
              <dd>{{ displayValue(associationQuality.nuclei_associated) }}</dd>
            </div>
            <div>
              <dt>Total</dt>
              <dd>{{ displayValue(associationQuality.nuclei_total) }}</dd>
            </div>
            <div>
              <dt>No asociados</dt>
              <dd>{{ displayValue(summary.unassociated_nuclei) }}</dd>
            </div>
            <div>
              <dt>Ambiguos</dt>
              <dd>{{ displayValue(summary.ambiguous_nuclei) }}</dd>
            </div>
            <div class="association-rate">
              <dt>Tasa de asociacion</dt>
              <dd>{{ formatNumber(associationQuality.nuclei_association_rate, 4) }}</dd>
            </div>
          </dl>
        </article>

        <article class="association-card">
          <h5>Micronucleos</h5>
          <dl>
            <div>
              <dt>Asociados a membrana</dt>
              <dd>{{ displayValue(associationQuality.micronuclei_associated_to_membrane) }}</dd>
            </div>
            <div>
              <dt>Asociados a nucleo</dt>
              <dd>{{ displayValue(associationQuality.micronuclei_associated_to_nucleus) }}</dd>
            </div>
            <div>
              <dt>Total</dt>
              <dd>{{ displayValue(associationQuality.micronuclei_total) }}</dd>
            </div>
            <div>
              <dt>No asociados</dt>
              <dd>{{ displayValue(summary.unassociated_micronuclei) }}</dd>
            </div>
            <div>
              <dt>Ambiguos</dt>
              <dd>{{ displayValue(summary.ambiguous_micronuclei) }}</dd>
            </div>
            <div class="association-rate">
              <dt>Tasa a membrana</dt>
              <dd>{{ formatNumber(associationQuality.micronuclei_membrane_association_rate, 4) }}</dd>
            </div>
            <div class="association-rate">
              <dt>Tasa a nucleo</dt>
              <dd>{{ formatNumber(associationQuality.micronuclei_nucleus_association_rate, 4) }}</dd>
            </div>
          </dl>
        </article>
      </div>
    </section>

    <div class="result-section evidence-section">
      <slot name="effective-overlay"></slot>
    </div>

    <section class="result-section">
      <div class="section-heading">
        <div>
          <h4>Celulas caracterizadas</h4>
          <p>Una fila por cada elemento persistido en <code>cells</code>.</p>
        </div>
        <span class="section-count">{{ cells.length }}</span>
      </div>

      <div
        v-if="cells.length"
        ref="cellsScroll"
        class="table-scroll cells-table-scroll"
      >
        <table class="data-table cells-table">
          <thead>
            <tr>
              <th>Celula</th>
              <th>Clase nuclear</th>
              <th>Nucleos</th>
              <th>Micronucleos</th>
              <th>Asociacion</th>
              <th>Detalle</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(cell, cellIndex) in cells"
              :key="cellKey(cell, cellIndex)"
              :data-membrane-id="cell.membrane_id"
              :class="{ 'cell-selected': cell.membrane_id != null && selectedCellId === cell.membrane_id }"
              @click="$emit('select-cell', cell.membrane_id)"
            >
              <td>
                <button
                  type="button"
                  class="cell-select-button"
                  :disabled="cell.membrane_id == null"
                  :aria-pressed="cell.membrane_id != null && selectedCellId === cell.membrane_id"
                  @click.stop="$emit('select-cell', cell.membrane_id)"
                >
                  {{ displayValue(cell.display_label) }}
                  <span v-if="cell.membrane_id != null && selectedCellId === cell.membrane_id">✓ Seleccionada</span>
                </button>
              </td>
              <td>{{ nuclearClassDisplay(cell.nuclear_class) }}</td>
              <td>{{ displayValue(cell.nuclei_count) }}</td>
              <td>{{ displayValue(cell.micronuclei_count) }}</td>
              <td>{{ associationDisplay(cell.association_status) }}</td>
              <td class="detail-cell" @click.stop>
                <details>
                  <summary>Consultar</summary>
                  <div class="cell-detail">
                    <article class="object-detail">
                      <h6>Membrana {{ displayValue(cell.membrane_id) }}</h6>
                      <span>ID origen: {{ displayValue(cell.source_raw_id) }}</span>
                      <dl class="metrics-list">
                        <div
                          v-for="metric in metricRows(cell.metrics)"
                          :key="metric.key"
                        >
                          <dt>{{ metric.label }}</dt>
                          <dd>{{ metric.value }}</dd>
                        </div>
                      </dl>
                    </article>

                    <article class="object-detail">
                      <h6>Nucleos asociados</h6>
                      <p
                        v-if="!objectList(cell.nuclei).length"
                        class="empty-detail"
                      >
                        Sin nucleos asociados.
                      </p>
                      <div
                        v-for="(nucleus, nucleusIndex) in objectList(cell.nuclei)"
                        :key="objectKey(nucleus, nucleusIndex, 'nucleus')"
                        class="nested-object"
                      >
                        <strong>Nucleo {{ displayValue(nucleus.id) }}</strong>
                        <span>ID origen: {{ displayValue(nucleus.source_raw_id) }}</span>
                        <span>Asociacion: {{ associationDisplay(nucleus.association_status) }}</span>
                        <dl class="metrics-list">
                          <div
                            v-for="metric in metricRows(nucleus.metrics)"
                            :key="metric.key"
                          >
                            <dt>{{ metric.label }}</dt>
                            <dd>{{ metric.value }}</dd>
                          </div>
                        </dl>
                      </div>
                    </article>

                    <article class="object-detail">
                      <h6>Micronucleos asociados</h6>
                      <p
                        v-if="!objectList(cell.micronuclei).length"
                        class="empty-detail"
                      >
                        Sin micronucleos asociados.
                      </p>
                      <div
                        v-for="(micronucleus, micronucleusIndex) in objectList(cell.micronuclei)"
                        :key="objectKey(micronucleus, micronucleusIndex, 'micronucleus')"
                        class="nested-object"
                      >
                        <strong>{{ displayValue(micronucleus.display_label) }}</strong>
                        <span>ID: {{ displayValue(micronucleus.id) }}</span>
                        <span>ID origen: {{ displayValue(micronucleus.source_raw_id) }}</span>
                        <span>Nucleo asociado: {{ displayValue(micronucleus.nucleus_id) }}</span>
                        <span>Asociacion: {{ associationDisplay(micronucleus.association_status) }}</span>
                        <dl class="metrics-list">
                          <div
                            v-for="metric in metricRows(micronucleus.metrics, true)"
                            :key="metric.key"
                          >
                            <dt>{{ metric.label }}</dt>
                            <dd>{{ metric.value }}</dd>
                          </div>
                        </dl>
                      </div>
                    </article>
                  </div>
                </details>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <p
        v-else
        class="empty-section"
      >
        La caracterizacion no contiene celulas.
      </p>
    </section>

    <section class="result-section">
      <div class="section-heading">
        <div>
          <h4>Objetos no asociados y ambiguos</h4>
          <p>Objetos que requieren revision del contexto de segmentacion.</p>
        </div>
      </div>

      <div
        v-if="specialGroupsWithItems.length"
        class="special-groups"
      >
        <details
          v-for="group in specialGroupsWithItems"
          :key="group.key"
          class="special-group"
        >
          <summary>
            <span>{{ group.title }}</span>
            <strong>{{ group.items.length }}</strong>
          </summary>
          <div class="special-object-grid">
            <article
              v-for="(item, itemIndex) in group.items"
              :key="objectKey(item, itemIndex, group.key)"
              class="object-detail"
            >
              <h6>{{ group.objectName }} {{ displayValue(item.id) }}</h6>
              <span>ID origen: {{ displayValue(item.source_raw_id) }}</span>
              <span>Asociacion: {{ associationDisplay(item.association_status) }}</span>
              <span v-if="group.ambiguous">
                Membranas candidatas: {{ candidateMembranesDisplay(item) }}
              </span>
              <dl class="metrics-list">
                <div
                  v-for="metric in metricRows(item.metrics, group.micronucleus)"
                  :key="metric.key"
                >
                  <dt>{{ metric.label }}</dt>
                  <dd>{{ metric.value }}</dd>
                </div>
              </dl>
            </article>
          </div>
        </details>
      </div>
      <p
        v-else
        class="empty-section"
      >
        No hay objetos no asociados ni ambiguos.
      </p>
    </section>

    <section class="result-section">
      <div class="section-heading">
        <div>
          <h4>Advertencias</h4>
          <p>Advertencias estructuradas generadas por el backend.</p>
        </div>
        <span class="section-count">{{ warnings.length }}</span>
      </div>

      <div
        v-if="warningGroups.length"
        class="warning-groups"
      >
        <article
          v-for="group in warningGroups"
          :key="group.code"
          class="warning-group"
        >
          <header>
            <strong>{{ group.code }}</strong>
            <span>{{ group.items.length }}</span>
          </header>
          <ul>
            <li
              v-for="(warning, warningIndex) in group.items"
              :key="warningKey(warning, warningIndex)"
            >
              <p>{{ displayValue(warning.message) }}</p>
              <div class="warning-context">
                <span>Objeto: {{ displayValue(warning.object_id) }}</span>
                <span
                  v-for="context in warningContext(warning)"
                  :key="context.key"
                >
                  {{ context.label }}: {{ context.value }}
                </span>
              </div>
            </li>
          </ul>
        </article>
      </div>
      <p
        v-else
        class="empty-section"
      >
        Sin advertencias para esta caracterizacion.
      </p>
    </section>
  </div>
</template>

<script>
import {
  displayValue,
  formatGenotoxicityPercentage,
  formatNumber,
} from "../../domain/characterizationPresentation";

const STATUS_LABELS = {
  VALID: "Valido",
  PARTIAL: "Parcial",
  NOT_COMPUTABLE: "No calculable",
};

const ASSOCIATION_LABELS = {
  ASSOCIATED: "Asociado",
  UNASSOCIATED: "No asociado",
  AMBIGUOUS: "Ambiguo",
};

const NUCLEAR_CLASS_LABELS = {
  ANUCLEATED: "Anucleada",
  MONONUCLEATED: "Mononucleada",
  BINUCLEATED: "Binucleada",
  TRINUCLEATED: "Trinucleada",
  MULTINUCLEATED: "Multinucleada",
};

export default {
  name: "SalivaMorphometricResult",
  emits: ["select-cell"],
  props: {
    selectedCellId: {
      type: [Number, String],
      default: null,
    },
    resultJson: {
      type: Object,
      required: true,
    },
  },

  computed: {
    summary() {
      return this.resultJson.summary && typeof this.resultJson.summary === "object"
        ? this.resultJson.summary
        : {};
    },

    associationQuality() {
      const quality = this.summary.association_quality;
      return quality && typeof quality === "object" ? quality : {};
    },

    cells() {
      return this.objectList(this.resultJson.cells);
    },

    warnings() {
      return this.objectList(this.resultJson.warnings).filter(
        warning => warning && typeof warning === "object"
      );
    },

    primarySummaryRows() {
      return [
        ["total_membranes", "Membranas"],
        ["total_nuclei", "Nucleos"],
        ["total_micronuclei", "Micronucleos"],
        ["cells_with_nucleus", "Celulas con nucleo"],
        ["cells_with_2plus_micronuclei", "Celulas con 2 o mas micronucleos"],
      ].map(([key, label]) => ({
        key,
        label,
        value: displayValue(this.summary[key]),
      }));
    },

    nuclearClassRows() {
      return [
        ["anucleated_cells", "Anucleadas"],
        ["mononucleated_cells", "Mononucleadas"],
        ["binucleated_cells", "Binucleadas"],
        ["trinucleated_cells", "Trinucleadas"],
        ["multinucleated_cells", "Multinucleadas"],
      ].map(([key, label]) => ({
        key,
        label,
        value: displayValue(this.summary[key]),
      }));
    },

    genotoxicityDisplay() {
      return formatGenotoxicityPercentage(this.summary.genotoxicity_index);
    },

    associationRows() {
      return [
        {
          key: "nuclei",
          label: "Nucleos a membrana",
          associated: this.associationQuality.nuclei_associated,
          total: this.associationQuality.nuclei_total,
          rate: this.associationQuality.nuclei_association_rate,
        },
        {
          key: "micronuclei-membrane",
          label: "Micronucleos a membrana",
          associated: this.associationQuality.micronuclei_associated_to_membrane,
          total: this.associationQuality.micronuclei_total,
          rate: this.associationQuality.micronuclei_membrane_association_rate,
        },
        {
          key: "micronuclei-nucleus",
          label: "Micronucleos a nucleo",
          associated: this.associationQuality.micronuclei_associated_to_nucleus,
          total: this.associationQuality.micronuclei_total,
          rate: this.associationQuality.micronuclei_nucleus_association_rate,
        },
      ];
    },

    specialGroups() {
      const unassociated = this.resultJson.unassociated || {};
      const ambiguous = this.resultJson.ambiguous || {};
      return [
        {
          key: "unassociated-nuclei",
          title: "Nucleos no asociados",
          objectName: "Nucleo",
          items: this.objectList(unassociated.nuclei),
          ambiguous: false,
          micronucleus: false,
        },
        {
          key: "unassociated-micronuclei",
          title: "Micronucleos no asociados",
          objectName: "Micronucleo",
          items: this.objectList(unassociated.micronuclei),
          ambiguous: false,
          micronucleus: true,
        },
        {
          key: "ambiguous-nuclei",
          title: "Nucleos ambiguos",
          objectName: "Nucleo",
          items: this.objectList(ambiguous.nuclei),
          ambiguous: true,
          micronucleus: false,
        },
        {
          key: "ambiguous-micronuclei",
          title: "Micronucleos ambiguos",
          objectName: "Micronucleo",
          items: this.objectList(ambiguous.micronuclei),
          ambiguous: true,
          micronucleus: true,
        },
      ];
    },

    specialGroupsWithItems() {
      return this.specialGroups.filter(group => group.items.length);
    },

    warningGroups() {
      const grouped = new Map();
      this.warnings.forEach(warning => {
        const code = warning.code || "WARNING_WITHOUT_CODE";
        if (!grouped.has(code)) grouped.set(code, []);
        grouped.get(code).push(warning);
      });
      return [...grouped.entries()].map(([code, items]) => ({ code, items }));
    },
  },

  methods: {
    scrollCellIntoView(cellId) {
      const container = this.$refs.cellsScroll;
      if (!container) return;
      const row = [...container.querySelectorAll("tbody > tr")].find(
        element => element.dataset.membraneId === String(cellId)
      );
      if (!row) return;
      const bounds = container.getBoundingClientRect();
      const rowBounds = row.getBoundingClientRect();
      const headerHeight = container.querySelector("thead")?.getBoundingClientRect().height || 0;
      const visibleTop = bounds.top + container.clientTop + headerHeight;
      const visibleBottom = bounds.top + container.clientTop + container.clientHeight;
      const offset = rowBounds.top < visibleTop
        ? rowBounds.top - visibleTop
        : rowBounds.bottom > visibleBottom ? rowBounds.bottom - visibleBottom : 0;
      if (offset) {
        // Equivalent to scrollIntoView({ block: 'nearest' }), constrained to
        // the local table; avoids scrolling the page away from the overlay.
        container.scrollTo({ top: container.scrollTop + offset, behavior: "smooth" });
      }
    },

    displayValue,
    formatNumber,

    statusDisplay(status) {
      return STATUS_LABELS[status] || displayValue(status);
    },

    statusClass(status) {
      if (status === "VALID") return "valid";
      if (status === "PARTIAL") return "partial";
      return "not-computable";
    },

    associationDisplay(status) {
      return ASSOCIATION_LABELS[status] || displayValue(status);
    },

    nuclearClassDisplay(nuclearClass) {
      return NUCLEAR_CLASS_LABELS[nuclearClass] || displayValue(nuclearClass);
    },

    objectList(value) {
      return Array.isArray(value) ? value : [];
    },

    cellKey(cell, index) {
      return `cell-${cell?.membrane_id ?? "without-id"}-${index}`;
    },

    objectKey(item, index, prefix) {
      return `${prefix}-${item?.id ?? "without-id"}-${index}`;
    },

    warningKey(warning, index) {
      return `${warning.code || "warning"}-${warning.object_id ?? "general"}-${index}`;
    },

    metricRows(metrics, includeDependencyMetrics = false) {
      const values = metrics && typeof metrics === "object" ? metrics : {};
      const definitions = [
        ["area_px2", "Area", value => formatNumber(value, 2, " px²")],
        ["perimeter_px", "Perimetro", value => formatNumber(value, 2, " px")],
        ["centroid_px", "Centroide", value => this.formatCentroid(value)],
        ["circularity", "Circularidad", value => formatNumber(value, 4)],
        ["mean_gray_intensity", "Intensidad media", value => formatNumber(value, 4)],
      ];

      if (includeDependencyMetrics) {
        definitions.push(
          [
            "distance_to_nucleus_px",
            "Distancia al nucleo",
            value => formatNumber(value, 2, " px"),
          ],
          [
            "area_fraction_to_nucleus",
            "Fraccion de area al nucleo",
            value => formatNumber(value, 4),
          ],
          [
            "intensity_fraction_to_nucleus",
            "Fraccion de intensidad al nucleo",
            value => formatNumber(value, 4),
          ]
        );
      }

      return definitions.map(([key, label, formatter]) => ({
        key,
        label,
        value: formatter(values[key]),
      }));
    },

    formatCentroid(value) {
      if (!Array.isArray(value) || value.length < 2) return "—";
      const x = formatNumber(value[0], 2);
      const y = formatNumber(value[1], 2);
      if (x === "—" || y === "—") return "—";
      return `(${x}, ${y}) px`;
    },

    candidateMembranesDisplay(item) {
      const candidates = item?.candidate_membrane_ids;
      return Array.isArray(candidates) && candidates.length
        ? candidates.join(", ")
        : "—";
    },

    warningContext(warning) {
      const excluded = new Set(["code", "object_id", "message"]);
      return Object.entries(warning)
        .filter(([key]) => !excluded.has(key))
        .map(([key, value]) => ({
          key,
          label: key.replaceAll("_", " "),
          value: this.formatContextValue(value),
        }));
    },

    formatContextValue(value) {
      if (value === null || value === undefined || value === "") return "—";
      if (Array.isArray(value)) return value.length ? value.join(", ") : "—";
      if (typeof value === "object") return JSON.stringify(value);
      return value;
    },
  },
};
</script>

<style scoped>
.morphometric-result,
.result-section {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-width: 0;
}

.result-section {
  border-top: 1px solid #eef2f6;
  padding-top: 16px;
}

.section-heading {
  align-items: flex-start;
  display: flex;
  gap: 12px;
  justify-content: space-between;
}

.section-heading h4 {
  color: #344054;
  font-size: 15px;
  margin: 0 0 3px;
}

.section-heading p {
  color: #667085;
  font-size: 12px;
  margin: 0;
}

.section-heading code {
  color: #475467;
  font-size: 11px;
}

.schema-badge,
.section-count {
  background: #eef4ff;
  border-radius: 999px;
  color: #3b5b8a;
  flex: 0 0 auto;
  font-size: 11px;
  font-weight: 700;
  padding: 5px 9px;
}

.summary-grid {
  display: grid;
  gap: 9px;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
}

.summary-card,
.index-card,
.science-metric-card,
.nuclear-class-panel,
.association-card {
  background: #f8fafc;
  border: 1px solid #e4e7ec;
  border-radius: 8px;
  min-width: 0;
  padding: 12px;
}

.summary-card {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.summary-card span,
.index-card span,
.science-metric-card span {
  color: #667085;
  font-size: 12px;
}

.summary-card strong,
.index-card strong,
.science-metric-card strong {
  color: #1f2937;
  font-size: 18px;
}

.science-grid,
.association-grid {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.index-card {
  align-items: flex-start;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: space-between;
}

.index-card > div {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.index-card small {
  color: #667085;
  flex-basis: 100%;
  font-size: 11px;
  line-height: 1.4;
}

.science-metric-card {
  display: flex;
  flex-direction: column;
  gap: 6px;
  justify-content: center;
}

.science-status {
  border-radius: 999px;
  font-size: 10px !important;
  font-weight: 700;
  padding: 4px 7px;
}

.science-status.valid {
  background: #e8f5e9;
  color: #2e7d32;
}

.science-status.partial {
  background: #fff8e1;
  color: #8a6d1d;
}

.science-status.not-computable {
  background: #eef2f6;
  color: #667085;
}

.nuclear-class-panel h5,
.association-card h5 {
  color: #344054;
  font-size: 13px;
  margin: 0 0 10px;
}

.nuclear-class-grid {
  display: grid;
  gap: 8px;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  margin: 0;
}

.nuclear-class-grid > div {
  background: #ffffff;
  border-radius: 7px;
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: 9px;
}

.nuclear-class-grid dt,
.association-card dt,
.metrics-list dt {
  color: #667085;
  font-size: 11px;
}

.nuclear-class-grid dd,
.association-card dd,
.metrics-list dd {
  color: #344054;
  font-size: 12px;
  font-weight: 700;
  margin: 0;
}

.association-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.association-card dl,
.metrics-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin: 0;
}

.association-card dl > div,
.metrics-list > div {
  align-items: baseline;
  display: flex;
  gap: 8px;
  justify-content: space-between;
}

.association-card .association-rate {
  background: #eef4ff;
  border-radius: 7px;
  margin-top: 2px;
  padding: 8px;
}

.metrics-list dd {
  text-align: right;
}

.evidence-section {
  gap: 0;
}

.table-scroll {
  border: 1px solid #e4e7ec;
  border-radius: 8px;
  max-width: 100%;
  overflow: auto;
}

.cells-table-scroll {
  max-height: 640px;
}

.data-table {
  border-collapse: collapse;
  color: #344054;
  font-size: 12px;
  min-width: 620px;
  width: 100%;
}

.cells-table {
  min-width: 720px;
}

.data-table th {
  background: #f8fafc;
  color: #667085;
  font-size: 10px;
  letter-spacing: 0.04em;
  position: sticky;
  text-align: left;
  text-transform: uppercase;
  top: 0;
  z-index: 1;
}

.data-table th,
.data-table td {
  border-bottom: 1px solid #eef2f6;
  padding: 9px 10px;
  vertical-align: top;
}

.data-table tbody tr:last-child td {
  border-bottom: 0;
}

.detail-cell {
  min-width: 120px;
}

.cells-table tbody > tr {
  cursor: pointer;
}

.cells-table tbody > tr.cell-selected > td {
  background: #eef4ff;
  border-top: 2px solid #1e88e5;
  border-bottom: 2px solid #1e88e5;
}

.cell-select-button {
  background: transparent;
  border: 0;
  color: inherit;
  cursor: pointer;
  font: inherit;
  font-weight: 700;
  padding: 4px;
  text-align: left;
}

.cell-select-button span {
  display: block;
  font-size: 11px;
  margin-top: 4px;
}

.cell-select-button:focus-visible {
  outline: 2px solid #1e88e5;
  outline-offset: 2px;
}

details > summary {
  color: #1e88e5;
  cursor: pointer;
  font-weight: 700;
}

.cell-detail {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(3, minmax(210px, 1fr));
  margin-top: 10px;
  min-width: 700px;
}

.object-detail {
  background: #ffffff;
  border: 1px solid #dde4ee;
  border-radius: 8px;
  color: #475467;
  display: flex;
  flex-direction: column;
  font-size: 11px;
  gap: 7px;
  min-width: 0;
  padding: 10px;
}

.object-detail h6 {
  color: #344054;
  font-size: 12px;
  margin: 0;
}

.nested-object {
  border-top: 1px solid #eef2f6;
  display: flex;
  flex-direction: column;
  gap: 5px;
  padding-top: 8px;
}

.nested-object:first-of-type {
  border-top: 0;
  padding-top: 0;
}

.empty-detail,
.empty-section {
  color: #667085;
  font-size: 12px;
  margin: 0;
}

.empty-section {
  background: #f8fafc;
  border-radius: 8px;
  padding: 12px;
}

.special-groups,
.warning-groups {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.special-group,
.warning-group {
  border: 1px solid #e4e7ec;
  border-radius: 8px;
  overflow: hidden;
}

.special-group > summary {
  align-items: center;
  background: #f8fafc;
  display: flex;
  justify-content: space-between;
  padding: 11px 12px;
}

.special-object-grid {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  padding: 12px;
}

.warning-group header {
  align-items: center;
  background: #fff8e1;
  color: #8a6d1d;
  display: flex;
  justify-content: space-between;
  padding: 9px 12px;
}

.warning-group ul {
  display: flex;
  flex-direction: column;
  gap: 0;
  list-style: none;
  margin: 0;
  padding: 0;
}

.warning-group li {
  border-top: 1px solid #f4ead1;
  padding: 10px 12px;
}

.warning-group li:first-child {
  border-top: 0;
}

.warning-group p {
  color: #684f12;
  font-size: 12px;
  line-height: 1.4;
  margin: 0 0 5px;
}

.warning-context {
  color: #8a6d1d;
  display: flex;
  flex-wrap: wrap;
  font-size: 10px;
  gap: 5px 12px;
}

@media (max-width: 1439px) {
  .science-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .nuclear-class-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 767px) {
  .science-grid,
  .association-grid,
  .special-object-grid {
    grid-template-columns: 1fr;
  }

  .summary-grid,
  .nuclear-class-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 479px) {
  .summary-grid,
  .nuclear-class-grid {
    grid-template-columns: 1fr;
  }
}
</style>
