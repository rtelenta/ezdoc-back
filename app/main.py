from fastapi import FastAPI
from app.routers import templates
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Ezdoc API",
    description="Ezdoc API for managing documents.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

API_PREFIX = "/api"

app.include_router(
    templates.router, prefix=f"{API_PREFIX}{templates.PREFIX}", tags=["Templates"]
)


@app.get("/", tags=["Root"])
def read_root():
    return {"message": "Welcome to the Ezdoc API!"}
