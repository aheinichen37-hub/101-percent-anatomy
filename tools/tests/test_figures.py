"""Task 2: locating a figure in the PDF and re-rendering it at higher resolution."""
import pytest

from idimg import figures

pytestmark = pytest.mark.skipif(not figures.pdf_available(),
                                reason="source PDF not staged in this session")


def test_resolves_figure_on_its_real_page():
    """The caption's text page is not always the figure's page: the text layer puts
    'Figure 11.16' on 443 while the drawing is on 444."""
    loc = figures.resolve("11.16")
    assert loc.score >= 0.90
    assert loc.page == 444


def test_resolve_is_cached_and_stable():
    a = figures.resolve("8.6")
    b = figures.resolve("8.6")
    assert (a.page, a.box, a.scale) == (b.page, b.box, b.scale)
    assert a.score >= 0.90


def test_render_is_higher_resolution_than_the_stored_crop():
    from PIL import Image
    stored = Image.open(figures.fig_path("11.32"))
    big = figures.render_figure("11.32", scale=3.0)
    assert big.width > stored.width * 1.1
    # same framing, so the aspect ratio must carry over
    assert abs(big.width / big.height - stored.width / stored.height) < 0.03


def test_unknown_figure_raises():
    with pytest.raises(KeyError):
        figures.resolve("99.99")
