from fastapi import APIRouter

router = APIRouter()

PREFIX = "/templates"


@router.get("/render")
def render_template():
    return {"message": "Welcome to the Ezdoc API!"}
