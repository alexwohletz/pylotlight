from fastapi import FastAPI
from pylotlight.api.routes import router as api_router

app = FastAPI(title="Pylot Light")

app.include_router(api_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)