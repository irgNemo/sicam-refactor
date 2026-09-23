import hashlib
from types import SimpleNamespace
from unittest.mock import Mock
import sys

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app import main
from app.services.segmentador import leer_imagen_bytes
from segmentacion_core import seg_pipeline_v2 as pipeline


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(main, "inicializar_modelo", Mock())
    with TestClient(main.app) as client:
        yield client


def test_docs_openapi_and_existing_multipart_contract(client):
    assert client.get("/docs").status_code == 200
    schema = client.get("/openapi.json").json()
    body = schema["paths"]["/segmentar"]["post"]["requestBody"]["content"]
    ref = body["multipart/form-data"]["schema"]["$ref"].split("/")[-1]
    assert schema["components"]["schemas"][ref]["required"] == ["file"]
    assert client.post("/segmentar").status_code == 422


def test_endpoint_returns_three_types_and_repeated_raw_ids(client, monkeypatch):
    masks = {name: np.zeros((80, 80), np.uint16) for name in ("membranas", "nucleos", "micronucleos")}
    masks["membranas"][5:75, 5:75] = 7
    masks["nucleos"][15:25, 15:25] = 7
    masks["nucleos"][35:45, 35:45] = 7
    masks["micronucleos"][55:60, 55:60] = 7
    monkeypatch.setattr(main, "segmentar_pipeline", lambda data: masks)
    response = client.post("/segmentar", files={"file": ("synthetic.png", b"mocked", "image/png")})
    assert response.status_code == 200
    result = response.json()
    assert set(result) == {"objetos"}
    assert [o["tipo"] for o in result["objetos"]] == ["membrana", "nucleo", "nucleo", "micronucleo"]
    for obj in result["objetos"]:
        assert set(obj) == {"id", "tipo", "puntos"}
        assert obj["id"] == 7
        assert all(len(p) == 2 and all(isinstance(v, int) for v in p) for p in obj["puntos"])


def test_decode_rgb_and_reject_invalid_image(client):
    bgr = np.full((8, 12, 3), (10, 20, 30), dtype=np.uint8)
    _, encoded = cv2.imencode(".png", bgr)
    decoded = leer_imagen_bytes(encoded.tobytes())
    assert decoded.shape == (8, 12, 3)
    assert decoded[0, 0].tolist() == [30, 20, 10]
    assert client.post("/segmentar", files={"file": ("bad.png", b"invalid")}).status_code == 400
    assert client.post("/segmentar", files={"file": ("empty.png", b"")}).status_code == 400


def test_fail_before_cellpose_if_version_wrong(monkeypatch):
    monkeypatch.setattr(pipeline, "_modelo_membranas", None)
    monkeypatch.setattr(pipeline, "version", lambda name: "3.1.0")
    with pytest.raises(RuntimeError, match="Cellpose requerido"):
        pipeline.inicializar_modelo()


def test_model_hash_size_and_missing_fail_closed(tmp_path, monkeypatch):
    path = tmp_path / "cpsam"
    with pytest.raises(RuntimeError, match="ausente"):
        pipeline.verificar_artefacto(path)
    path.write_bytes(b"abc")
    with pytest.raises(RuntimeError, match="tamaño"):
        pipeline.verificar_artefacto(path)
    monkeypatch.setattr(pipeline, "MODEL_SIZE", 3)
    with pytest.raises(RuntimeError, match="SHA-256"):
        pipeline.verificar_artefacto(path)
    monkeypatch.setattr(pipeline, "MODEL_SHA256", hashlib.sha256(b"abc").hexdigest())
    pipeline.verificar_artefacto(path)


def test_loader_uses_verified_absolute_cpsam_once(tmp_path, monkeypatch):
    model_path = tmp_path / "cpsam"
    model = SimpleNamespace(pretrained_model=str(model_path))
    constructor = Mock(return_value=model)
    models = SimpleNamespace(MODEL_NAMES=["cpsam"], MODEL_DIR=tmp_path, CellposeModel=constructor)
    monkeypatch.setitem(sys.modules, "cellpose", SimpleNamespace(models=models))
    monkeypatch.setattr(pipeline, "version", lambda name: "4.0.8")
    monkeypatch.setattr(pipeline, "_modelo_membranas", None)
    verify = Mock()
    monkeypatch.setattr(pipeline, "verificar_artefacto", verify)
    pipeline.inicializar_modelo()
    pipeline.inicializar_modelo()
    verify.assert_called_once_with(model_path)
    constructor.assert_called_once_with(pretrained_model=str(model_path), gpu=False)
