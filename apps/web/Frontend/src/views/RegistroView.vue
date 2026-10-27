<template>
  <main class="registration-content" aria-labelledby="registration-title">
    <div class="registration-shell">
      <header class="page-header">
        <h2 id="registration-title">Registro de datos</h2>
        <p>Gestión de pacientes, casos e imágenes.</p>
      </header>
      <nav class="registration-nav mode-selector" aria-label="Modo de Registro">
        <button type="button" :class="{active:recordMode === 'new'}" :aria-pressed="recordMode === 'new'" :disabled="isBusy" @click="requestMode('new')">Nuevo registro</button>
        <button type="button" :class="{active:recordMode === 'manage'}" :aria-pressed="recordMode === 'manage'" :disabled="isBusy" @click="requestMode('manage')">Gestionar registros</button>
      </nav>
      <RecordManagement v-if="recordMode === 'manage'" @busy="lifecycleBusy = $event" @dirty="managementDirty = $event" @changed="cargarPacientes" />
      <div v-show="recordMode === 'new'">
      <p v-if="!can('register')">Acceso de consulta. Puede consultar pacientes y casos desde Segmentación y Caracterización.</p>
      <section v-if="!can('register')" aria-label="Pacientes de la institución"><h3>Pacientes</h3><ul><li v-for="patient in pacientes" :key="patient.id_paciente">{{ patientRegistrationLabel(patient) }}</li></ul></section>
      <nav v-if="can('register')" class="registration-nav" aria-label="Secciones de Registro">
        <button v-for="tab in [{ key: 'paciente', label: 'Paciente' }, { key: 'caso', label: 'Caso' }, { key: 'imagenes', label: 'Imágenes' }]"
          :key="tab.key" type="button" :class="{ active: vistaActiva === tab.key }"
          :aria-current="vistaActiva === tab.key ? 'page' : undefined" :disabled="isBusy"
          @click="requestTabChange(tab.key)">{{ tab.label }}</button>
      </nav>

      <section v-if="can('register') && vistaActiva === 'paciente'" class="registration-card" aria-labelledby="patient-title">
        <header class="card-header">
          <h3 id="patient-title">Nuevo paciente</h3>
          <p>Los campos con * son obligatorios.</p>
        </header>
        <form @submit.prevent="crearPaciente">
          <InstitutionSelect v-model="patientInstitution" />
          <fieldset class="registration-fields" :disabled="isCreatingPatient" :aria-busy="isCreatingPatient">
            <legend class="sr-only">Datos del paciente</legend>
            <div class="card-body">
              <fieldset class="sample-types identity-types">
                <legend>Tipo de registro</legend>
                <div class="sample-type-options">
                  <label v-for="mode in [{ value: 'IDENTIFIED', label: 'Identificado' }, { value: 'PSEUDONYMIZED', label: 'Pseudonimizado' }]"
                    :key="mode.value" :for="`patient-mode-${mode.value}`" :class="{ selected: patientIdentityMode === mode.value }">
                    <input :id="`patient-mode-${mode.value}`" type="radio" name="patient-mode" :value="mode.value"
                      :checked="patientIdentityMode === mode.value" @change="requestPatientMode(mode.value, $event)" />{{ mode.label }}
                  </label>
                </div>
              </fieldset>
              <div class="form-grid">
                <div v-if="patientIdentityMode === 'IDENTIFIED'" class="form-group">
                  <label for="patient-identificacion">Identificación *</label>
                  <input id="patient-identificacion" v-model="formPaciente.identificacion" type="text" required
                    placeholder="ID o cédula"
                    :aria-invalid="Boolean(patientErrors.identificacion)"
                    :aria-describedby="patientErrors.identificacion ? 'patient-identificacion-error' : undefined" />
                  <p v-if="patientErrors.identificacion" id="patient-identificacion-error" class="field-error">{{ patientErrors.identificacion }}</p>
                </div>
                <div v-if="patientIdentityMode === 'PSEUDONYMIZED'" class="form-group">
                  <label for="patient-external_patient_id">ID hospitalario *</label>
                  <input id="patient-external_patient_id" v-model="formPaciente.external_patient_id" type="text" required
                    :aria-invalid="Boolean(patientErrors.external_patient_id)"
                    :aria-describedby="patientErrors.external_patient_id ? 'patient-external_patient_id-error' : undefined" />
                  <p v-if="patientErrors.external_patient_id" id="patient-external_patient_id-error" class="field-error">{{ patientErrors.external_patient_id }}</p>
                </div>
                <div class="form-group">
                  <label for="patient-fecha_nacimiento">Fecha de nacimiento *</label>
                  <input id="patient-fecha_nacimiento" v-model="formPaciente.fecha_nacimiento" type="date" required
                    :max="currentLocalDate()"
                    @change="validateBirthDate" @invalid="validateBirthDate"
                    :aria-invalid="Boolean(patientErrors.fecha_nacimiento)"
                    :aria-describedby="patientErrors.fecha_nacimiento ? 'patient-fecha_nacimiento-error' : undefined" />
                  <p v-if="patientErrors.fecha_nacimiento" id="patient-fecha_nacimiento-error" class="field-error">{{ patientErrors.fecha_nacimiento }}</p>
                </div>
                <div v-if="patientIdentityMode === 'IDENTIFIED'" class="form-group">
                  <label for="patient-nombre">Nombre *</label>
                  <input id="patient-nombre" v-model="formPaciente.nombre" type="text" required
                    placeholder="Nombre"
                    :aria-invalid="Boolean(patientErrors.nombre)"
                    :aria-describedby="patientErrors.nombre ? 'patient-nombre-error' : undefined" />
                  <p v-if="patientErrors.nombre" id="patient-nombre-error" class="field-error">{{ patientErrors.nombre }}</p>
                </div>
                <div v-if="patientIdentityMode === 'IDENTIFIED'" class="form-group">
                  <label for="patient-apellido">Apellido *</label>
                  <input id="patient-apellido" v-model="formPaciente.apellido" type="text" required
                    placeholder="Apellido"
                    :aria-invalid="Boolean(patientErrors.apellido)"
                    :aria-describedby="patientErrors.apellido ? 'patient-apellido-error' : undefined" />
                  <p v-if="patientErrors.apellido" id="patient-apellido-error" class="field-error">{{ patientErrors.apellido }}</p>
                </div>
                <div v-if="patientIdentityMode === 'IDENTIFIED'" class="form-group">
                  <label for="patient-email">Email</label>
                  <input id="patient-email" v-model="formPaciente.email" type="email"
                    placeholder="correo@ejemplo.com"
                    :aria-invalid="Boolean(patientErrors.email)"
                    :aria-describedby="patientErrors.email ? 'patient-email-error' : undefined" />
                  <p v-if="patientErrors.email" id="patient-email-error" class="field-error">{{ patientErrors.email }}</p>
                </div>
                <div v-if="patientIdentityMode === 'IDENTIFIED'" class="form-group">
                  <label for="patient-telefono">Teléfono</label>
                  <input id="patient-telefono" v-model="formPaciente.telefono" type="tel"
                    placeholder="Teléfono"
                    :aria-invalid="Boolean(patientErrors.telefono)"
                    :aria-describedby="patientErrors.telefono ? 'patient-telefono-error' : undefined" />
                  <p v-if="patientErrors.telefono" id="patient-telefono-error" class="field-error">{{ patientErrors.telefono }}</p>
                </div>
                <div v-if="patientIdentityMode === 'PSEUDONYMIZED'" class="form-group">
                  <label for="patient-initials">Iniciales *</label>
                  <input id="patient-initials" v-model="formPaciente.initials" type="text" required
                    :aria-invalid="Boolean(patientErrors.initials)"
                    :aria-describedby="patientErrors.initials ? 'patient-initials-error' : undefined" />
                  <p v-if="patientErrors.initials" id="patient-initials-error" class="field-error">{{ patientErrors.initials }}</p>
                </div>
                <div v-if="patientIdentityMode === 'PSEUDONYMIZED'" class="form-group">
                  <label for="patient-external_id_namespace">Origen / institución *</label>
                  <input id="patient-external_id_namespace" v-model="formPaciente.external_id_namespace" type="text" required
                    :aria-invalid="Boolean(patientErrors.external_id_namespace)"
                    :aria-describedby="patientErrors.external_id_namespace ? 'patient-external_id_namespace-error' : undefined" />
                  <p v-if="patientErrors.external_id_namespace" id="patient-external_id_namespace-error" class="field-error">{{ patientErrors.external_id_namespace }}</p>
                  <p class="help-text">Identificador del sistema o institución de origen.</p>
                </div>
              </div>
              <p v-if="patientErrors.non_field_errors || patientErrors.identity_mode" class="field-error" role="alert">
                {{ patientErrors.non_field_errors || patientErrors.identity_mode }}
              </p>
            </div>
            <footer class="form-actions">
              <button type="button" class="btn-secondary" :disabled="isBusy" @click="limpiarFormularioActivo">Limpiar</button>
              <button type="submit" class="btn-primary">{{ isCreatingPatient ? 'Registrando...' : 'Registrar paciente' }}</button>
            </footer>
          </fieldset>
        </form>
      </section>

      <section v-if="can('register') && vistaActiva === 'caso'" class="registration-card" aria-labelledby="case-title">
        <header class="card-header"><h3 id="case-title">Nuevo caso</h3><p>Asocie el caso a un paciente existente. Los campos con * son obligatorios.</p></header>
        <form @submit.prevent="crearCaso">
          <fieldset class="registration-fields" :disabled="isCreatingCase" :aria-busy="isCreatingCase">
            <legend class="sr-only">Datos del caso</legend>
            <div class="card-body form-stack">
              <div class="form-group">
                <label for="case-patient">Paciente *</label>
                <select id="case-patient" v-model="formCaso.paciente" required :disabled="isLoadingPatients"
                  :aria-invalid="Boolean(caseErrors.paciente || caseErrors.id_paciente_fk)"
                  :aria-describedby="caseErrors.paciente || caseErrors.id_paciente_fk ? 'case-patient-error' : undefined">
                  <option value="">{{ isLoadingPatients ? 'Cargando pacientes...' : 'Seleccione un paciente' }}</option>
                  <option v-for="patient in pacientes" :key="patient.id_paciente" :value="patient.id_paciente">{{ patientRegistrationLabel(patient) }}</option>
                </select>
                <p v-if="isLoadingPatients" class="help-text" role="status">Cargando pacientes...</p>
                <p v-else-if="!pacientes.length" class="help-text">No hay pacientes disponibles.</p>
                <p v-if="formCaso.paciente && formCaso.paciente === newlyCreatedPatientId" class="help-text">Paciente recién registrado.</p>
                <p v-if="caseErrors.paciente || caseErrors.id_paciente_fk" id="case-patient-error" class="field-error">{{ caseErrors.paciente || caseErrors.id_paciente_fk }}</p>
              </div>
              <div class="form-group">
                <label for="case-name">Título *</label>
                <input id="case-name" v-model="formCaso.titulo" type="text" required placeholder="Título del caso"
                  :aria-invalid="Boolean(caseErrors.titulo)" :aria-describedby="caseErrors.titulo ? 'case-name-error' : undefined" />
                <p v-if="caseErrors.titulo" id="case-name-error" class="field-error">{{ caseErrors.titulo }}</p>
              </div>
              <div class="form-group">
                <label for="case-description">Descripción</label>
                <textarea id="case-description" v-model="formCaso.descripcion" rows="4" placeholder="Detalles o notas sobre el caso"
                  :aria-invalid="Boolean(caseErrors.descripcion)" :aria-describedby="caseErrors.descripcion ? 'case-description-error' : undefined"></textarea>
                <p v-if="caseErrors.descripcion" id="case-description-error" class="field-error">{{ caseErrors.descripcion }}</p>
              </div>
              <div class="analysis-option">
                <label for="crear_analisis"><input id="crear_analisis" v-model="formCaso.crear_analisis" type="checkbox" aria-describedby="analysis-help" /> Crear análisis automáticamente</label>
                <p id="analysis-help" class="help-text">Se creará un análisis asociado al nuevo caso.</p>
              </div>
              <p v-if="caseErrors.non_field_errors || caseErrors.id_caso_fk || caseErrors.analisis" class="field-error" role="alert">
                {{ caseErrors.non_field_errors || caseErrors.id_caso_fk || caseErrors.analisis }}
              </p>
            </div>
            <footer class="form-actions">
              <button type="button" class="btn-secondary" :disabled="isBusy" @click="limpiarFormularioActivo">Limpiar</button>
              <button type="submit" class="btn-primary">{{ isCreatingCase ? 'Creando...' : 'Crear caso' }}</button>
            </footer>
          </fieldset>
        </form>
      </section>

      <section v-if="can('register') && vistaActiva === 'imagenes'" class="registration-card" aria-labelledby="images-title">
        <header class="card-header"><h3 id="images-title">Agregar imágenes</h3><p>Seleccione el destino y revise los archivos antes de subirlos.</p></header>
        <form @submit.prevent="subirImagenes">
          <fieldset class="registration-fields" :disabled="isUploading || isCreatingAnalysis || isCreatingSeries" :aria-busy="isUploading || isCreatingAnalysis || isCreatingSeries">
            <legend class="sr-only">Carga de imágenes</legend>
            <div class="card-body form-stack">
              <section class="upload-section" aria-labelledby="context-title">
                <h4 id="context-title">Contexto</h4>
                <div class="context-grid">
                  <div class="form-group">
                    <label for="upload-patient">Paciente *</label>
                    <select id="upload-patient" v-model="formImagenes.paciente" required :disabled="isLoadingPatients" @change="cargarCasosPaciente">
                      <option value="">{{ isLoadingPatients ? 'Cargando pacientes...' : 'Seleccione un paciente' }}</option>
                      <option v-for="patient in pacientes" :key="patient.id_paciente" :value="patient.id_paciente">{{ patientRegistrationLabel(patient) }}</option>
                    </select>
                    <p v-if="isLoadingPatients" class="help-text" role="status">Cargando pacientes...</p>
                    <p v-else-if="!pacientes.length" class="help-text">No hay pacientes disponibles.</p>
                  </div>
                  <div class="form-group">
                    <label for="upload-case">Caso *</label>
                    <select id="upload-case" v-model="formImagenes.caso" required :disabled="!formImagenes.paciente || isLoadingCases" @change="cargarAnalisisCaso">
                      <option value="">{{ isLoadingCases ? 'Cargando casos...' : 'Seleccione un caso' }}</option>
                      <option v-for="caso in casosDisponibles" :key="caso.id_caso" :value="caso.id_caso">{{ caso.titulo }}</option>
                    </select>
                    <p v-if="!formImagenes.paciente" class="help-text">Seleccione un paciente para ver sus casos.</p>
                    <p v-else-if="isLoadingCases" class="help-text" role="status">Cargando casos...</p>
                    <button v-else-if="casesLoadError" type="button" class="btn-secondary retry-btn" @click="cargarCasosPaciente">Reintentar carga de casos</button>
                    <p v-else-if="!casosDisponibles.length" class="help-text">No hay casos disponibles para este paciente.</p>
                  </div>
                  <div class="form-group">
                    <label for="upload-analysis">Análisis *</label>
                    <select id="upload-analysis" v-model="formImagenes.analisis" required :disabled="!formImagenes.caso || isLoadingAnalyses" @change="resetFilesForContext">
                      <option value="">{{ isLoadingAnalyses ? 'Cargando análisis...' : 'Seleccione un análisis' }}</option>
                      <option v-for="analisis in analisisDisponibles" :key="analisis.id_analisis" :value="analisis.id_analisis">Análisis #{{ analisis.id_analisis }} — {{ estadoTexto(analisis.estado) }}</option>
                    </select>
                    <p v-if="!formImagenes.caso" class="help-text">Seleccione un caso para ver sus análisis.</p>
                    <p v-else-if="isLoadingAnalyses" class="help-text" role="status">Cargando análisis...</p>
                    <button v-else-if="analysesLoadError" type="button" class="btn-secondary retry-btn" @click="cargarAnalisisCaso">Reintentar carga de análisis</button>
                    <p v-else-if="!analisisDisponibles.length" class="help-text">No hay análisis disponibles para este caso.</p>
                    <button v-if="canCreateAnalysis || isCreatingAnalysis" type="button" class="btn-secondary"
                      :disabled="isCreatingAnalysis" @click="crearAnalisis">{{ isCreatingAnalysis ? 'Creando análisis...' : 'Crear análisis' }}</button>
                  </div>
                </div>
              </section>
              <AcquisitionSeriesSelector :patient-id="formImagenes.paciente" :disabled="isUploading || isCreatingAnalysis"
                @change="acquisitionChanged" @dirty="seriesDirty = $event" @busy="isCreatingSeries = $event" />
              <fieldset class="sample-types upload-section" :disabled="!formImagenes.analisis || isAnalysisClosed">
                <legend>Tipo de muestra *</legend>
                <div class="sample-type-options">
                  <label v-for="tipo in sampleTypeOptions" :key="tipo.sampleType" :for="`upload-type-${tipo.sampleType}`"
                    :class="{ selected: formImagenes.tipoMuestra === tipo.sampleType }">
                    <input :id="`upload-type-${tipo.sampleType}`" v-model="formImagenes.tipoMuestra" type="radio" name="upload-type"
                      :value="tipo.sampleType" required @change="resetFilesForContext" />{{ tipo.displayName }}
                  </label>
                </div>
              </fieldset>
              <dl v-if="formImagenes.paciente || formImagenes.caso || formImagenes.analisis" class="upload-context" aria-label="Destino de las imágenes">
                <div v-if="formImagenes.paciente"><dt>Paciente</dt><dd>{{ uploadPatient ? patientRegistrationLabel(uploadPatient) : '#' + formImagenes.paciente }}</dd></div>
                <div v-if="formImagenes.caso"><dt>Caso</dt><dd>{{ uploadCase ? uploadCase.titulo : '#' + formImagenes.caso }}</dd></div>
                <div v-if="formImagenes.analisis"><dt>Análisis</dt><dd>#{{ formImagenes.analisis }}</dd></div>
                <div><dt>Serie</dt><dd>{{ selectedAcquisition.series?.label || 'Sin serie' }}</dd></div>
                <div v-if="selectedAcquisition.profile"><dt>Configuración</dt><dd>{{ selectedAcquisition.profile.name }}</dd></div>
                <div v-if="selectedAcquisition.series"><dt>Calibración</dt><dd>{{ selectedAcquisition.calibration?.label || 'Sin calibración física' }}{{ selectedAcquisition.calibration ? ' · ' + selectedAcquisition.calibration.status : '' }}</dd></div>
                <div v-if="uploadAnalysis"><dt>Estado</dt><dd>{{ estadoTexto(uploadAnalysis.estado) }}</dd></div>
                <div v-if="formImagenes.analisis"><dt>Tipo</dt><dd>{{ selectedSampleTypeDisplayName }}</dd></div>
              </dl>
              <p v-if="isAnalysisClosed" class="field-error" role="status">Este análisis está cerrado y no admite nuevas imágenes.</p>
              <section class="upload-section" aria-labelledby="files-title">
                <h4 id="files-title">Archivos</h4>
                <div class="file-picker">
                  <label for="upload-files">Seleccionar imágenes</label>
                  <input id="upload-files" ref="fileInput" class="file-input" type="file" multiple accept="image/*"
                    :disabled="!formImagenes.analisis || isAnalysisClosed" aria-describedby="upload-help" @change="onFileChange" />
                  <p id="upload-help" class="help-text">Puede seleccionar varias imágenes. Cambiar el destino o el tipo reinicia la selección.</p>
                </div>
                <p v-if="!imagenesPreview.length" class="empty-state">No hay archivos seleccionados.</p>
              </section>
              <section v-if="imagenesPreview.length" class="upload-section" aria-labelledby="upload-status-title">
                <h4 id="upload-status-title">Estado de carga <span class="count-badge">{{ imagenesPreview.length }} archivos</span></h4>
                <ul class="preview-grid" aria-live="polite">
                  <li v-for="(img, index) in imagenesPreview" :key="img.url" class="preview-item">
                    <div class="preview-image">
                      <img v-if="!img.previewUnavailable" :src="img.url" :alt="`Vista previa de ${img.archivo.name}`" @error="img.previewUnavailable = true" />
                      <span v-else>Vista previa no disponible</span>
                    </div>
                    <div class="preview-detail">
                      <strong class="file-name">{{ img.archivo.name }}</strong>
                      <span class="status-badge" :class="img.status.toLowerCase()">{{ uploadStatusText(img.status) }}</span>
                      <p v-if="img.dimensions" class="help-text">{{ img.dimensions.width }} × {{ img.dimensions.height }} px</p>
                      <p v-if="img.status !== 'SUCCESS'" class="help-text">{{ resolutionFeedback(img.dimensions, selectedAcquisition.profile) }}</p>
                      <p v-if="img.compatibility" class="help-text">Calibración física: {{ compatibilityText(img.compatibility.status) }}</p>
                      <p v-if="img.error" class="field-error">{{ img.error }}</p>
                    </div>
                    <button type="button" class="remove-btn" :aria-label="`Quitar ${img.archivo.name} de la lista`"
                      title="Quitar de la lista" @click="removerImagen(index)">✕</button>
                  </li>
                </ul>
              </section>
            </div>
            <footer class="form-actions">
              <button type="button" class="btn-secondary" :disabled="isBusy" @click="limpiarFormularioActivo">Limpiar</button>
              <button type="submit" class="btn-primary" :disabled="isUploading || isAnalysisClosed || pendingUploads.length === 0 || !formImagenes.analisis">{{ uploadButtonText }}</button>
            </footer>
          </fieldset>
        </form>
      </section>
      </div>
    </div>
    <transition name="notification-slide">
      <div v-if="notificacion.mostrar" class="notification" :class="notificacion.tipo" :role="notificacion.tipo === 'error' ? 'alert' : 'status'">
        <span>{{ notificacion.mensaje }}</span>
        <button type="button" @click="notificacion.mostrar = false" class="notification-close" aria-label="Cerrar notificación">✕</button>
      </div>
    </transition>
  </main>
