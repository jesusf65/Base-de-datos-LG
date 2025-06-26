from app.core.database import engine
from fastapi import APIRouter    
router = APIRouter()


@router.get("/db-healthcheck")
def test_connection():
    try:
        with engine.begin() as conn:
            print("✅ Conexión exitosa a PostgreSQL")
    except Exception as e:
        print("❌ Error de conexión:", e)
    return "✅ Conexión exitosa a PostgreSQL"