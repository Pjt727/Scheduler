from fasthtml.common import *
from make_app import app, PARTIALS_PREFIX, SCRIPTS_PATH, CSS_PATH, ASSETS_PATH
from utility_components.full_pages import Page
from models.core import *
from sqlalchemy import select


@app.get("/")
def register(req: Request):
    return Page(req, "Home", Div("Hi there"))