</template>

<script>
import { auth, can } from '../services/auth';
import RecordManagement from '../components/registration/RecordManagement.vue';
import InstitutionSelect from '../components/InstitutionSelect.vue';
import { patientRegistrationLabel } from "../domain/patientPresentation";
import apiClient from '../services/apiClient';
import AcquisitionSeriesSelector from '../components/acquisition/AcquisitionSeriesSelector.vue';
import { compatibilityText, resolutionFeedback, readDimensions } from '../services/acquisitionService';
import { registrationErrorMessage, registrationFieldErrors } from '../services/registrationErrors';
import {
  SAMPLE_TYPES,
  getSegmentationTypeConfig,
} from '../domain/segmentationTypes';

export default {
  name: 'RegistroView',
  components: { AcquisitionSeriesSelector, InstitutionSelect, RecordManagement },

  data() {
    return {
      vistaActiva: 'paciente',
      recordMode: 'new', managementDirty: false,
      lifecycleBusy: false,
      patientInstitution: null,
      selectedAcquisition: { series: null, profile: null, calibration: null },
      seriesDirty: false, isCreatingSeries: false,
      patientIdentityMode: 'IDENTIFIED',
      patientIdentityBaseline: 'IDENTIFIED',
      patientErrors: {},
      caseErrors: {},
      isLoadingPatients: false,
      isCreatingPatient: false,
      isCreatingCase: false,
      isCreatingAnalysis: false,
      isUploading: false,
      isLoadingCases: false,
      isLoadingAnalyses: false,
      casesLoadError: false,
      analysesLoadError: false,
      casesGeneration: 0,
      analysesGeneration: 0,
      disposed: false,
      notificationTimer: null,
      newlyCreatedPatientId: null,
      newlyCreatedCaseId: null,
      newlyCreatedAnalysisId: null,

      // Formulario Paciente
      formPaciente: {
        nombre: '',
        apellido: '',
        identificacion: '',
        fecha_nacimiento: '',
        email: '',
        telefono: '',
        initials: '',
        external_id_namespace: '',
        external_patient_id: ''
      },

      // Formulario Caso
      formCaso: {
        paciente: '',
        titulo: '',
        descripcion: '',
        crear_analisis: true
      },

      // Formulario Imágenes
      formImagenes: {
        paciente: '',
        caso: '',
        analisis: '',
        tipoMuestra: SAMPLE_TYPES.SALIVA,
        archivos: []
      },

      // Datos
      pacientes: [],
      casosDisponibles: [],
      analisisDisponibles: [],
      imagenesPreview: [],

      // Notificación
      notificacion: {
        mostrar: false,
        mensaje: '',
        tipo: 'success'
      }
    };
  },

  computed: {
    uploadPatient() {
      return this.pacientes.find(patient => patient.id_paciente === this.formImagenes.paciente);
    },
    uploadCase() {
      return this.casosDisponibles.find(item => item.id_caso === this.formImagenes.caso);
    },
    uploadAnalysis() {
      return this.analisisDisponibles.find(item => item.id_analisis === this.formImagenes.analisis);
    },
    isAnalysisClosed() {
      return Number(this.uploadAnalysis?.estado) === 2;
    },
    canCreateAnalysis() {
      return Boolean(this.uploadCase && this.uploadCase.paciente === this.formImagenes.paciente
        && !this.isBusy && !this.isLoadingCases && !this.isLoadingAnalyses
        && !this.casesLoadError && !this.analysesLoadError && !this.analisisDisponibles.length);
    },
    uploadButtonText() {
      if (this.isUploading) return 'Subiendo...';
      return this.pendingUploads.length && this.pendingUploads.every(item => item.status === 'ERROR')
        ? 'Reintentar fallidos' : 'Subir imágenes';
    },
    isBusy() {
      return this.lifecycleBusy || this.isCreatingPatient || this.isCreatingCase || this.isCreatingAnalysis || this.isUploading || this.isCreatingSeries;
    },
    pendingUploads() {
      return this.imagenesPreview.filter(item => ['PENDING', 'ERROR'].includes(item.status));
    },
    hasUnsavedWork() {
      return this.isBusy || this.managementDirty || this.seriesDirty || this.patientIdentityMode !== this.patientIdentityBaseline || Object.values(this.formPaciente).some(value => String(value).trim())
        || Boolean(this.formCaso.paciente || this.formCaso.titulo.trim() || this.formCaso.descripcion.trim()
          || !this.formCaso.crear_analisis) || this.pendingUploads.length > 0;
    },
    sampleTypeOptions() {
      return [SAMPLE_TYPES.SALIVA, SAMPLE_TYPES.BLOOD].map(sampleType => ({
        sampleType,
        displayName: getSegmentationTypeConfig(sampleType).displayName,
      }));
    },

    selectedSampleTypeDisplayName() {
      return getSegmentationTypeConfig(
        this.formImagenes.tipoMuestra
      ).displayName.toLowerCase();
    },
  },

  mounted() {
    this.cargarPacientes();
    window.addEventListener('beforeunload', this.handleBeforeUnload);
  },

  beforeUnmount() {
    this.disposed = true;
    this.casesGeneration++;
    this.analysesGeneration++;
    clearTimeout(this.notificationTimer);
    window.removeEventListener('beforeunload', this.handleBeforeUnload);
    this.clearFiles();
  },

  methods: {
    requestMode(mode) {
      if (!['new','manage'].includes(mode) || mode === this.recordMode) return;
      if (this.confirmLeave()) this.recordMode = mode;
    },
    async lifecycleChanged() {
      this.formImagenes.paciente = '';
      await this.cargarCasosPaciente();
      await this.cargarPacientes();
    },
    can,
    patientRegistrationLabel,
    compatibilityText,
    resolutionFeedback,
    acquisitionChanged(context) {
      if (this.isUploading) return;
      if (this.selectedAcquisition.series?.id !== context.series?.id) this.resetFilesForContext();
      this.selectedAcquisition = context;
    },
    requestPatientMode(mode, event) {
      const resetRadio = () => {
        if (event?.target?.form) {
          for (const input of event.target.form.querySelectorAll('input[name="patient-mode"]')) {
            input.checked = input.value === this.patientIdentityMode;
          }
        }
      };
      if (this.isCreatingPatient || !['IDENTIFIED', 'PSEUDONYMIZED'].includes(mode)
          || mode === this.patientIdentityMode) { resetRadio(); return; }
      const identified = ['nombre', 'apellido', 'identificacion', 'email', 'telefono'];
      const pseudonymized = ['initials', 'external_id_namespace', 'external_patient_id'];
      const previousFields = this.patientIdentityMode === 'IDENTIFIED' ? identified : pseudonymized;
      if (previousFields.some(field => String(this.formPaciente[field] || '').trim())
          && !window.confirm('Al cambiar el tipo de registro se limpiarán los campos exclusivos de la modalidad actual. ¿Desea cambiar?')) {
        resetRadio();
        return;
      }
      for (const field of [...identified, ...pseudonymized]) this.formPaciente[field] = '';
      this.patientIdentityMode = mode;
      this.patientErrors = {};
    },
    patientPayload() {
      const fields = this.patientIdentityMode === 'PSEUDONYMIZED'
        ? ['initials', 'external_id_namespace', 'external_patient_id', 'fecha_nacimiento']
        : ['nombre', 'apellido', 'identificacion', 'fecha_nacimiento', 'email', 'telefono'];
      const payload = Object.fromEntries(fields.map(field => [field, this.formPaciente[field]]));
      if (auth.user?.is_superuser) payload.institution = this.patientInstitution;
      if (this.patientIdentityMode === 'PSEUDONYMIZED') payload.identity_mode = 'PSEUDONYMIZED';
      return payload;
    },
    currentLocalDate() {
      const now = new Date();
      return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
    },
    validateBirthDate() {
      if (this.formPaciente.fecha_nacimiento > this.currentLocalDate()) {
        this.patientErrors.fecha_nacimiento = 'La fecha de nacimiento no puede ser futura.';
        return false;
      }
      delete this.patientErrors.fecha_nacimiento;
      return true;
    },
    async cargarPacientes() {
      this.isLoadingPatients = true;
      try {
        const response = await apiClient.get('/api/pacientes/');
        if (!this.disposed) this.pacientes = response.data;
      } catch (error) {
        console.error('Error al cargar pacientes:', error);
        this.mostrarNotificacion('Error al cargar pacientes', 'error');
      } finally { this.isLoadingPatients = false; }
    },

    async cargarCasosPaciente() {
      if (this.isUploading || this.isCreatingAnalysis) return;
      this.selectedAcquisition = { series: null, profile: null, calibration: null };
      this.seriesDirty = false;
      const generation = ++this.casesGeneration;
      ++this.analysesGeneration;
      this.formImagenes.caso = '';
      this.formImagenes.analisis = '';
      this.casosDisponibles = [];
      this.analisisDisponibles = [];
      this.isLoadingAnalyses = false;
      this.analysesLoadError = false;
      this.casesLoadError = false;
      this.resetFilesForContext();
      const patientId = this.formImagenes.paciente;
      this.isLoadingCases = Boolean(patientId);
      if (!patientId) return;
      try {
        const response = await apiClient.get(`/api/pacientes/${patientId}/casos/`);
        if (!this.disposed && generation === this.casesGeneration) this.casosDisponibles = response.data;
      } catch {
        if (!this.disposed && generation === this.casesGeneration) {
          this.casesLoadError = true;
          this.mostrarNotificacion('No fue posible cargar los casos. Puede reintentar.', 'error');
        }
      } finally {
        if (!this.disposed && generation === this.casesGeneration) this.isLoadingCases = false;
      }
    },

    async cargarAnalisisCaso() {
      if (this.isUploading || this.isCreatingAnalysis) return;
      const generation = ++this.analysesGeneration;
      this.formImagenes.analisis = '';
      this.analisisDisponibles = [];
      this.analysesLoadError = false;
      this.resetFilesForContext();
      const caseId = this.formImagenes.caso;
      this.isLoadingAnalyses = Boolean(caseId);
      if (!caseId) return;
      try {
        const response = await apiClient.get(`/api/casos/${caseId}/analisis/`);
        if (!this.disposed && generation === this.analysesGeneration) this.analisisDisponibles = response.data;
      } catch {
        if (!this.disposed && generation === this.analysesGeneration) {
          this.analysesLoadError = true;
          this.mostrarNotificacion('No fue posible cargar los análisis. Puede reintentar.', 'error');
        }
      } finally {
        if (!this.disposed && generation === this.analysesGeneration) this.isLoadingAnalyses = false;
      }
    },

    async crearPaciente() {
      if (this.isCreatingPatient) return;
      this.patientErrors = {};
      if (!this.validateBirthDate()) return;
      this.isCreatingPatient = true;
      try {
        const response = await apiClient.post('/api/pacientes/', this.patientPayload());
        this.newlyCreatedPatientId = response.data.id_paciente ?? null;
        this.limpiarFormPaciente();
        this.mostrarNotificacion('Paciente registrado exitosamente', 'success');
        await this.cargarPacientes();
      } catch (error) {
        this.patientErrors = registrationFieldErrors(error);
        this.mostrarNotificacion(registrationErrorMessage(error, 'Error al registrar paciente'), 'error');
      } finally { this.isCreatingPatient = false; }
    },

    async crearCaso() {
      if (this.isCreatingCase) return;
      this.isCreatingCase = true;
      this.caseErrors = {};
      const withAnalysis = this.formCaso.crear_analisis;
      const payload = { paciente: this.formCaso.paciente, titulo: this.formCaso.titulo, descripcion: this.formCaso.descripcion };
      try {
        const response = await apiClient.post(withAnalysis ? '/api/casos/crear-con-analisis/' : '/api/casos/', payload);
        this.newlyCreatedCaseId = (withAnalysis ? response.data.caso : response.data).id_caso;
        this.newlyCreatedAnalysisId = withAnalysis ? response.data.analisis.id_analisis : null;
        this.mostrarNotificacion('Caso creado exitosamente', 'success');
        this.limpiarFormCaso();
      } catch (error) {
        this.caseErrors = registrationFieldErrors(error);
        this.mostrarNotificacion(registrationErrorMessage(error, 'Error al crear caso'), 'error');
      } finally { this.isCreatingCase = false; }
    },

    async crearAnalisis() {
      if (!this.canCreateAnalysis) return;
      const caseId = this.uploadCase.id_caso;
      const patientId = this.uploadCase.paciente;
      const generation = ++this.analysesGeneration;
      const isCurrent = () => !this.disposed && generation === this.analysesGeneration
        && this.formImagenes.caso === caseId && this.formImagenes.paciente === patientId;
      this.isCreatingAnalysis = true;
      try {
        const response = await apiClient.post('/api/analisis/', {
          id_paciente_fk: patientId, id_caso_fk: caseId, estado: 0,
        });
        if (!isCurrent()) return;
        const created = response.data;
        this.newlyCreatedAnalysisId = created.id_analisis;
        this.analisisDisponibles = [created];
        this.formImagenes.analisis = created.id_analisis;
        // Keep the confirmed creation even if the subsequent GET fails.
        this.isLoadingAnalyses = true;
        try {
          const refreshed = await apiClient.get(`/api/casos/${caseId}/analisis/`);
          if (!isCurrent()) return;
          this.analisisDisponibles = refreshed.data.some(item => item.id_analisis === created.id_analisis)
            ? refreshed.data : [...refreshed.data, created];
          this.mostrarNotificacion('Análisis creado y seleccionado.', 'success');
        } catch {
          if (isCurrent()) {
            this.analysesLoadError = true;
            this.mostrarNotificacion('El análisis fue creado. No fue posible actualizar la lista; puede reintentar la carga.', 'info');
          }
        }
      } catch (error) {
        if (isCurrent()) this.mostrarNotificacion(registrationErrorMessage(error, 'No fue posible crear el análisis. Puede reintentar.'), 'error');
      } finally {
        if (isCurrent()) this.isLoadingAnalyses = false;
        this.isCreatingAnalysis = false;
      }
    },

    async subirImagenes() {
      if (this.isUploading || this.isCreatingAnalysis || this.isCreatingSeries || !this.pendingUploads.length) return;
      if (this.isAnalysisClosed) {
        this.mostrarNotificacion('Este análisis está cerrado y no admite nuevas imágenes.', 'error');
        return;
      }
      if (!this.formImagenes.paciente || !this.formImagenes.caso || !this.formImagenes.analisis
          || this.isLoadingCases || this.isLoadingAnalyses) {
        this.mostrarNotificacion('Seleccione paciente, caso y análisis antes de subir.', 'error');
        return;
      }
      this.isUploading = true;
      const analysisId = this.formImagenes.analisis;
      const seriesId = this.selectedAcquisition.series?.id;
      const sampleType = this.formImagenes.tipoMuestra;
      const endpoint = this.formImagenes.tipoMuestra === SAMPLE_TYPES.BLOOD ? '/api/muestras-sangre/' : '/api/muestras/';
      const batch = [...this.pendingUploads];
      try {
        for (const item of batch) {
          if (this.disposed) break;
          item.status = 'UPLOADING'; item.error = '';
          try {
            const formData = new FormData();
            formData.append('imagen', item.archivo);
            formData.append('analisis', analysisId);
            if (seriesId) formData.append('acquisition_series', seriesId);
            const response = await apiClient.post(endpoint, formData, {
              headers: { 'Content-Type': 'multipart/form-data' },
            });
            item.status = 'SUCCESS'; item.sampleId = response.data.id_muestra;
            item.compatibility = response.data.physical_compatibility || { status: 'CHECK_PENDING' };
            if (!response.data.physical_compatibility) try {
              const checked = await apiClient.get(`/api/acquisition-compatibility/${sampleType}/${item.sampleId}/`);
              item.compatibility = checked.data;
            } catch { item.compatibility = { status: 'CHECK_FAILED' }; }
          } catch (error) {
            item.status = 'ERROR';
            item.error = registrationErrorMessage(error, 'No se pudo confirmar la subida.');
          }
        }
        if (!this.disposed) {
          const failed = batch.filter(item => item.status === 'ERROR').length;
          this.mostrarNotificacion(`${batch.filter(item => item.status === 'SUCCESS').length} subida(s); ${failed} con error.`, failed ? 'error' : 'success');
        }
      } finally { this.isUploading = false; }
    },

    clearFiles() {
      const previous = this.imagenesPreview;
      this.imagenesPreview = [];
      this.formImagenes.archivos = [];
      previous.forEach(item => URL.revokeObjectURL(item.url));
      if (this.$refs.fileInput) this.$refs.fileInput.value = '';
    },

    resetFilesForContext() {
      if (this.isUploading || this.isCreatingAnalysis) return;
      const hadPending = this.pendingUploads.length > 0;
      this.clearFiles();
      if (hadPending) this.mostrarNotificacion('La selección de archivos se reinició por cambio de contexto.', 'info');
    },

    onFileChange(event) {
      if (this.isUploading || this.isCreatingAnalysis || this.isAnalysisClosed) return;
      const files = Array.from(event.target.files || []);
      this.clearFiles();
      this.formImagenes.archivos = files;
      this.imagenesPreview = files.map(archivo => ({
        archivo, url: URL.createObjectURL(archivo), status: 'PENDING', error: '', previewUnavailable: false, dimensions: null, compatibility: null,
      }));
      for (const item of this.imagenesPreview) {
        readDimensions(item.url).then(dimensions => {
          if (!this.disposed && this.imagenesPreview.some(current => current.url === item.url)) item.dimensions = dimensions;
        });
      }
    },

    removerImagen(index) {
      if (this.isUploading || this.isCreatingAnalysis) return;
      const [removed] = this.imagenesPreview.splice(index, 1);
      this.formImagenes.archivos.splice(index, 1);
      if (removed) URL.revokeObjectURL(removed.url);
      if (this.$refs.fileInput && !this.imagenesPreview.length) this.$refs.fileInput.value = '';
    },

    uploadStatusText(status) {
      return { PENDING: 'Pendiente', UPLOADING: 'Subiendo...', SUCCESS: 'Subida', ERROR: 'Error' }[status] || status;
    },

    confirmLeave() {
      if (this.isBusy) {
        this.mostrarNotificacion('Espere a que termine la operación en curso.', 'info');
        return false;
      }
      return !this.hasUnsavedWork || window.confirm('Hay trabajo sin guardar en Registro. ¿Desea continuar?');
    },

    requestTabChange(tab) {
      if (tab === this.vistaActiva || !['paciente', 'caso', 'imagenes'].includes(tab)) return;
      if (this.confirmLeave()) this.vistaActiva = tab;
    },

    handleBeforeUnload(event) {
      if (!this.hasUnsavedWork) return;
      event.preventDefault(); event.returnValue = '';
    },

    estadoTexto(estado) {
      const estados = { 0: 'Abierto', 1: 'En proceso', 2: 'Cerrado' };
      return estados[estado] || 'Desconocido';
    },

    mostrarNotificacion(mensaje, tipo = 'success') {
      if (this.disposed) return;
      this.notificacion.mensaje = mensaje;
      this.notificacion.tipo = tipo;
      this.notificacion.mostrar = true;
      
      clearTimeout(this.notificationTimer);
      this.notificationTimer = setTimeout(() => {
        this.notificacion.mostrar = false;
      }, 4000);
    },

    limpiarFormularioActivo() {
      if (this.isBusy) return;
      if (this.vistaActiva === 'paciente') {
        this.limpiarFormPaciente();
      } else if (this.vistaActiva === 'caso') {
        this.limpiarFormCaso();
      } else if (this.vistaActiva === 'imagenes') {
        this.limpiarFormImagenes();
      }
    },

    limpiarFormPaciente() {
      this.patientErrors = {};
      this.patientIdentityBaseline = this.patientIdentityMode;
      this.formPaciente = {
        nombre: '',
        apellido: '',
        identificacion: '',
        fecha_nacimiento: '',
        email: '',
        telefono: '',
        initials: '',
        external_id_namespace: '',
        external_patient_id: ''
      };
    },

    limpiarFormCaso() {
      this.caseErrors = {};
      this.formCaso = {
        paciente: '',
        titulo: '',
        descripcion: '',
        crear_analisis: true
      };
    },

    limpiarFormImagenes() {
      this.selectedAcquisition = { series: null, profile: null, calibration: null };
      this.seriesDirty = false;
      this.casesGeneration++;
      this.analysesGeneration++;
      this.isLoadingCases = false;
      this.isLoadingAnalyses = false;
      this.casesLoadError = false;
      this.analysesLoadError = false;
      this.clearFiles();
      this.formImagenes = {
        paciente: '',
        caso: '',
        analisis: '',
        tipoMuestra: SAMPLE_TYPES.SALIVA,
        archivos: []
      };
      this.imagenesPreview = [];
      this.casosDisponibles = [];
      this.analisisDisponibles = [];
      if (this.$refs.fileInput) {
        this.$refs.fileInput.value = '';
      }
    }
  }
};
</script>

