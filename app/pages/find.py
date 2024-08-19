from fasthtml.common import *
from starlette.requests import Request
from models.core import *
from utility_components.full_pages import Page
from make_app import app, PARTIALS_PREFIX, SCRIPTS_PATH
from sqlalchemy import select


def SectionOptions(current_tab: str | None = None, professor_id: int | None = None):
    if current_tab is None:
        current_tab = "Multi-course Search"
    tab_items = [
        (
            "Multi-course Search",
            app.url_path_for("get_section_options"),
        ),
        (
            "General Search",
            app.url_path_for("get_section_options"),
        ),
        (
            "Course Attribute Search",
            app.url_path_for("get_section_options"),
        ),
    ]
    tabs = [
        Li(cls="nav-item")(
            A(
                tab_name,
                hx_target="#section_options",
                hx_vals={"tab_name": tab_name},
                hx_get=tab_url if tab_name != current_tab else None,
                aria_current="page" if tab_name == current_tab else None,
                cls="nav-link" + (" active disabled" if tab_name == current_tab else ""),
            )
        )
        for tab_name, tab_url in tab_items
    ]

    if current_tab == "Multi-course Search":
        # todo get the professors OG data
        og_course: list[Course] = []
        pills = [
            (
                Input(value=course.rowid, name="included_course", hidden=True),
                Span(
                    f"{course.subject_code} {course.code}",
                    cls="badge rounded-pill text-bg-secondary",
                ),
            )
            for course in og_course
        ]
        tab_content = Div(cls="row mb-3 justify-content-center")(
            Div(cls="col-sm-8")(
                Input(
                    id="course_search",
                    cls="form-control",
                    placeholder="Course Title or Subject and Number",
                    inputmode="text",
                    name="course_query",
                ),
                Div(id="course_search_results", hidden=True),
                Script("onload(() => liveSearch('course_search', 'course_search_results'))"),
            ),
            Form(cls="")(*pills),
        )
    elif current_tab == "General Search":
        tab_content = Div(cls="row mb-3 justify-content-center")(
            Div(cls="col-sm-8")(
                Input(
                    id="general_search",
                    cls="form-control",
                    inputmode="text",
                    name="general_query",
                    placeholder="Space separated search terms (subject, course, professor)",
                    value="",
                    hx_target="#sections",
                    hx_get=app.url_path_for("general_section_search"),
                    hx_trigger="input changed delay:300ms, search",
                ),
                Div(id="general_search_results", hidden=True),
            )
        )
    elif current_tab == "Course Attribute Search":
        tab_content = Form()
    else:
        raise NotImplemented()

    return Div(id="section_options")(
        Ul(cls="nav nav-tabs")(*tabs), Div(cls="pt-5 border border-top-0")(tab_content)
    )


@app.get("/search")
def search(req: Request):
    return Page(req, "Search", SectionOptions(), Script(File(f"{SCRIPTS_PATH}/search.js")))


@app.get(f"{PARTIALS_PREFIX}/get_section_options")
def get_section_options(tab_name: str):
    return SectionOptions(current_tab=tab_name)


@app.get(f"{PARTIALS_PREFIX}/general_section_search")
def general_section_search(section_query: str):
    return Li()


@app.get(f"{PARTIALS_PREFIX}/course_live_search")
def course_live_search(course_query: str):
    filters = []
    for search_term in course_query.split():
        filters.append(
            Course.name.like(f"%{search_term}%")
            or Course.subject_code.like(f"%{search_term}%")
            or Course.code.like(f"%{search_term}%")
        )
    course_select = select(Course).filter(*filters)
    courses = session.scalars(course_select).all()
    return Ul()(
        *[
            Li(cls="search-option")(f"{course.subject_code} {course.code} - {course.description}")
            for course in courses
        ]
    )
