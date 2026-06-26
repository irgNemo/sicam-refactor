from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.concurrency import run_in_threadpool
import traceback

from app.services.segmentador import segmentar_pipeline
from app.utils.poligonos import obtener_poligonos_desde_mascara

router = APIRouter()


@router.post("/segmentar")
async def segmentar(file: UploadFile = File(...)):
    """
    Recibe una imagen de sangre y retorna los polígonos
    de células y micronúcleos detectados.

    El procesamiento (Cellpose + DBSCAN) corre en un thread separado
    via run_in_threadpool para no bloquear el event loop de asyncio.
    Esto permite que múltiples requests del cliente lleguen sin que
    uno bloquee a los demás mientras procesa.

    Returns:
        {
            "objetos": [
                { "id": 1, "tipo": "membrana",      "puntos": [[x,y], ...] },
                { "id": 1, "tipo": "micronucleo",  "puntos": [[x,y], ...] }
            ]
        }
    """
    try:
        contenido = await file.read()

        # run_in_threadpool: corre la función síncrona pesada en un thread
        # del pool de Uvicorn, liberando el event loop para otros requests.
        resultado = await run_in_threadpool(segmentar_pipeline, contenido)

        objetos = []
        objetos += obtener_poligonos_desde_mascara(resultado["celulas"],      "membrana")
        objetos += obtener_poligonos_desde_mascara(resultado["micronucleos"], "micronucleo")

        return {"objetos": objetos}

    except Exception as e:
        print("\n ERROR EN SEGMENTACIÓN SANGRE")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))