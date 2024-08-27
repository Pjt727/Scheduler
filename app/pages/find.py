from fasthtml.common import *
from sqlalchemy.orm import joinedload
from itertools import groupby, zip_longest
from starlette.requests import Request
from models.core import *
from utility_components.full_pages import Page
from make_app import app, PARTIALS_PREFIX, SCRIPTS_PATH, CSS_PATH, ASSETS_PATH
from sqlalchemy import select
from datetime import datetime
from dataclasses import dataclass, field


def SectionOptions(
    current_tab: str | None = None, professor_id: int | None = None, htmx_request: bool = True
):
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
        og_courses: list[Course] = [Course.get(762)]
        pills = [CoursePill(course) for course in og_courses]
        live_search_script = "liveSearch('course_search', 'course_search_results')"
        tab_content = Div(cls="row mb-3 justify-content-center")(
            Div(cls="col-sm-8 position-relative mb-3")(
                Input(
                    hx_get=app.url_path_for("course_live_search"),
                    hx_trigger="input changed delay:300ms, search",
                    hx_target="#course_search_results",
                    hx_vals={"start_slice": 0},
                    id="course_search",
                    cls="form-control",
                    placeholder="Course Title or Subject and Number",
                    inputmode="text",
                    name="course_query",
                ),
                Table(
                    cls="search-table table table-striped position-absolute scrollable-table",
                    style="top: 105%;",
                )(Tbody(id="course_search_results")),
                Script(
                    live_search_script if htmx_request else f"onload(() => {live_search_script})"
                ),
            ),
            Form(id="included_courses", cls="ms-4")(
                *pills if pills else H3(cls="d-inline")("There are no courses selected.")
            ),
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

    return Div(id="section_options", cls="mb-3")(
        Ul(cls="nav nav-tabs")(*tabs),
        Div(cls="pt-5 border border-top-0 rounded-bottom-2")(tab_content),
    )


def CoursePill(course: Course):
    return H3(cls="d-inline")(
        Span(cls="badge rounded-pill text-bg-primary d-inline-flex align-items-center")(
            f"{course.subject_code} {course.code}",
            Button(
                hx_include="#included_courses",
                hx_target="#included_courses",
                hx_vals={"course_id": course.rowid},
                hx_delete=app.url_path_for("remove_course_pill"),
                type="button",
                aria_label="Close",
                cls="btn-close",
            ),
        ),
        Input(name="included_course", value=course.rowid, hidden=True),
    )


def SectionMeetingTimes(section: Section) -> list:
    meeting_times = []
    meetings = sorted(section.meetings, key=lambda m: (m.display_time))
    meetings_by_group_time = groupby(meetings, key=lambda m: m.display_time)
    for display_time, meetings in meetings_by_group_time:
        days = [meeting.day for meeting in meetings]
        day_labels = [
            Div(cls=f"d-inline p-1 {"bg-secondary" if day[0] in days else ""}")(day[1])
            for day in [
                (Day.MON, "MO"),
                (Day.TUE, "TU"),
                (Day.WED, "WE"),
                (Day.THU, "TH"),
                (Day.FRI, "FR"),
                (Day.SAT, "SA"),
            ]
        ]
        meeting_time = Div(cls="border mt-1")(*day_labels, display_time)
        meeting_times.append(meeting_time)

    return meeting_times


@app.get("/search")
def search(req: Request):
    terms = session.scalars(select(Term).order_by(*Term.recent_order())).all()
    return Page(
        req,
        "Search",
        Div(cls="form-floating")(
            Select(cls="form-select mb-4 w-25", id="term_id")(
                *[Option(f"{term.season} {term.year}", value=term.rowid) for term in terms]
            ),
            Label("Term", _for="term"),
        ),
        SectionOptions(htmx_request=False),
        Table(cls="table table-striped caption-top")(
            Caption(
                "All Matching Sections",
                Img(
                    id="section-spinner",
                    cls="htmx-indicator",
                    src=f"{ASSETS_PATH}/loading.gif",
                    alt="Logo",
                    width="64",
                    height="64",
                ),
            ),
            Thead(
                Tr(
                    Th(cls="col-3")("Course name"),
                    Th(cls="col-2")("Course abbreviation"),
                    Th(cls="col-2")("Professor"),
                    Th(cls="col-4")("Meeting Times"),
                ),
            ),
            Tbody(
                id="sections",
                hx_indicator="#section-spinner",
                hx_get=app.url_path_for("search_sections"),
                hx_include="#section_options, #term_id",
                hx_vals={"start_slice": 0},
                hx_trigger="updateSections from:body, load",
            ),
        ),
        Script(File(f"{SCRIPTS_PATH}/search.js")),
        StyleX(f"{CSS_PATH}/search.css"),
    )


@app.get(f"{PARTIALS_PREFIX}/get_section_options")
def get_section_options(tab_name: str):
    return (
        SectionOptions(current_tab=tab_name),
        HttpHeader("HX-Trigger-After-Settle", "updateSections"),
    )


@app.get(f"{PARTIALS_PREFIX}/course_live_search")
def course_live_search(course_query: str, start_slice: int):
    filters = []
    for search_term in course_query.split():
        filters.append(
            Course.name.like(f"%{search_term}%")
            | Course.subject_code.like(f"%{search_term}%")
            | Course.code.like(f"%{search_term}%")
        )
    course_select = select(Course).filter(*filters)
    courses = session.scalars(course_select).all()
    og_length = len(courses)
    courses = courses[start_slice : start_slice + Course.SEARCH_INTERVAL]
    LastTd = Td()
    if og_length > start_slice + Course.SEARCH_INTERVAL:
        LastTd = Td(
            hx_trigger="intersect once",
            hx_target="closest tr",
            hx_include="#course_search",
            hx_get=app.url_path_for("course_live_search"),
            hx_swap="afterend",
            hx_vals={"start_slice": start_slice + Course.SEARCH_INTERVAL},
        )
    return tuple(
        [
            Tr(
                hx_trigger="click",
                hx_get=app.url_path_for("add_course_pill"),
                hx_include="#included_courses",
                hx_vals={"course_id": course.rowid},
                hx_target="#included_courses",
                cls="search-option border-start border-end",
            )(
                (LastTd if i == len(courses) - 1 else Td)(f"{course.subject_code} {course.code}"),
                Td(f"{course.name}"),
            )
            for i, course in enumerate(courses)
        ]
    )


# want to replace all instead of adding one such that we easliy replace the message
# that there are no courses selected
@app.get(f"{PARTIALS_PREFIX}/add_course_pill")
def add_course_pill(request: Request, course_id: int):
    included_courses = request.query_params.getlist("included_course")
    included_courses.append(str(course_id))
    courses_select = select(Course).filter(Course.rowid.in_(included_courses))
    courses = list(session.scalars(courses_select).all())

    return (
        tuple(CoursePill(course) for course in courses),
        HttpHeader("HX-Trigger-After-Settle", "updateSections"),
    )


@app.delete(f"{PARTIALS_PREFIX}/remove_course_pill")
def remove_course_pill(request: Request, course_id: int):
    included_courses = request.query_params.getlist("included_course")
    included_courses.remove(str(course_id))
    courses_select = select(Course).filter(Course.rowid.in_(included_courses))
    courses = list(session.scalars(courses_select).all())
    return (
        tuple(CoursePill(course) for course in courses),
        HttpHeader("HX-Trigger-After-Settle", "updateSections"),
    )


# this seems slow for some reason or another
@app.get(f"{PARTIALS_PREFIX}/search_sections")
def search_sections(request: Request, term_id: int, start_slice: int):
    included_courses = request.query_params.getlist("included_course")
    if not included_courses:
        sections = []
    else:
        sections_select = (
            select(Section)
            .options(joinedload(Section.course))
            .options(joinedload(Section.professor))
            .options(joinedload(Section.meetings))
            .join(Course)
            .join(Term)
            .join(Meeting)
            .filter(Course.rowid.in_(included_courses), Term.rowid == term_id)
            .order_by(Course.rowid, Section.number)
        )
        sections = session.scalars(sections_select).unique()

    return tuple(
        [
            Tr(
                Td(section.course.name),
                Td(f"{section.subject_code} {section.course_code}"),
                Td(section.professor if section.professor else "None"),
                Td(*SectionMeetingTimes(section)),
            )
            for section in sections
        ]
    )
