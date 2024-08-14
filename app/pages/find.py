from fasthtml.common import *
from starlette.requests import Request
from utility_components.full_pages import Page
from make_app import app, PARTIALS_PREFIX

def GeneralSearch(previous_query: str = ""):
    return Input(
            inputmode="text",
            name="section_query",
            style="width: 40%",
            value=previous_query,
            hx_target="#sections",
            hx_get=app.url_path_for("general_section_search"),
            hx_trigger="input changed delay:300ms, search")
 


@app.get("/search")
def search(req: Request):
    contents = Div(GeneralSearch(), GeneralSearch())
    return Page(req, "Search", contents)

@app.get(f"{PARTIALS_PREFIX}/get_general_section_search")
def get_general_section_search(req: Request):
    print(req.url.path)
    return GeneralSearch()

@app.get(f"{PARTIALS_PREFIX}/general_section_search")
def general_section_search(section_query: str):
    return Li()



