from fasthtml.common import *
from make_app import app, PARTIALS_PREFIX, SCRIPTS_PATH, CSS_PATH, ASSETS_PATH
from utility_components.full_pages import Page
from utility_components.messages import Message, MessageKind, MessageStack
from sqlalchemy import select
from dataclasses import dataclass
from models.users import *
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


def RegisterSubmit(is_force=False):
    return (
        Button(
            id="submitRegister",
            hx_swap_oob="true",
            cls=f"btn { "btn-warning" if is_force else "btn-primary" }",
            inputmode="submit",
            hx_vals={"force": is_force},
        )("Register Anyways" if is_force else "Register"),
    )


@app.get("/register")
def register(req: Request):
    return Page(
        req,
        "Register",
        Form(hx_post=app.url_path_for("make_user"))(
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
            RegisterSubmit(),
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
    force: bool


@app.post("/register")
def make_user(data: AccountCreation):
    email = data.email.lower()
    same_email = select(User).filter(User.email == email)
    dupe_user = session.scalar(same_email)
    # there is already a user email as registered
    if dupe_user:
        return Message(
            Div(
                f"That email is already an existing user under {dupe_user.professor.first_name} {dupe_user.professor.last_name}"
            ),
            kind=MessageKind.ERROR,
        )

    # allow users to assume the professor of unlinked professors with the same name
    if not data.force:
        similar_name_select = (
            select(Professor)
            .join(Professor)
            .filter(
                Professor.first_name.like(f"%{data.first_name}%")
                & Professor.last_name.like(f"%{data.last_name}%")
                & Professor.user
                == None
            )
        )
        # TODO: implement this selection
        similiar_profs = session.scalars(similar_name_select)

    if data.password1 != data.password2 or not data.password1:
        # the password would only be none of someone hacked the request
        #   so idk that the error message is bad
        return Message(Div(f"Your passwords do not match"), kind=MessageKind.ERROR)
    # checking password complexity
    if not data.force:
        reason, is_complex = User.password_is_complex(data.password1)
        if not is_complex:
            return Message(
                Div(
                    f"Your password is not very complex are you sure you want to coninue with this password? {reason}"
                ),
                MessageKind.WARNING,
            ), RegisterSubmit(True)
    select_exisiting_professor = select(Professor).filter(
        Professor.email == email, Professor.user == None
    )
    exisiting_professor = session.scalar(select_exisiting_professor)
    message = "Your account is linked to your teaching history"
    if exisiting_professor is None:
        exisiting_professor = Professor()
        session.add(exisiting_professor)
        message = "A new professor instance is made for your account"
    exisiting_professor.first_name = data.first_name
    exisiting_professor.last_name = data.last_name
    exisiting_professor.email = email

    user = User(
        email=email, password=User.hash_password(data.password1), professor=exisiting_professor
    )
    session.add(user)
    session.commit()
    return Message(
        Div(f"A Scheduler account already exists under the email {email}! Try logging in."),
        kind=MessageKind.ERROR,
    ), HttpHeader("HX-Redirect", app.get_url_for("home"))


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
