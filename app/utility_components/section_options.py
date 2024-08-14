from fasthtml.common import *

def get_general_section_search(req: Request):
    return Input(
            inputmode="text",
            name="section_query",
            hx_target="#sections",
            hx_get=req.url_for("general_section_search"),
            hx_trigger="input changed delay:300ms, search")

def general_section_search(section_query: str):
    return Li()



