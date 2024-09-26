from fastapi import FastAPI
from pylotlight.api.routes import router as api_router
from pylotlight.database.session import create_tables
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from alembic import command
from alembic.config import Config

app = FastAPI(title="Pylot Light")

app.add_middleware(
       CORSMiddleware,
       allow_origins=["*"],  # Allows all origins
       allow_credentials=True,
       allow_methods=["*"],  # Allows all methods
       allow_headers=["*"],  # Allows all headers
   )
app.include_router(api_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)