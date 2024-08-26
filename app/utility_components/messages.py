from fasthtml.common import *


def Message(*c, title="Scheduler", title_secondary: str = ""):
    return Div(
        hx_swap_oob="afterend:#messages",
        role="alert",
        aria_live="assertive",
        aria_atomic="true",
        cls="toast",
        onload="bootstrap.Toast.getOrCreateInstance(toastLiveExample).show()",
    )(
        Div(cls="toast-header")(
            Strong(title, cls="me-auto"),
            Small(title_secondary, cls="text-body-secondary"),
            Button(type="button", data_bs_dismiss="toast", aria_label="Close", cls="btn-close"),
        ),
        Div(*c, cls="toast-body"),
    )


MessageStack = Div(id="messages", cls="toast-container position-static")