<style scoped>
.registration-nav.mode-selector {width:fit-content;padding:5px;gap:4px;background:#e9eff5;border-radius:12px;border:1px solid #d4dee8}
.registration-nav.mode-selector button {border:0;background:transparent;border-radius:8px}
.registration-nav.mode-selector button.active {background:#fff;color:#1565c0;box-shadow:0 1px 4px #0002}

.registration-content { flex: 1; width: 100%; min-width: 0; padding: 24px; }
.registration-shell { width: 100%; max-width: 960px; margin: 0 auto; }
.page-header { margin-bottom: 24px; }
.page-header h2 { margin: 0 0 8px; font-size: 24px; color: #2c3e50; }
.page-header p, .card-header p { margin: 0; color: #52606d; font-size: 14px; line-height: 1.5; }
.registration-nav { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 16px; }
.registration-nav button { background: #fff; border: 2px solid #d9e2ec; border-radius: 10px; padding: 10px 24px; font-size: 14px; font-weight: 600; color: #52606d; cursor: pointer; }
.registration-nav button.active { background: #e3f2fd; border-color: #1e88e5; color: #1565c0; }
.registration-nav button:hover:not(:disabled) { border-color: #1e88e5; }
.registration-card { background: #fff; border: 1px solid #e4e9ef; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,.06); min-width: 0; }
.card-header { padding: 16px 24px; border-bottom: 2px solid #f0f0f0; background: linear-gradient(to right, #fafbfc, #fff); border-radius: 12px 12px 0 0; }
.card-header h3 { margin: 0 0 8px; font-size: 18px; }
.registration-fields { border: 0; padding: 0; margin: 0; min-width: 0; }
.card-body { padding: 24px; }
.form-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px 24px; }
.form-stack { display: flex; flex-direction: column; gap: 24px; }
.form-group { display: flex; flex-direction: column; gap: 8px; min-width: 0; }
.form-group label, .file-picker > label { font-size: 13px; font-weight: 600; color: #34495e; }
.form-group input, .form-group select, .form-group textarea { width: 100%; min-width: 0; border: 1px solid #bdc9d5; border-radius: 8px; padding: 10px 12px; font-size: 14px; background: white; color: #2c3e50; }
.form-group textarea { resize: vertical; }
.form-group [aria-invalid="true"] { border-color: #c62828; }
:where(input, select, textarea, button):focus-visible { outline: 3px solid #1e88e5; outline-offset: 2px; }
:where(input, select, textarea):disabled { background: #f0f4f8; color: #52606d; cursor: not-allowed; }
.field-error { color: #b71c1c; font-size: 13px; margin: 0; line-height: 1.5; overflow-wrap: anywhere; }
.help-text, .empty-state { color: #52606d; font-size: 13px; line-height: 1.5; margin: 0; }
.form-actions { padding: 16px 24px; border-top: 1px solid #e4e9ef; display: flex; flex-wrap: wrap; justify-content: space-between; gap: 12px; }
.btn-primary, .btn-secondary { border: 2px solid #1e88e5; border-radius: 10px; padding: 10px 16px; font-size: 13px; font-weight: 600; cursor: pointer; }
.btn-primary { background: #1e88e5; color: #fff; }
.btn-primary:hover:not(:disabled) { background: #1976d2; border-color: #1976d2; }
.btn-secondary { background: #fff; border-color: #d9e2ec; color: #34495e; }
.btn-secondary:hover:not(:disabled) { background: #e3f2fd; border-color: #1e88e5; }
button:disabled { opacity: .6; cursor: not-allowed; }
.analysis-option { background: #f8fafc; border: 1px solid #e4e9ef; border-radius: 8px; padding: 16px; }
.analysis-option label { display: flex; align-items: center; gap: 8px; font-size: 14px; font-weight: 600; }
.analysis-option input, .sample-type-options input { accent-color: #1e88e5; }
.analysis-option p { margin-top: 8px; }
.upload-section { display: flex; flex-direction: column; gap: 12px; min-width: 0; }
.upload-section h4 { margin: 0; font-size: 14px; display: flex; flex-wrap: wrap; align-items: center; gap: 8px; }
.context-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; }
.retry-btn { align-self: flex-start; text-align: left; }
.sample-types { margin: 0; padding: 0; border: 0; }
.identity-types { margin-bottom: 16px; }
.sample-types legend { font-size: 14px; font-weight: 600; margin-bottom: 12px; }
.sample-type-options { display: flex; flex-wrap: wrap; gap: 8px; }
.sample-type-options label { display: flex; align-items: center; gap: 8px; border: 2px solid #d9e2ec; border-radius: 8px; padding: 10px 16px; font-size: 14px; cursor: pointer; }
.sample-type-options label.selected { border-color: #1e88e5; background: #e3f2fd; color: #1565c0; }
.sample-types:disabled .sample-type-options label { opacity: .65; cursor: not-allowed; }
.upload-context { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px 24px; background: #f0f4f8; border-radius: 8px; padding: 16px; margin: 0; font-size: 13px; }
.upload-context div { min-width: 0; }
.upload-context dt { color: #52606d; margin-bottom: 4px; }
.upload-context dd { margin: 0; font-weight: 600; overflow-wrap: anywhere; }
.file-picker { display: flex; flex-direction: column; gap: 12px; padding: 16px; border: 1px solid #bdc9d5; border-radius: 8px; background: #fafbfc; }
.file-input { width: 100%; min-width: 0; font-size: 13px; }
.file-input::file-selector-button { background: #fff; border: 1px solid #bdc9d5; border-radius: 8px; padding: 8px 12px; margin-right: 12px; color: #34495e; cursor: pointer; }
.file-input:disabled::file-selector-button { cursor: not-allowed; }
.preview-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 240px), 1fr)); gap: 12px; padding: 0; margin: 0; list-style: none; }
.preview-item { position: relative; display: flex; gap: 12px; align-items: flex-start; border: 1px solid #d9e2ec; border-radius: 8px; padding: 12px; min-width: 0; }
.preview-image { width: 72px; height: 72px; flex: 0 0 72px; border-radius: 6px; overflow: hidden; background: #f0f4f8; display: flex; align-items: center; justify-content: center; }
.preview-image img { width: 100%; height: 100%; object-fit: contain; }
.preview-image span { font-size: 11px; text-align: center; padding: 4px; color: #52606d; }
.preview-detail { display: flex; flex-direction: column; gap: 8px; min-width: 0; padding-right: 24px; }
.file-name { font-size: 13px; overflow-wrap: anywhere; }
.status-badge, .count-badge { align-self: flex-start; padding: 4px 8px; border-radius: 8px; background: #f0f4f8; color: #52606d; font-size: 12px; }
.status-badge.uploading { background: #e3f2fd; color: #1565c0; }
.status-badge.success { background: #e8f5e9; color: #256029; }
.status-badge.error { background: #ffebee; color: #b71c1c; }
.remove-btn { position: absolute; right: 8px; top: 8px; background: #fff; border: 1px solid #d9e2ec; border-radius: 6px; width: 28px; height: 28px; color: #52606d; cursor: pointer; }
.remove-btn:hover:not(:disabled) { color: #b71c1c; border-color: #b71c1c; }
.notification { position: fixed; bottom: 24px; right: 24px; width: max-content; max-width: min(480px, calc(100vw - 32px)); padding: 16px; border: 1px solid #c8e6c9; border-radius: 10px; background: #e8f5e9; color: #256029; box-shadow: 0 2px 8px rgba(0,0,0,.12); z-index: 1000; display: flex; align-items: flex-start; gap: 12px; font-size: 14px; line-height: 1.5; overflow-wrap: anywhere; }
.notification.error { background: #ffebee; border-color: #ffcdd2; color: #b71c1c; }
.notification.info { background: #e3f2fd; border-color: #bbdefb; color: #1565c0; }
.notification-close { background: transparent; border: 0; color: inherit; padding: 0; font-size: 16px; cursor: pointer; }
.notification-slide-enter-active, .notification-slide-leave-active { transition: opacity .2s ease; }
.notification-slide-enter-from, .notification-slide-leave-to { opacity: 0; }
.sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0,0,0,0); white-space: nowrap; border: 0; }
@media (max-width: 767px) {
  .registration-content { padding: 16px; }
  .form-grid, .context-grid { grid-template-columns: minmax(0, 1fr); }
  .card-body, .card-header { padding: 16px; }
  .form-actions { padding: 16px; }
  .registration-nav button { flex: 1; padding: 10px 12px; }
}
@media (max-width: 479px) {
  .form-actions { flex-direction: column; }
  .upload-context { grid-template-columns: minmax(0, 1fr); }
  .notification { right: 16px; bottom: 16px; }
}
</style>
