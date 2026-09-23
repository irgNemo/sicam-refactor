"""Synthetic regression cases; no model construction, download or clinical data."""
from unittest.mock import Mock

import numpy as np
import pytest
from skimage.draw import disk

from segmentacion_core import seg_pipeline_v2 as pipeline
from segmentacion_core.poligonos import obtener_poligonos_desde_mascara
from segmentacion_core.segmentacion import convertir_resultado


def scene(shape=(512, 512), nuclei=((256, 190), (256, 330)), radius=30):
    image = np.full((*shape, 3), 0.85)
    membrane = np.zeros(shape, dtype=np.uint16)
    membrane[40:-40, 40:-40] = 7
    for center in nuclei:
        rr, cc = disk(center, radius, shape=shape)
        image[rr, cc] = 0.1
    return image, membrane


def test_two_nuclei_share_label_but_produce_two_objects():
    image, membrane = scene()
    nuclei = pipeline.extraer_nucleos_principales(image, membrane)
    assert set(np.unique(nuclei)) == {0, 7}
    objects = obtener_poligonos_desde_mascara(nuclei, "nucleo")
    assert len(objects) == 2
    assert [obj["id"] for obj in objects] == [7, 7]
    assert all(len(obj["puntos"]) >= 3 for obj in objects)


@pytest.mark.parametrize("shape", [(512, 512), (1024, 1024), (320, 768)])
@pytest.mark.parametrize("inference_shape", [(512, 512), (192, 192)])
def test_pipeline_restores_original_shape_and_keeps_labels(monkeypatch, shape, inference_shape):
    image = np.full((*shape, 3), 0.8)
    # diameter=80/resample=False can return masks smaller than the input.
    masks = np.zeros(inference_shape, dtype=np.uint16)
    masks[100:300, 100:300] = 7
    masks[10:15, 10:15] = 13  # <200 pixels: removed before resize
    model = Mock()
    model.eval.return_value = (masks, None, None)
    monkeypatch.setattr(pipeline, "_get_modelo", lambda: model)
    monkeypatch.setattr(pipeline, "extraer_nucleos_principales", lambda img, mem: mem.copy())
    monkeypatch.setattr(pipeline, "extraer_micronucleos", lambda img, mem, nuc: np.zeros_like(mem))
    result = pipeline.segmentar_todo(image)
    for mask in result.values():
        assert mask.shape == shape
        assert mask.dtype == np.uint16
    assert set(np.unique(result["membranas"])) == {0, 7}
    args, kwargs = model.eval.call_args
    assert args[0].shape == (512, 512)
    assert args[0].dtype == np.uint8
    assert kwargs == dict(diameter=80, flow_threshold=0.5, cellprob_threshold=-0.5, resample=False)


def test_anucleated_membrane_is_removed(monkeypatch):
    image, membrane = scene(nuclei=())
    model = Mock()
    model.eval.return_value = (membrane, None, None)
    monkeypatch.setattr(pipeline, "_get_modelo", lambda: model)
    result = pipeline.segmentar_todo(image)
    assert all(not np.any(mask) for mask in result.values())
    assert convertir_resultado(result) == {"objetos": []}


def test_tiny_cell_cannot_have_nucleus():
    image, _ = scene(nuclei=())
    membrane = np.zeros(image.shape[:2], np.uint16)
    membrane[5:10, 5:10] = 7
    assert not np.any(pipeline.extraer_nucleos_principales(image, membrane))


def test_otsu_fallback_preserves_nucleus(monkeypatch):
    image, membrane = scene(nuclei=((256, 256),))
    monkeypatch.setattr(pipeline.skimage.filters, "threshold_multiotsu", Mock(side_effect=ValueError))
    otsu = Mock(return_value=0.4)
    monkeypatch.setattr(pipeline.skimage.filters, "threshold_otsu", otsu)
    assert np.any(pipeline.extraer_nucleos_principales(image, membrane))
    otsu.assert_called_once()


def micronucleus_scene(nucleus_radius, candidate_radius, centers=((200, 180),)):
    image, membrane = scene(nuclei=centers, radius=nucleus_radius)
    nuclei = np.zeros_like(membrane)
    for center in centers:
        nuclei[disk(center, nucleus_radius, shape=membrane.shape)] = 7
    image[disk((350, 350), candidate_radius, shape=membrane.shape)] = 0.1
    return image, membrane, nuclei


@pytest.mark.parametrize("nucleus_radius,candidate_radius,accepted", [
    (60, 22, True),  # within [max(800, area/16), area/3]
    (60, 10, False),  # <800 pixels
    (20, 18, False),  # area/3 <800; no feasible MN interval
    (100, 18, False),  # below the relative area/16 lower bound
    (60, 40, False),  # above the relative area/3 upper bound
])
def test_micronucleus_absolute_and_relative_limits(monkeypatch, nucleus_radius, candidate_radius, accepted):
    # Isolate size/geometry from intensity threshold estimation.
    monkeypatch.setattr(pipeline.skimage.filters, "threshold_multiotsu", lambda *a, **k: [0.3, 0.6])
    image, membrane, nuclei = micronucleus_scene(nucleus_radius, candidate_radius)
    result = pipeline.extraer_micronucleos(image, membrane, nuclei)
    assert bool(np.any(result)) is accepted
    assert set(np.unique(result)).issubset({0, 7})


def test_combined_nuclear_area_affects_micronucleus_limit(monkeypatch):
    monkeypatch.setattr(pipeline.skimage.filters, "threshold_multiotsu", lambda *a, **k: [0.3, 0.6])
    image, membrane, nuclei = micronucleus_scene(25, 18, centers=((180, 180), (260, 180)))
    assert np.any(pipeline.extraer_micronucleos(image, membrane, nuclei))
    nuclei[disk((260, 180), 25, shape=membrane.shape)] = 0
    assert not np.any(pipeline.extraer_micronucleos(image, membrane, nuclei))


def test_no_micronucleus_without_main_nucleus():
    image, membrane, nuclei = micronucleus_scene(60, 22)
    nuclei[:] = 0
    assert not np.any(pipeline.extraer_micronucleos(image, membrane, nuclei))


def test_polygons_discard_degenerate_objects_and_use_xy_coordinates():
    mask = np.zeros((40, 70), np.uint16)
    mask[10:20, 30:50] = 7
    mask[1, 1] = 8
    objects = obtener_poligonos_desde_mascara(mask, "membrana")
    assert len(objects) == 1
    assert objects[0]["id"] == 7
    assert set(map(tuple, objects[0]["puntos"])) == {(30, 10), (49, 10), (49, 19), (30, 19)}
