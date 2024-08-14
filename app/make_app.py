from fasthtml.common import *

hdrs = (
        Link(rel="stylesheet", href="https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.red.min.css"), # specific pico
        Script('''
               var qs = document.querySelector.bind(document);
               var qsa = document.querySelectorAll.bind(document);
               '''), # query selector abbreviates
        )

app, rt = fast_app(hdrs=hdrs, pico=False, surreal=False, live=True)

PARTIALS_PREFIX = "/partials"
