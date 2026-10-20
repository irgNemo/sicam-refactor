<template>
  <div class="content">
    
    <!-- HEADER -->
    <header class="page-header">
      <h2>Registro de Datos</h2>
      <div class="header-actions">
        <button class="btn-outline" :disabled="isBusy" @click="limpiarFormularioActivo">
          🗑️ Limpiar
        </button>
      </div>
    </header>

    <!-- TABS -->
    <div class="tabs-container">
      <button 
        class="tab-btn"
        :class="{ active: vistaActiva === 'paciente' }"
        :disabled="isBusy" @click="requestTabChange('paciente')"
      >
        Nuevo Paciente
      </button>
      <button 
        class="tab-btn"
        :class="{ active: vistaActiva === 'caso' }"
        :disabled="isBusy" @click="requestTabChange('caso')"
      >
        Nuevo Caso
      </button>
      <button 
        class="tab-btn"
        :class="{ active: vistaActiva === 'imagenes' }"
        :disabled="isBusy" @click="requestTabChange('imagenes')"
      >
        Agregar Imágenes
      </button>
    </div>

    <!-- CONTENIDO DE LOS TABS -->
    <div class="tab-content">

      <!-- ========== FORMULARIO NUEVO PACIENTE ========== -->
      <div v-if="vistaActiva === 'paciente'" class="form-wrapper">
        <div class="card">
          <div class="card-header">
            <h3>Datos del Paciente</h3>
          </div>
          
          <div class="card-body">
            <form @submit.prevent="crearPaciente">
              <fieldset class="registration-fields" :disabled="isCreatingPatient" :aria-busy="isCreatingPatient">
              <div class="form-grid">
                <div class="form-group">
                  <label>Nombre *</label>
                  <input 
                    v-model="formPaciente.nombre" 
                    type="text" 
                    required
                    placeholder="Nombre"
                  />
                </div>

                <div class="form-group">
                  <label>Apellido *</label>
                  <input 
                    v-model="formPaciente.apellido" 
                    type="text" 
                    required
                    placeholder="Apellido"
                  />
                </div>

                <div class="form-group">
                  <label>Identificación *</label>
                  <input 
                    v-model="formPaciente.identificacion" 
                    type="text" 
                    required
                    placeholder="ID o Cédula"
                  />
                </div>

                <div class="form-group">
                  <label>Fecha de Nacimiento *</label>
                  <input 
                    v-model="formPaciente.fecha_nacimiento" 
                    type="date" 
                    required
                  />
                </div>

                <div class="form-group">
                  <label>Email</label>
                  <input 
                    v-model="formPaciente.email" 
                    type="email"
                    placeholder="correo@ejemplo.com"
                  />
                </div>

                <div class="form-group">
                  <label>Teléfono</label>
                  <input 
                    v-model="formPaciente.telefono" 
                    type="tel"
                    placeholder="3331234567"
                  />
                </div>
              </div>

              <div class="form-actions">
                <button type="submit" class="btn-primary">
                  {{ isCreatingPatient ? 'Registrando...' : '✓ Registrar Paciente' }}
                </button>
              </div>
              </fieldset>
            </form>
          </div>
        </div>
      </div>

      <!-- ========== FORMULARIO NUEVO CASO ========== -->
      <div v-if="vistaActiva === 'caso'" class="form-wrapper">
        <div class="card">
          <div class="card-header">
            <h3>Crear Nuevo Caso</h3>
          </div>
          
          <div class="card-body">
            <form @submit.prevent="crearCaso">
              <fieldset class="registration-fields" :disabled="isCreatingCase" :aria-busy="isCreatingCase">
              <div class="form-group">
                <label>Seleccionar Paciente *</label>
                <select v-model="formCaso.paciente" required>
                  <option value="">-- Seleccione un paciente --</option>
                  <option 
                    v-for="paciente in pacientes" 
                    :key="paciente.id_paciente"
                    :value="paciente.id_paciente"
                  >
                    {{ patientDisplayName(paciente) }} - {{ paciente.identificacion }}
                  </option>
                </select>
              </div>

              <div class="form-group">
                <label>Título del Caso *</label>
                <input 
                  v-model="formCaso.titulo" 
                  type="text" 
                  required
                  placeholder="Ej: Análisis de rutina - Enero 2026"
                />
              </div>

              <div class="form-group">
                <label>Descripción</label>
                <textarea 
                  v-model="formCaso.descripcion" 
                  rows="4"
                  placeholder="Detalles o notas sobre el caso..."
                ></textarea>
              </div>

              <div class="checkbox-wrapper">
                <input 
                  v-model="formCaso.crear_analisis" 
                  type="checkbox" 
                  id="crear_analisis"
                />
                <label for="crear_analisis">Crear análisis automáticamente</label>
              </div>

              <div class="form-actions">
                <button type="submit" class="btn-primary">
                  {{ isCreatingCase ? 'Creando...' : '✓ Crear Caso' }}
                </button>
              </div>
              </fieldset>
            </form>
          </div>
        </div>
      </div>

      <!-- ========== FORMULARIO AGREGAR IMÁGENES ========== -->
      <div v-if="vistaActiva === 'imagenes'" class="form-wrapper">
        <div class="card">
          <div class="card-header">
            <h3>Agregar Imágenes a Caso Existente</h3>
          </div>
          
          <div class="card-body">
            <form @submit.prevent="subirImagenes">
              <fieldset class="registration-fields" :disabled="isUploading" :aria-busy="isUploading">
              <div class="form-group">
                <label>Seleccionar Paciente *</label>
                <select v-model="formImagenes.paciente" required @change="cargarCasosPaciente">
                  <option value="">-- Seleccione un paciente --</option>
                  <option 
                    v-for="paciente in pacientes" 
                    :key="paciente.id_paciente"
                    :value="paciente.id_paciente"
                  >
                    {{ patientDisplayName(paciente) }}
                  </option>
                </select>
              </div>

              <div class="form-group" v-if="formImagenes.paciente">
                <label>Seleccionar Caso *</label>
                <select v-model="formImagenes.caso" :disabled="isLoadingCases" required @change="cargarAnalisisCaso">
                  <option value="">-- Seleccione un caso --</option>
                  <option 
                    v-for="caso in casosDisponibles" 
                    :key="caso.id_caso"
                    :value="caso.id_caso"
                  >
                    {{ caso.titulo }}
                  </option>
                </select>
              </div>

              <p v-if="isLoadingCases" role="status">Cargando casos...</p>
              <button v-if="casesLoadError" type="button" @click="cargarCasosPaciente">Reintentar carga de casos</button>
              <div class="form-group" v-if="formImagenes.caso">
                <label>Seleccionar Análisis *</label>
                <select v-model="formImagenes.analisis" :disabled="isLoadingAnalyses" required @change="resetFilesForContext">
                  <option value="">-- Seleccione un análisis --</option>
                  <option 
                    v-for="analisis in analisisDisponibles" 
                    :key="analisis.id_analisis"
                    :value="analisis.id_analisis"
                  >
                    Análisis #{{ analisis.id_analisis }} - {{ estadoTexto(analisis.estado) }}
                  </option>
                </select>
              </div>

              <p v-if="isLoadingAnalyses" role="status">Cargando análisis...</p>
              <button v-if="analysesLoadError" type="button" @click="cargarAnalisisCaso">Reintentar carga de análisis</button>
              <div class="form-group" v-if="formImagenes.analisis">
                <label>Tipo de muestra *</label>
                <select v-model="formImagenes.tipoMuestra" required @change="resetFilesForContext">
                  <option
                    v-for="tipo in sampleTypeOptions"
                    :key="tipo.sampleType"
                    :value="tipo.sampleType"
                  >
                    {{ tipo.displayName }}
                  </option>
                </select>
              </div>

              <div class="form-group" v-if="formImagenes.analisis">
                <label>Seleccionar Imágenes *</label>
                <input 
                  type="file" 
                  multiple 
                  accept="image/*"
                  @change="onFileChange"
                  ref="fileInput"
                  class="file-input"
                />
                <p class="help-text">Puede seleccionar múltiples imágenes</p>
              </div>

              <!-- PREVIEW DE IMÁGENES -->
              <div v-if="imagenesPreview.length > 0" class="preview-section">
                <label>Vista Previa ({{ imagenesPreview.length }} imagen{{ imagenesPreview.length > 1 ? 'es' : '' }})</label>
                <div class="preview-grid">
                  <div 
                    v-for="(img, index) in imagenesPreview" 
                    :key="index"
                    class="preview-item"
                  >
                    <img v-if="!img.previewUnavailable" :src="img.url" :alt="`Preview ${index}`" @error="img.previewUnavailable = true" />
                    <span v-else>Vista previa no disponible</span>
                    <button 
                      type="button" 
                      class="remove-btn"
                      @click="removerImagen(index)"
                      title="Eliminar"
                    >
                      ✕
                    </button>
                  </div>
                </div>
              </div>

              <ul v-if="imagenesPreview.length" class="upload-results" aria-live="polite">
                <li v-for="(img, index) in imagenesPreview" :key="index">
                  {{ img.archivo.name }} — {{ uploadStatusText(img.status) }}
                  <span v-if="img.error">: {{ img.error }}</span>
                </li>
              </ul>
              <div class="form-actions">
                <button 
                  type="submit" 
                  class="btn-primary"
                  :disabled="isUploading || pendingUploads.length === 0 || !formImagenes.analisis"
                >
                  {{ isUploading ? 'Subiendo...' : `⬆ Subir/reintentar ${pendingUploads.length} imagen(es) de ${selectedSampleTypeDisplayName}` }}
                </button>
              </div>
              </fieldset>
            </form>
          </div>
        </div>
      </div>

    </div>

    <!-- NOTIFICACIÓN -->
    <transition name="notification-slide">
      <div v-if="notificacion.mostrar" class="notification" :class="notificacion.tipo">
        <span>{{ notificacion.mensaje }}</span>
        <button @click="notificacion.mostrar = false" class="notification-close">✕</button>
      </div>
    </transition>
  </div>
