import { computed, ref } from "vue";

function cloneJson(value) {
  return value == null ? value : JSON.parse(JSON.stringify(value));
}

function serializeObjects(objects) {
  return JSON.stringify(objects || []);
}

export function useSegmentationEditor() {
  const editorTool = ref("SELECT");
  const vertexEditMode = ref("MOVE");
  const workingObjects = ref([]);
  const isDraftDirty = ref(false);
  const draftBaselineSignature = ref("");
  const undoStack = ref([]);
  const redoStack = ref([]);
  const manualObjectIdCursor = ref(0);
  const drawingLabel = ref("membrana");
  const draftPolygonPoints = ref([]);
  const selectedDraftPointIndex = ref(null);
  const draftPointDrag = ref(null);
  const selectedVertexIndex = ref(null);
  const invalidDrawMessage = ref("");
  const vertexDrag = ref(null);
  const selectedObjectKey = ref(null);

  const workingSummary = computed(() => {
    const counts = {
      membrana: 0,
      nucleo: 0,
      micronucleo: 0,
    };

    workingObjects.value.forEach(object => {
      if (Object.prototype.hasOwnProperty.call(counts, object.label)) {
        counts[object.label] += 1;
      }
    });

    return {
      counts_by_label: counts,
      total_objects: workingObjects.value.length,
    };
  });

  const selectedObject = computed(() => {
    if (selectedObjectKey.value === null) return null;

    return workingObjects.value.find(
      object => revisionObjectSelectionKey(object) === selectedObjectKey.value
    ) || null;
  });

  const hasPendingDraftWork = computed(
    () => isDraftDirty.value || draftPolygonPoints.value.length > 0
  );

  const canDeleteSelectedVertex = computed(() => {
    const points = selectedObject.value?.geometry?.points;
    return (
      selectedVertexIndex.value !== null &&
      Array.isArray(points) &&
      points.length > 3
    );
  });

  function maxRevisionObjectId(objects) {
    return objects.reduce((maxId, object) => {
      const objectId = Number(object?.id);
      return Number.isInteger(objectId) && objectId > maxId ? objectId : maxId;
    }, 0);
  }

  function nextRevisionObjectId() {
    const usedIds = new Set(
      workingObjects.value
        .map(object => Number(object?.id))
        .filter(objectId => Number.isInteger(objectId) && objectId > 0)
    );
    let candidate = Math.max(
      manualObjectIdCursor.value,
      maxRevisionObjectId(workingObjects.value)
    ) + 1;

    while (usedIds.has(candidate)) {
      candidate += 1;
    }

    manualObjectIdCursor.value = candidate;
    return candidate;
  }

  function revisionObjectSelectionKey(object) {
    return `revision-${object.id}`;
  }

  function findWorkingObjectIndexByKey(selectionKey) {
    return workingObjects.value.findIndex(
      object => revisionObjectSelectionKey(object) === selectionKey
    );
  }

  function findWorkingObjectIndexById(objectId) {
    return workingObjects.value.findIndex(object => object.id === objectId);
  }

  function updateDraftDirtyState() {
    isDraftDirty.value =
      serializeObjects(workingObjects.value) !== draftBaselineSignature.value;
  }

  function clearTransientEditorState() {
    draftPolygonPoints.value = [];
    selectedDraftPointIndex.value = null;
    draftPointDrag.value = null;
    selectedVertexIndex.value = null;
    invalidDrawMessage.value = "";
    vertexDrag.value = null;
    selectedObjectKey.value = null;
  }

  function resetEditor() {
    editorTool.value = "SELECT";
    vertexEditMode.value = "MOVE";
    workingObjects.value = [];
    isDraftDirty.value = false;
    draftBaselineSignature.value = "";
    undoStack.value = [];
    redoStack.value = [];
    manualObjectIdCursor.value = 0;
    clearTransientEditorState();
  }

  function loadRevisionSnapshot(revision) {
    const objects = Array.isArray(revision?.resultado_editado?.objects)
      ? revision.resultado_editado.objects
      : [];

    workingObjects.value = cloneJson(objects);
    draftBaselineSignature.value = serializeObjects(workingObjects.value);
    isDraftDirty.value = false;
    undoStack.value = [];
    redoStack.value = [];
    clearTransientEditorState();
    manualObjectIdCursor.value = maxRevisionObjectId(workingObjects.value);
  }

  function buildEditableSnapshot(baseSnapshot = {}) {
    return {
      ...cloneJson(baseSnapshot || {}),
      objects: cloneJson(workingObjects.value),
    };
  }

  function updateWorkingObjectAt(index, updater) {
    if (index < 0) return;

    const nextObjects = cloneJson(workingObjects.value);
    nextObjects[index] = updater(nextObjects[index]);
    workingObjects.value = nextObjects;
  }

  function buildModifiedProvenance(provenance) {
    return {
      ...(cloneJson(provenance) || {}),
      modified: true,
    };
  }

  function applyVertexMove(objectId, vertexIndex, point, provenance) {
    const objectIndex = findWorkingObjectIndexById(objectId);
    if (objectIndex < 0) return;

    updateWorkingObjectAt(objectIndex, object => {
      const points = Array.isArray(object.geometry?.points)
        ? cloneJson(object.geometry.points)
        : [];
      if (!points[vertexIndex]) return object;

      points[vertexIndex] = cloneJson(point);

      return {
        ...object,
        geometry: {
          ...object.geometry,
          points,
        },
        provenance: cloneJson(provenance || object.provenance),
      };
    });
  }

  function applyVertexPointsSnapshot(objectId, points, provenance) {
    const objectIndex = findWorkingObjectIndexById(objectId);
    if (objectIndex < 0 || !Array.isArray(points)) return;

    updateWorkingObjectAt(objectIndex, object => ({
      ...object,
      geometry: {
        ...object.geometry,
        points: cloneJson(points),
      },
      provenance: cloneJson(provenance || object.provenance),
    }));
  }

  function applyRevisionOperation(operation) {
    const object = cloneJson(operation.object);

    if (operation.type === "CREATE_OBJECT") {
      const index = Math.min(
        Math.max(operation.index, 0),
        workingObjects.value.length
      );
      workingObjects.value.splice(index, 0, object);
      selectedObjectKey.value = revisionObjectSelectionKey(object);
    }

    if (operation.type === "DELETE_OBJECT") {
      workingObjects.value = workingObjects.value.filter(
        item => item.id !== object.id
      );
      if (selectedObjectKey.value === revisionObjectSelectionKey(object)) {
        selectedObjectKey.value = null;
        selectedVertexIndex.value = null;
      }
    }

    if (operation.type === "MOVE_VERTEX") {
      applyVertexMove(
        operation.objectId,
        operation.vertexIndex,
        operation.after,
        operation.provenanceAfter
      );
    }

    if (["INSERT_VERTEX", "DELETE_VERTEX"].includes(operation.type)) {
      applyVertexPointsSnapshot(
        operation.objectId,
        operation.afterPoints,
        operation.provenanceAfter
      );
      selectedVertexIndex.value = operation.selectedVertexIndexAfter ?? null;
    }

    updateDraftDirtyState();
  }

  function revertRevisionOperation(operation) {
    const object = cloneJson(operation.object);

    if (operation.type === "CREATE_OBJECT") {
      workingObjects.value = workingObjects.value.filter(
        item => item.id !== object.id
      );
      if (selectedObjectKey.value === revisionObjectSelectionKey(object)) {
        selectedObjectKey.value = null;
        selectedVertexIndex.value = null;
      }
    }

    if (operation.type === "DELETE_OBJECT") {
      const index = Math.min(
        Math.max(operation.index, 0),
        workingObjects.value.length
      );
      workingObjects.value.splice(index, 0, object);
    }

    if (operation.type === "MOVE_VERTEX") {
      applyVertexMove(
        operation.objectId,
        operation.vertexIndex,
        operation.before,
        operation.provenanceBefore
      );
    }

    if (["INSERT_VERTEX", "DELETE_VERTEX"].includes(operation.type)) {
      applyVertexPointsSnapshot(
        operation.objectId,
        operation.beforePoints,
        operation.provenanceBefore
      );
      selectedVertexIndex.value = operation.selectedVertexIndexBefore ?? null;
    }

    updateDraftDirtyState();
  }

  function pushUndoOperation(operation) {
    undoStack.value.push(cloneJson(operation));
    redoStack.value = [];
    updateDraftDirtyState();
  }

  function undoRevisionEdit() {
    const operation = undoStack.value.pop();
    if (!operation) return;

    revertRevisionOperation(operation);
    redoStack.value.push(cloneJson(operation));
  }

  function redoRevisionEdit() {
    const operation = redoStack.value.pop();
    if (!operation) return;

    applyRevisionOperation(operation);
    undoStack.value.push(cloneJson(operation));
  }

  function beginVertexDrag(handle, pointerData) {
    const objectIndex = findWorkingObjectIndexById(handle.objectId);
    const object = workingObjects.value[objectIndex];
    const beforePoint = object?.geometry?.points?.[handle.vertexIndex];
    if (!beforePoint) return false;

    selectedVertexIndex.value = handle.vertexIndex;
    vertexDrag.value = {
      objectId: handle.objectId,
      vertexIndex: handle.vertexIndex,
      ...pointerData,
      before: cloneJson(beforePoint),
      after: cloneJson(beforePoint),
      provenanceBefore: cloneJson(object.provenance),
      provenanceAfter: buildModifiedProvenance(object.provenance),
    };
    return true;
  }

  function updateVertexDrag(point) {
    if (!vertexDrag.value) return;

    vertexDrag.value.after = cloneJson(point);
    applyVertexMove(
      vertexDrag.value.objectId,
      vertexDrag.value.vertexIndex,
      point,
      vertexDrag.value.provenanceAfter
    );
    updateDraftDirtyState();
  }

  function finishVertexDrag() {
    if (!vertexDrag.value) return null;

    const operation = {
      type: "MOVE_VERTEX",
      objectId: vertexDrag.value.objectId,
      vertexIndex: vertexDrag.value.vertexIndex,
      before: cloneJson(vertexDrag.value.before),
      after: cloneJson(vertexDrag.value.after),
      provenanceBefore: cloneJson(vertexDrag.value.provenanceBefore),
      provenanceAfter: cloneJson(vertexDrag.value.provenanceAfter),
    };
    const changed =
      serializeObjects([operation.before]) !== serializeObjects([operation.after]);

    vertexDrag.value = null;

    if (changed) {
      pushUndoOperation(operation);
    } else {
      updateDraftDirtyState();
    }

    return { changed, operation };
  }

  function cancelVertexDragState() {
    if (!vertexDrag.value) return false;

    applyVertexMove(
      vertexDrag.value.objectId,
      vertexDrag.value.vertexIndex,
      vertexDrag.value.before,
      vertexDrag.value.provenanceBefore
    );
    vertexDrag.value = null;
    updateDraftDirtyState();
    return true;
  }

  function insertVertexInSelectedObject(segment, point) {
    const object = selectedObject.value;
    if (!object) return false;

    const beforePoints = Array.isArray(object.geometry?.points)
      ? cloneJson(object.geometry.points)
      : [];
    if (beforePoints.length < 3) return false;

    const insertIndex = segment.endIndex === 0
      ? beforePoints.length
      : segment.startIndex + 1;
    const afterPoints = [
      ...beforePoints.slice(0, insertIndex),
      point,
      ...beforePoints.slice(insertIndex),
    ];
    const provenanceBefore = cloneJson(object.provenance);
    const provenanceAfter = buildModifiedProvenance(object.provenance);
    const selectedVertexIndexBefore = selectedVertexIndex.value;

    applyVertexPointsSnapshot(object.id, afterPoints, provenanceAfter);
    selectedObjectKey.value = revisionObjectSelectionKey(object);
    selectedVertexIndex.value = insertIndex;
    pushUndoOperation({
      type: "INSERT_VERTEX",
      objectId: object.id,
      vertexIndex: insertIndex,
      point: cloneJson(point),
      beforePoints,
      afterPoints,
      provenanceBefore,
      provenanceAfter,
      selectedVertexIndexBefore,
      selectedVertexIndexAfter: insertIndex,
    });
    return true;
  }

  function deleteSelectedVertex() {
    if (!canDeleteSelectedVertex.value || !selectedObject.value) return;

    const object = selectedObject.value;
    const beforePoints = cloneJson(object.geometry.points);
    const point = cloneJson(beforePoints[selectedVertexIndex.value]);
    const afterPoints = beforePoints.filter(
      (_item, index) => index !== selectedVertexIndex.value
    );
    const selectedVertexIndexBefore = selectedVertexIndex.value;
    const selectedVertexIndexAfter = Math.min(
      selectedVertexIndexBefore,
      afterPoints.length - 1
    );
    const provenanceBefore = cloneJson(object.provenance);
    const provenanceAfter = buildModifiedProvenance(object.provenance);

    cancelVertexDragState();
    applyVertexPointsSnapshot(object.id, afterPoints, provenanceAfter);
    selectedVertexIndex.value = selectedVertexIndexAfter;
    pushUndoOperation({
      type: "DELETE_VERTEX",
      objectId: object.id,
      vertexIndex: selectedVertexIndexBefore,
      point,
      beforePoints,
      afterPoints,
      provenanceBefore,
      provenanceAfter,
      selectedVertexIndexBefore,
      selectedVertexIndexAfter,
    });
  }

  function beginDraftPointDrag(index, pointerData) {
    const beforePoint = draftPolygonPoints.value[index];
    if (!beforePoint) return false;

    selectedDraftPointIndex.value = index;
    draftPointDrag.value = {
      index,
      ...pointerData,
      before: cloneJson(beforePoint),
      after: cloneJson(beforePoint),
      didDrag: false,
    };
    return true;
  }

  function updateDraftPointAt(index, point) {
    if (index < 0 || index >= draftPolygonPoints.value.length) return;

    const nextPoints = cloneJson(draftPolygonPoints.value);
    nextPoints[index] = cloneJson(point);
    draftPolygonPoints.value = nextPoints;
    invalidDrawMessage.value = "";
  }

  function updateDraftPointDrag(point, didDrag) {
    if (!draftPointDrag.value) return;

    if (didDrag) {
      draftPointDrag.value.didDrag = true;
    }
    draftPointDrag.value.after = cloneJson(point);
    updateDraftPointAt(draftPointDrag.value.index, point);
  }

  function finishDraftPointDrag() {
    if (!draftPointDrag.value) return null;

    const drag = cloneJson(draftPointDrag.value);
    draftPointDrag.value = null;
    return drag;
  }

  function cancelDraftPointDragState() {
    if (!draftPointDrag.value) return false;

    updateDraftPointAt(draftPointDrag.value.index, draftPointDrag.value.before);
    draftPointDrag.value = null;
    return true;
  }

  function deleteSelectedDraftPoint() {
    if (selectedDraftPointIndex.value === null) return;
    if (
      selectedDraftPointIndex.value < 0 ||
      selectedDraftPointIndex.value >= draftPolygonPoints.value.length
    ) {
      selectedDraftPointIndex.value = null;
      return;
    }

    cancelDraftPointDragState();
    draftPolygonPoints.value = draftPolygonPoints.value.filter(
      (_point, index) => index !== selectedDraftPointIndex.value
    );
    selectedDraftPointIndex.value = null;
    invalidDrawMessage.value = "";
  }

  function insertDraftPoint(insertIndex, point) {
    draftPolygonPoints.value = [
      ...draftPolygonPoints.value.slice(0, insertIndex),
      point,
      ...draftPolygonPoints.value.slice(insertIndex),
    ];
    selectedDraftPointIndex.value = insertIndex;
    invalidDrawMessage.value = "";
  }

  function appendDraftPoint(point) {
    draftPolygonPoints.value = [
      ...draftPolygonPoints.value,
      point,
    ];
    selectedDraftPointIndex.value = draftPolygonPoints.value.length - 1;
    invalidDrawMessage.value = "";
  }

  function finishDraftPolygon() {
    if (draftPolygonPoints.value.length < 3) return null;
    cancelDraftPointDragState();

    const newObject = {
      id: nextRevisionObjectId(),
      label: drawingLabel.value,
      geometry: {
        type: "polygon",
        points: cloneJson(draftPolygonPoints.value),
      },
      provenance: {
        origin: "manual",
        base_object_id: null,
      },
    };
    const index = workingObjects.value.length;

    workingObjects.value = [
      ...workingObjects.value,
      newObject,
    ];
    draftPolygonPoints.value = [];
    selectedDraftPointIndex.value = null;
    invalidDrawMessage.value = "";
    selectedObjectKey.value = revisionObjectSelectionKey(newObject);
    pushUndoOperation({
      type: "CREATE_OBJECT",
      object: newObject,
      index,
    });

    return newObject;
  }

  function cancelDraftPolygon() {
    cancelDraftPointDragState();
    draftPolygonPoints.value = [];
    selectedDraftPointIndex.value = null;
    invalidDrawMessage.value = "";
  }

  function deleteSelectedObject() {
    if (!selectedObjectKey.value) return;

    const index = findWorkingObjectIndexByKey(selectedObjectKey.value);
    if (index < 0) return;

    cancelVertexDragState();
    const object = cloneJson(workingObjects.value[index]);
    workingObjects.value.splice(index, 1);
    selectedObjectKey.value = null;
    selectedVertexIndex.value = null;
    pushUndoOperation({
      type: "DELETE_OBJECT",
      object,
      index,
    });
  }

  function selectObject(selectionKey) {
    selectedVertexIndex.value = null;
    selectedObjectKey.value =
      selectedObjectKey.value === selectionKey ? null : selectionKey;
  }

  function selectObjectVertex(selectionKey, nearestVertexIndex) {
    const changedObject = selectedObjectKey.value !== selectionKey;
    selectedObjectKey.value = selectionKey;

    if (nearestVertexIndex !== null) {
      selectedVertexIndex.value = nearestVertexIndex;
    } else if (changedObject) {
      selectedVertexIndex.value = null;
    }
  }

  function clearSelection() {
    selectedObjectKey.value = null;
    selectedVertexIndex.value = null;
  }

  return {
    editorTool,
    vertexEditMode,
    workingObjects,
    isDraftDirty,
    draftBaselineSignature,
    undoStack,
    redoStack,
    manualObjectIdCursor,
    drawingLabel,
    draftPolygonPoints,
    selectedDraftPointIndex,
    draftPointDrag,
    selectedVertexIndex,
    invalidDrawMessage,
    vertexDrag,
    selectedObjectKey,
    workingSummary,
    selectedObject,
    hasPendingDraftWork,
    canDeleteSelectedVertex,
    cloneJson,
    serializeObjects,
    revisionObjectSelectionKey,
    findWorkingObjectIndexByKey,
    findWorkingObjectIndexById,
    updateDraftDirtyState,
    resetEditor,
    loadRevisionSnapshot,
    loadWorkingRevision: loadRevisionSnapshot,
    buildEditableSnapshot,
    buildModifiedProvenance,
    applyVertexMove,
    applyVertexPointsSnapshot,
    applyRevisionOperation,
    revertRevisionOperation,
    pushUndoOperation,
    undoRevisionEdit,
    redoRevisionEdit,
    beginVertexDrag,
    updateVertexDrag,
    finishVertexDrag,
    cancelVertexDragState,
    insertVertexInSelectedObject,
    deleteSelectedVertexEdit: deleteSelectedVertex,
    beginDraftPointDrag,
    updateDraftPointAt,
    updateDraftPointDrag,
    finishDraftPointDrag,
    cancelDraftPointDragState,
    deleteSelectedDraftPointEdit: deleteSelectedDraftPoint,
    insertDraftPoint,
    appendDraftPoint,
    finishDraftPolygonEdit: finishDraftPolygon,
    cancelDraftPolygonEdit: cancelDraftPolygon,
    deleteSelectedObjectEdit: deleteSelectedObject,
    selectObject,
    selectObjectVertex,
    clearSelection,
  };
}
