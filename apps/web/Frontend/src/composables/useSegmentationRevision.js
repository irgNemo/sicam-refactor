import { ref } from "vue";
import {
  getEffectiveSegmentation,
  getOrCreateSegmentationDraft,
  getSegmentationRevisions,
  updateSegmentationDraft,
  validateRevision,
} from "../services/segmentationRevisionService";

export function useSegmentationRevision() {
  const activeRevision = ref(null);
  const activeRevisionId = ref(null);
  const pendingDraftRevision = ref(null);
  const latestValidatedRevision = ref(null);
  const effectiveSegmentation = ref(null);
  const effectiveSegmentationLoading = ref(false);
  const effectiveSegmentationError = ref("");
  const effectiveSegmentationRequestToken = ref(0);
  const pendingDraftLoading = ref(false);
  const pendingDraftError = ref("");
  const isSavingDraft = ref(false);
  const isValidatingRevision = ref(false);
  const saveDraftError = ref("");
  const saveDraftMessage = ref("");
  const validateRevisionError = ref("");
  const validateRevisionMessage = ref("");
  const revisionLoading = ref(false);
  const revisionError = ref("");
  const activeResultadoId = ref(null);

  function setActiveRevision(revision) {
    activeRevision.value = revision || null;
    activeRevisionId.value = revision?.id_revision_segmentacion || null;
  }

  function findLatestValidatedRevision(revisions) {
    if (!Array.isArray(revisions)) return null;

    return revisions
      .filter(revision => revision.estado === "VALIDADA")
      .sort((a, b) => Number(b.numero_revision) - Number(a.numero_revision))[0] || null;
  }

  function resetRevisionState() {
    activeResultadoId.value = null;
    activeRevision.value = null;
    activeRevisionId.value = null;
    pendingDraftRevision.value = null;
    latestValidatedRevision.value = null;
    effectiveSegmentation.value = null;
    effectiveSegmentationLoading.value = false;
    effectiveSegmentationError.value = "";
    effectiveSegmentationRequestToken.value += 1;
    pendingDraftLoading.value = false;
    pendingDraftError.value = "";
    isSavingDraft.value = false;
    isValidatingRevision.value = false;
    saveDraftError.value = "";
    saveDraftMessage.value = "";
    validateRevisionError.value = "";
    validateRevisionMessage.value = "";
    revisionLoading.value = false;
    revisionError.value = "";
  }

  function clearEffectiveSegmentation() {
    effectiveSegmentation.value = null;
    effectiveSegmentationError.value = "";
    effectiveSegmentationLoading.value = false;
    effectiveSegmentationRequestToken.value += 1;
  }

  function isCurrentResultado(resultadoId) {
    return activeResultadoId.value === resultadoId;
  }

  function ensureRevisionBelongsToResult(resultadoId) {
    if (
      activeRevision.value &&
      activeRevision.value.resultado_segmentacion !== resultadoId
    ) {
      resetRevisionState();
      return false;
    }

    return true;
  }

  async function loadRevisionState(resultadoId) {
    activeResultadoId.value = resultadoId || null;
    pendingDraftRevision.value = null;
    latestValidatedRevision.value = null;
    pendingDraftError.value = "";

    if (!resultadoId) return;

    if (
      activeRevision.value?.resultado_segmentacion === resultadoId &&
      activeRevision.value?.estado === "BORRADOR"
    ) {
      pendingDraftRevision.value = activeRevision.value;
    }

    pendingDraftLoading.value = true;

    try {
      const response = await getSegmentationRevisions(resultadoId);

      if (!isCurrentResultado(resultadoId)) return;

      const revisions = Array.isArray(response.data) ? response.data : [];
      pendingDraftRevision.value =
        revisions.find(revision => revision.estado === "BORRADOR") || null;
      latestValidatedRevision.value = findLatestValidatedRevision(revisions);
    } catch (error) {
      if (isCurrentResultado(resultadoId)) {
        pendingDraftError.value =
          error.response?.data?.error ||
          "No fue posible consultar revisiones pendientes.";
      }
    } finally {
      if (isCurrentResultado(resultadoId)) {
        pendingDraftLoading.value = false;
      }
    }
  }

  async function loadEffectiveSegmentation(resultadoId) {
    activeResultadoId.value = resultadoId || null;
    const requestToken = effectiveSegmentationRequestToken.value + 1;
    effectiveSegmentationRequestToken.value = requestToken;
    effectiveSegmentation.value = null;
    effectiveSegmentationError.value = "";

    if (!resultadoId) {
      effectiveSegmentationLoading.value = false;
      return null;
    }

    effectiveSegmentationLoading.value = true;

    try {
      const response = await getEffectiveSegmentation(resultadoId);

      if (
        !isCurrentResultado(resultadoId) ||
        effectiveSegmentationRequestToken.value !== requestToken
      ) {
        return null;
      }

      effectiveSegmentation.value = response.data || null;
      return effectiveSegmentation.value;
    } catch (error) {
      if (
        isCurrentResultado(resultadoId) &&
        effectiveSegmentationRequestToken.value === requestToken
      ) {
        effectiveSegmentation.value = null;
        effectiveSegmentationError.value =
          error.response?.data?.error ||
          "No fue posible cargar el resultado mostrado.";
      }
      return null;
    } finally {
      if (
        isCurrentResultado(resultadoId) &&
        effectiveSegmentationRequestToken.value === requestToken
      ) {
        effectiveSegmentationLoading.value = false;
      }
    }
  }

  async function getOrCreateDraft(resultadoId) {
    activeResultadoId.value = resultadoId || null;
    revisionError.value = "";

    if (!resultadoId) {
      setActiveRevision(null);
      revisionError.value = "No hay resultado de segmentacion para editar.";
      return null;
    }

    if (
      activeRevision.value &&
      activeRevision.value.resultado_segmentacion === resultadoId &&
      activeRevision.value.estado === "BORRADOR"
    ) {
      pendingDraftRevision.value = activeRevision.value;
      return activeRevision.value;
    }

    revisionLoading.value = true;
    setActiveRevision(null);

    try {
      const response = await getOrCreateSegmentationDraft(resultadoId);

      if (!isCurrentResultado(resultadoId)) return null;

      setActiveRevision(response.data);
      pendingDraftRevision.value = response.data;
      return response.data;
    } catch (error) {
      if (isCurrentResultado(resultadoId)) {
        setActiveRevision(null);
        revisionError.value =
          error.response?.data?.error || "No fue posible cargar el borrador experto.";
      }
      return null;
    } finally {
      if (isCurrentResultado(resultadoId)) {
        revisionLoading.value = false;
      }
    }
  }

  async function saveActiveDraft(snapshot) {
    if (!activeRevisionId.value) return null;

    isSavingDraft.value = true;
    saveDraftError.value = "";
    saveDraftMessage.value = "";
    validateRevisionError.value = "";
    validateRevisionMessage.value = "";

    try {
      const response = await updateSegmentationDraft(
        activeRevisionId.value,
        snapshot
      );

      setActiveRevision(response.data);
      pendingDraftRevision.value = response.data;
      saveDraftMessage.value = "Borrador guardado.";
      return response.data;
    } catch (error) {
      saveDraftError.value =
        error.response?.data?.resultado_editado?.[0] ||
        error.response?.data?.detail ||
        "No fue posible guardar el borrador.";
      return null;
    } finally {
      isSavingDraft.value = false;
    }
  }

  async function validateActiveRevision(resultadoId) {
    if (
      !activeRevisionId.value ||
      activeRevision.value?.estado !== "BORRADOR"
    ) {
      return null;
    }

    isValidatingRevision.value = true;
    validateRevisionError.value = "";
    validateRevisionMessage.value = "";

    try {
      const response = await validateRevision(activeRevisionId.value);

      setActiveRevision(response.data);
      pendingDraftRevision.value = null;
      latestValidatedRevision.value = response.data;
      saveDraftError.value = "";
      saveDraftMessage.value = "";
      validateRevisionMessage.value = "Revisión validada.";

      await loadEffectiveSegmentation(resultadoId);
      await loadRevisionState(resultadoId);
      return response.data;
    } catch (error) {
      const status = error.response?.status;
      validateRevisionError.value =
        status === 409
          ? "La revisión ya no está disponible como BORRADOR."
          : error.response?.data?.error || "No fue posible validar la revisión.";

      if (status === 409) {
        await loadRevisionState(resultadoId);
      }

      return null;
    } finally {
      isValidatingRevision.value = false;
    }
  }

  return {
    activeRevision,
    activeRevisionId,
    pendingDraftRevision,
    latestValidatedRevision,
    effectiveSegmentation,
    effectiveSegmentationLoading,
    effectiveSegmentationError,
    effectiveSegmentationRequestToken,
    pendingDraftLoading,
    pendingDraftError,
    isSavingDraft,
    isValidatingRevision,
    saveDraftError,
    saveDraftMessage,
    validateRevisionError,
    validateRevisionMessage,
    revisionLoading,
    revisionError,
    activeResultadoId,
    setActiveRevision,
    findLatestValidatedRevision,
    resetRevisionState,
    clearEffectiveSegmentation,
    ensureRevisionBelongsToResult,
    loadRevisionState,
    loadPendingDraftRevision: loadRevisionState,
    loadEffectiveSegmentation,
    getOrCreateDraft,
    saveActiveDraft,
    validateActiveRevision,
  };
}
