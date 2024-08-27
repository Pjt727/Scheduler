from fasthtml.common import *
from make_app import app, PARTIALS_PREFIX, SCRIPTS_PATH, CSS_PATH, ASSETS_PATH
from utility_components.full_pages import Page
from utility_components.messages import Message, MessageKind, MessageStack
from sqlalchemy import select
from dataclasses import dataclass
from models.core import *


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
            Legend("Create a scheduler account"),
            Input(
                hx_post=app.url_path_for("validate_email"),
                # hx_trigger="search, offfocus",
                hx_target="#name",
                id="course_search",
                cls="form-control mb-3",
                placeholder="Marist Email",
                inputmode="text",
                name="email",
            ),
            Name(),
            Input(
                cls="form-control mb-3",
                _type="password",
                name="password1",
                placeholder="Password",
            ),
            Input(
                cls="form-control mb-3",
                _type="password",
                name="password2",
                placeholder="Confirm Password",
            ),
            Button(cls="btn btn-primary", inputmode="submit")("Register"),
        ),
        MessageStack(),
    )


@dataclass
class AccountCreation:
    email: str
    first_name: str
    last_name: str
    password1: str
    password2: str


@app.post("/register")
def make_user(data: AccountCreation):
    same_email = select(Professor.first_name, Professor.last_name).filter(
        Professor.email == data.email
    )
    dupe_email_result = session.execute(same_email).first()
    if dupe_email_result:
        return
    same_name_select = select(Professor.email).filter(
        (Professor.first_name == data.first_name) & (Professor.last_name == data.last_name)
    )
    emaiL_ = select
    pass


@app.post(f"{PARTIALS_PREFIX}/validate_email")
def validate_email(email: str):
    email = email.lower()
    prof_name_select = select(Professor.first_name, Professor.last_name).filter(
        Professor.email == email
    )
    result = session.execute(prof_name_select).first()
    if result is None:
        return (
            Message(
                Div(
                    f"Your Marist email of `{email}` is not recognize. If this is suprising please check your spelling"
                ),
                kind=MessageKind.ERROR,
            ),
            HttpHeader("HX-Reswap", "none"),
        )

    first_name, last_name = result

    return Name(first_name, last_name), Message(
        Div(
            f"Hi {first_name} we recognize your email! Feel free to fix your name if there are mistakes"
        ),
        kind=MessageKind.SUCCESS,
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
