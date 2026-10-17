"""Render every reachable Streamlit page without a browser or model calls."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from ui.state import USERS

ROOT = Path(__file__).resolve().parents[1]


def run_page(user, page=None):
    app = AppTest.from_file(ROOT / "app.py", default_timeout=12)
    if user:
        app.session_state["user"] = user
    app.run()
    assert not app.exception
    if page:
        app.switch_page(page).run(timeout=12)
        assert not app.exception
    return app


def test_public_sign_in_page_renders():
    run_page(None)


@pytest.mark.parametrize(("email", "page"), [
    ("ana@ncsu.edu", "ui/pages/student.py"),
    ("ana@ncsu.edu", "ui/pages/shop.py"),
    ("jake@ncsu.edu", "ui/pages/seller.py"),
    ("admin@campusloop.ai", "ui/pages/livedemo.py"),
    ("admin@campusloop.ai", "ui/pages/control.py"),
])
def test_authenticated_pages_render(email, page):
    run_page({"email": email, **USERS[email]}, page)
