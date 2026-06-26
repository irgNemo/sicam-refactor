# ✅ DEBE SER LO PRIMERO — antes de cualquier import de numpy/torch/cellpose
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.concurrency import run_in_threadpool

from app.routers.segmentacion import router as segmentacion_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Se ejecuta al arrancar y al apagar el servidor.
    La carga del modelo ocurre aquí, una sola vez, en un thread separado
    para no bloquear el event loop de asyncio mientras PyTorch inicializa.
    """
    from segmentacion_core.sicam_master import _obtener_modelo

    print("[main] Precargando modelo Cellpose al iniciar el servidor...")
    await run_in_threadpool(_obtener_modelo)
    print("[main] Modelo listo. Servidor disponible para recibir requests.")

    yield  # ← servidor corriendo

    print("[main] Servidor apagándose.")


app = FastAPI(
    title="Microservicio Segmentación Sangre",
    description="Segmentación de imágenes de sangre para análisis de micronúcleos",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(segmentacion_router, prefix="/api/v1")