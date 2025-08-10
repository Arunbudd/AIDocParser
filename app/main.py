import uvicorn
from fastapi import FastAPI
from contextlib import asynccontextmanager
from sqlalchemy import text
from app.db import engine
from app.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup code
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        print("Database connected:", result.scalar() == 1)
    yield


app = FastAPI(lifespan=lifespan)

app.include_router(router)

if __name__ == "__main__":
    uvicorn.run("main:app", port=8010, reload=True)
