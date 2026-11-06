"""Shared fixtures: serve the repo over HTTP and hand tests a loaded page."""
import functools
import http.server
import os
import threading

import pytest
from playwright.sync_api import sync_playwright

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


@pytest.fixture(scope="session")
def base_url():
    srv = http.server.ThreadingHTTPServer(
        ("127.0.0.1", 0), functools.partial(_Quiet, directory=REPO))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


@pytest.fixture(scope="session")
def browser():
    with sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


@pytest.fixture
def page(browser, base_url):
    """A phone-sized page with index.html loaded; fails the test on a page error."""
    ctx = browser.new_context(viewport={"width": 390, "height": 664},
                              has_touch=True, is_mobile=True)
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(f"{base_url}/index.html")
    pg.wait_for_timeout(250)
    pg.page_errors = errors
    yield pg
    ctx.close()
    assert not errors, f"page errors: {errors}"
