from fastapi import APIRouter, UploadFile, File, HTTPException
import traceback

from app.services.segmentador import segmentar_pipeline
from app.utils.poligonos import obtener_poligonos_desde_mascara

router = APIRouter()


@router.post("/segmentar")
async def segmentar(file: UploadFile = File(...)):
    try:
        contenido = await file.read()

        resultado = segmentar_pipeline(contenido)

        objetos = []
        objetos += obtener_poligonos_desde_mascara(resultado["membranas"], "membrana")
        objetos += obtener_poligonos_desde_mascara(resultado["nucleos"], "nucleo")
        objetos += obtener_poligonos_desde_mascara(resultado["micronucleos"], "micronucleo")

        return {"objetos": objetos}

    except Exception as e:
        print("\n🔥 ERROR EN SEGMENTACIÓN 🔥")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))