from fasthtml.common import *
from make_app import app, PARTIALS_PREFIX, SCRIPTS_PATH, CSS_PATH, ASSETS_PATH
from utility_components.full_pages import Page
from dataclasses import dataclass


def Name(first_name="", last_name=""):
    return Fieldset(id="name")(
        Input(
            cls="form-control mb-3",
            inputmode="text",
            name="first_name",
            placeholder="First Name",
            value=first_name,
        ),
        Input(
            cls="form-control mb-3",
            inputmode="text",
            name="last_name",
            placeholder="First Last",
            value=last_name,
        ),
    )


@app.get("/register")
def register(req: Request):
    return Page(
        req,
        "Register",
        Form(
            Legend("Creating a scheduler account"),
            Input(
                hx_get=app.url_path_for("course_live_search"),
                hx_trigger="search offfocus",
                hx_target="#course_search_results",
                hx_vals={"start_slice": 0},
                id="course_search",
                cls="form-control mb-3",
                placeholder="Marist Email",
                inputmode="text",
                name="email",
            ),
            Name(),
            Input(
                cls="form-control mb-3",
                inputmode="password",
                name="password1",
                placeholder="Password",
            ),
            Input(
                cls="form-control mb-3",
                inputmode="password",
                name="password2",
                placeholder="Confirm Password",
            ),
        ),
    )


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
