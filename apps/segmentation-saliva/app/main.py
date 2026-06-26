from fastapi import FastAPI
from app.routers.segmentacion import router as segmentacion_router

app = FastAPI()

app.include_router(segmentacion_router)