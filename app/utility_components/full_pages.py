from fasthtml.common import *
from starlette.requests import Request
from make_app import app, ASSETS_PATH


def Page(req: Request, title: str, *c):
    logged_in_nav = [("Search", app.url_path_for("search"))]
    unauth_nav = [("Login", app.url_path_for("login")), ("Register", app.url_path_for("register"))]

    # uncomment this when fisnihing auth
    logged_in_nav.extend(unauth_nav)
    print(req.url.path)

    nav_items = [
        A(
            href=url,
            cls=f"nav-link {"active" if url == req.url.path else ""}",
            aria_current="page" if url == req.url.path else None,
        )(name)
        for name, url in logged_in_nav
    ]
    nav_options = Div(id="navbarNav", cls="collapse navbar-collapse")(
        Div(cls="navbar-nav")(*nav_items)
    )
    return (
        Title(title),
        Nav(cls="navbar navbar-expand-lg bg-body-tertiary")(
            Div(cls="container-fluid")(
                A(href="/", cls="navbar-brand me-5 align-items-center d-flex")(
                    Img(
                        cls="d-inline-block align-text-top me-2",
                        src=f"{ASSETS_PATH}/marist_logo.png",
                        alt="Logo",
                        width="64",
                        height="64",
                    ),
                    "Scheduler",
                ),
                Button(
                    type="button",
                    data_bs_toggle="collapse",
                    data_bs_target="#navbarNav",
                    aria_controls="navbarNav",
                    aria_expanded="false",
                    aria_label="Toggle navigation",
                    cls="navbar-toggler",
                )(Span(cls="navbar-toggler-icon")),
                nav_options,
            ),
        ),
        Hr(),
        Body(Container(*c)),
    )
