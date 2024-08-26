from fasthtml.common import *
from make_app import app, PARTIALS_PREFIX, SCRIPTS_PATH, CSS_PATH, ASSETS_PATH
from utility_components.full_pages import Page


@app.get("/login")
def login(req: Request):
    return Page(
        req,
        "Login",
        Input(
            hx_get=app.url_path_for("course_live_search"),
            hx_trigger="search offfocus",
            hx_target="#course_search_results",
            hx_vals={"start_slice": 0},
            id="course_search",
            cls="form-control",
            placeholder="Marist Email",
            inputmode="text",
            name="course_query",
        ),
    )

@app.get
