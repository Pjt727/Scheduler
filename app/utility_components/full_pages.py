from fasthtml.common import *
from starlette.requests import Request
from make_app import app, ASSETS_PATH


def Page(req: Request, title: str, *c):
    nav_pairs = [("Search", app.url_path_for("search"))]
    nav_items = [
        A(
            href=url,
            cls="nav-link",
            aria_current="page" if url == req.url.path else None,
        )(name)
        for name, url in nav_pairs
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
