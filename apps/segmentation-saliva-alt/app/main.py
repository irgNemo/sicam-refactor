"""Independent SALIVA ALT service, deliberately not wired into Django."""
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool

from app.services.segmentador import segmentar_pipeline
from segmentacion_core.seg_pipeline_v2 import inicializar_modelo
from segmentacion_core.segmentacion import convertir_resultado

logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await run_in_threadpool(inicializar_modelo, gpu=False)
    # Serialize CPU inference to bound memory use of the independent service.
    app.state.processing = asyncio.Semaphore(1)
    yield


app = FastAPI(
    title="SICAM SALIVA ALT — Cellpose-SAM",
    version="1.0",
    description="ALT_CPSAM_MORPHOLOGICAL_V1; Cellpose 4.0.8; cpsam; CPU",
    lifespan=lifespan,
)


@app.post("/segmentar")
async def segmentar(file: UploadFile = File(...)):
    """Receive multipart `file`, as in the existing SALIVA API."""
    contenido = await file.read()
    try:
        async with app.state.processing:
            resultado = await run_in_threadpool(segmentar_pipeline, contenido)
            return await run_in_threadpool(convertir_resultado, resultado)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Error en segmentación SALIVA ALT")
        raise HTTPException(status_code=500, detail="Error de segmentación SALIVA ALT") from exc