</template>

<script>
import { patientDisplayName } from "../domain/patientPresentation";
import apiClient from '../services/apiClient';
import { registrationErrorMessage } from '../services/registrationErrors';
import {
  SAMPLE_TYPES,
  getSegmentationTypeConfig,
} from '../domain/segmentationTypes';

export default {
  name: 'RegistroView',

  data() {
    return {
      vistaActiva: 'paciente',
      isCreatingPatient: false,
      isCreatingCase: false,
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
        telefono: ''
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
    isBusy() {
      return this.isCreatingPatient || this.isCreatingCase || this.isUploading;
    },
    pendingUploads() {
      return this.imagenesPreview.filter(item => ['PENDING', 'ERROR'].includes(item.status));
    },
    hasUnsavedWork() {
      return this.isBusy || Object.values(this.formPaciente).some(value => String(value).trim())
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
    patientDisplayName,
    async cargarPacientes() {
      try {
        const response = await apiClient.get('/api/pacientes/');
        if (!this.disposed) this.pacientes = response.data;
      } catch (error) {
        console.error('Error al cargar pacientes:', error);
        this.mostrarNotificacion('Error al cargar pacientes', 'error');
      }
    },

    async cargarCasosPaciente() {
      if (this.isUploading) return;
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
      if (this.isUploading) return;
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
      this.isCreatingPatient = true;
      try {
        const response = await apiClient.post('/api/pacientes/', { ...this.formPaciente });
        this.newlyCreatedPatientId = response.data.id_paciente ?? null;
        this.limpiarFormPaciente();
        this.mostrarNotificacion('Paciente registrado exitosamente', 'success');
        await this.cargarPacientes();
      } catch (error) {
        this.mostrarNotificacion(registrationErrorMessage(error, 'Error al registrar paciente'), 'error');
      } finally { this.isCreatingPatient = false; }
    },

    async crearCaso() {
      if (this.isCreatingCase) return;
      this.isCreatingCase = true;
      const withAnalysis = this.formCaso.crear_analisis;
      const payload = { paciente: this.formCaso.paciente, titulo: this.formCaso.titulo, descripcion: this.formCaso.descripcion };
      try {
        const response = await apiClient.post(withAnalysis ? '/api/casos/crear-con-analisis/' : '/api/casos/', payload);
        this.newlyCreatedCaseId = (withAnalysis ? response.data.caso : response.data).id_caso;
        this.newlyCreatedAnalysisId = withAnalysis ? response.data.analisis.id_analisis : null;
        this.mostrarNotificacion('Caso creado exitosamente', 'success');
        this.limpiarFormCaso();
      } catch (error) {
        this.mostrarNotificacion(registrationErrorMessage(error, 'Error al crear caso'), 'error');
      } finally { this.isCreatingCase = false; }
    },

    async subirImagenes() {
      if (this.isUploading || !this.pendingUploads.length) return;
      if (!this.formImagenes.paciente || !this.formImagenes.caso || !this.formImagenes.analisis
          || this.isLoadingCases || this.isLoadingAnalyses) {
        this.mostrarNotificacion('Seleccione paciente, caso y análisis antes de subir.', 'error');
        return;
      }
      this.isUploading = true;
      const analysisId = this.formImagenes.analisis;
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
            const response = await apiClient.post(endpoint, formData, {
              headers: { 'Content-Type': 'multipart/form-data' },
            });
            item.status = 'SUCCESS'; item.sampleId = response.data.id_muestra;
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
      if (this.isUploading) return;
      const hadPending = this.pendingUploads.length > 0;
      this.clearFiles();
      if (hadPending) this.mostrarNotificacion('La selección de archivos se reinició por cambio de contexto.', 'info');
    },

    onFileChange(event) {
      if (this.isUploading) return;
      const files = Array.from(event.target.files || []);
      this.clearFiles();
      this.formImagenes.archivos = files;
      this.imagenesPreview = files.map(archivo => ({
        archivo, url: URL.createObjectURL(archivo), status: 'PENDING', error: '', previewUnavailable: false,
      }));
    },

    removerImagen(index) {
      if (this.isUploading) return;
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
      const estados = { 0: 'Abierto', 1: 'En Proceso', 2: 'Cerrado' };
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
      this.formPaciente = {
        nombre: '',
        apellido: '',
        identificacion: '',
        fecha_nacimiento: '',
        email: '',
        telefono: ''
      };
    },

    limpiarFormCaso() {
      this.formCaso = {
        paciente: '',
        titulo: '',
        descripcion: '',
        crear_analisis: true
      };
    },

    limpiarFormImagenes() {
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
.registration-fields { border: 0; padding: 0; margin: 0; min-width: 0; }
.upload-results { overflow-wrap: anywhere; font-size: 13px; }
.notification.info { background: #1565c0; }
/* TABS */
.tabs-container {
  display: flex;
  gap: 8px;
  margin-bottom: 15px;
  border-bottom: 2px solid #e0e0e0;
  padding-bottom: 0;
}

.tab-btn {
  background: transparent;
  border: none;
  border-bottom: 3px solid transparent;
  padding: 10px 20px;
  font-size: 14px;
  color: #666;
  cursor: pointer;
  transition: all 0.2s ease;
  margin-bottom: -2px;
}

.tab-btn:hover {
  color: #333;
  background: #f8f9fa;
}

.tab-btn.active {
  color: #1e88e5;
  border-bottom-color: #1e88e5;
  font-weight: 500;
}

/* CONTENIDO */
.tab-content {
  flex: 1;
  overflow-y: auto;
}

.form-wrapper {
  max-width: 900px;
}

.card-body {
  padding: 20px;
}

/* FORMULARIOS */
.form-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 15px;
  margin-bottom: 20px;
}

.form-group {
  margin-bottom: 15px;
}

.form-group label {
  font-size: 12px;
  color: #666;
  margin-bottom: 6px;
  display: block;
  font-weight: 500;
}

.form-group input,
.form-group select,
.form-group textarea {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 14px;
  transition: border-color 0.2s ease;
}

.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
  outline: none;
  border-color: #1e88e5;
}

.form-group textarea {
  resize: vertical;
  font-family: inherit;
}

.checkbox-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 15px 0;
}

.checkbox-wrapper input[type="checkbox"] {
  width: auto;
  cursor: pointer;
}

.checkbox-wrapper label {
  font-size: 13px;
  color: #333;
  cursor: pointer;
  margin: 0;
}

.help-text {
  font-size: 11px;
  color: #999;
  margin-top: 4px;
}

.file-input {
  cursor: pointer;
}

/* ACCIONES */
.form-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  margin-top: 20px;
  padding-top: 15px;
  border-top: 1px solid #e0e0e0;
}

.btn-primary:disabled {
  background: #ccc;
  cursor: not-allowed;
  opacity: 0.6;
}

/* PREVIEW DE IMÁGENES */
.preview-section {
  margin: 20px 0;
}

.preview-section > label {
  font-size: 12px;
  color: #666;
  margin-bottom: 10px;
  display: block;
  font-weight: 500;
}

.preview-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 12px;
  margin-top: 10px;
}

.preview-item {
  position: relative;
  aspect-ratio: 1;
  border-radius: 6px;
  overflow: hidden;
  border: 2px solid #e0e0e0;
  background: #f5f5f5;
}

.preview-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.remove-btn {
  position: absolute;
  top: 6px;
  right: 6px;
  background: rgba(211, 47, 47, 0.9);
  color: white;
  border: none;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  cursor: pointer;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s ease;
}

.remove-btn:hover {
  background: #c62828;
}

/* NOTIFICACIÓN */
.notification {
  position: fixed;
  bottom: 20px;
  right: 20px;
  padding: 12px 20px;
  border-radius: 6px;
  background: #4caf50;
  color: white;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  z-index: 1000;
  display: flex;
  align-items: center;
  gap: 15px;
  max-width: 400px;
}

.notification.error {
  background: #f44336;
}

.notification-close {
  background: transparent;
  border: none;
  color: white;
  font-size: 18px;
  cursor: pointer;
  padding: 0;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0.8;
  transition: opacity 0.2s ease;
}

.notification-close:hover {
  opacity: 1;
}

.notification-slide-enter-active,
.notification-slide-leave-active {
  transition: all 0.3s ease;
}

.notification-slide-enter-from {
  transform: translateX(100%);
  opacity: 0;
}

.notification-slide-leave-to {
  transform: translateY(20px);
  opacity: 0;
}
</style>
