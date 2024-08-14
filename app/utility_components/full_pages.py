from fasthtml.common import *
from starlette.requests import Request
def Page(req: Request, title: str, *c):
    nav_items = [('Search', '/search')]
    nav_as =[Li(A(name, href=url, aria_current="page" if url == req.url.path else None))
            for name, url in nav_items]
    return (
            Title(title),
            Header(Nav(
                Ul(Strong(A("Marist Scheduler", href="/"))),
                Ul(*nav_as),
                ), cls="container"),
            Hr(),
            Body(Container(*c))
            )
