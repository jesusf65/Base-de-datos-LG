from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.api import api_router

def create_application():
    application = FastAPI(
        title="GHL to Gmail",
        version="0.0.1",
        description="Este servicio permite la importacion de datos de contactos de GHL a Gmail.",
        docs_url="/docs", 
        swagger_ui_parameters={
            "defaultModelsExpandDepth": -1, 
            "defaultModelExpandDepth": -1,   
            "docExpansion": "none",
            "persistAuthorization": True,    
            "tryItOutEnabled":True,           
        }
    )

    application.include_router(api_router)
    return application

app = create_application()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Hi, I am Louis - Your app is done & working, if u have problems contact me (luis1233210e@gmail.com)."}