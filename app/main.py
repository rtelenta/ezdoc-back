from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.templates.router import router as templates_router, PREFIX as templates_prefix
from app.users.router import router as users_router, PREFIX as users_prefix

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
    templates_router, prefix=f"{API_PREFIX}{templates_prefix}", tags=["Templates"]
)

app.include_router(users_router, prefix=f"{API_PREFIX}{users_prefix}", tags=["Users"])


@app.get("/", tags=["Root"])
def read_root():
    return {"message": "Welcome to the Ezdoc API!"}
