#-----------------------------------------------------------------------------
# Copyright (c) 2012 - 2023, Anaconda, Inc., and Bokeh Contributors.
# All rights reserved.
#
# The full license is in the file LICENSE.txt, distributed with this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Boilerplate
#-----------------------------------------------------------------------------
from __future__ import annotations # isort:skip

import pytest ; pytest

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

# Standard library imports
import re
import sys
from typing import TYPE_CHECKING

## External imports
if TYPE_CHECKING:
    from selenium.webdriver.remote.webdriver import WebDriver

# Bokeh imports
from bokeh.core.validation import silenced
from bokeh.core.validation.warnings import MISSING_RENDERERS
from bokeh.io.state import curstate
from bokeh.io.webdriver import webdriver_control
from bokeh.layouts import row
from bokeh.models import (
    Circle,
    ColumnDataSource,
    Div,
    Plot,
    Range1d,
    Rect,
)
from bokeh.plotting import figure
from bokeh.resources import Resources
from bokeh.themes import Theme

# Module under test
import bokeh.io.export as bie # isort:skip

#-----------------------------------------------------------------------------
# Setup
#-----------------------------------------------------------------------------

@pytest.fixture(scope="module", params=["chromium", "firefox"])
def webdriver(request: pytest.FixtureRequest):
    driver = webdriver_control.create(request.param)
    try:
        yield driver
    finally:
        webdriver_control.terminate(driver)


@pytest.fixture(scope="module", params=["chromium", "firefox"])
def webdriver_with_scale_factor(request: pytest.FixtureRequest):
    driver = webdriver_control.create(request.param, scale_factor=2.5)
    try:
        yield driver
    finally:
        webdriver_control.terminate(driver)

#-----------------------------------------------------------------------------
# General API
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Dev API
#-----------------------------------------------------------------------------

@pytest.mark.selenium
@pytest.mark.parametrize("dimensions", [(14, 14), (44, 44), (144, 144), (444, 444), (1444, 1444)])
def test_get_screenshot_as_png(webdriver: WebDriver, dimensions: tuple[int, int]) -> None:
    if sys.platform == "darwin" and webdriver.name == "firefox":
        pytest.skip(reason="unreliable on MacOS and Firefox")

    width, height = dimensions
    border = 5

    layout = Plot(x_range=Range1d(), y_range=Range1d(),
                  height=width, width=height,
                  min_border=border,
                  hidpi=False,
                  toolbar_location=None,
                  outline_line_color=None, background_fill_color="#00ff00", border_fill_color="#00ff00")

    with silenced(MISSING_RENDERERS):
        png = bie.get_screenshot_as_png(layout, driver=webdriver)

    # a WxHpx image of white pixels
    assert png.size == (width, height)

    data = png.tobytes()
    assert len(data) == 4*width*height
    assert data == b"\x00\xff\x00\xff"*width*height


@pytest.mark.selenium
@pytest.mark.parametrize("dimensions", [(14, 14), (44, 44), (144, 144), (444, 444), (1444, 1444)])
def test_get_screenshot_as_png_with_glyph(webdriver: WebDriver, dimensions: tuple[int, int]) -> None:
    if sys.platform == "darwin" and webdriver.name == "firefox":
        pytest.skip(reason="unreliable on MacOS and Firefox")

    width, height = dimensions
    border = 5

    layout = Plot(x_range=Range1d(-1, 1), y_range=Range1d(-1, 1),
                  height=width, width=height,
                  toolbar_location=None,
                  min_border=border,
                  hidpi=False,
                  outline_line_color=None, background_fill_color="#00ff00", border_fill_color="#00ff00")
    glyph = Rect(x="x", y="y", width=2, height=2, fill_color="#ff0000", line_color="#ff0000")
    source = ColumnDataSource(data=dict(x=[0], y=[0]))
    layout.add_glyph(source, glyph)

    png = bie.get_screenshot_as_png(layout, driver=webdriver)
    assert png.size == (width, height)

    data = png.tobytes()
    assert len(data) == 4*width*height

    # count red pixels in center area
    count = 0
    for x in range(width*height):
        pixel = data[x*4:x*4+4]
        if pixel == b"\xff\x00\x00\xff":
            count += 1

    w, h, b = width, height, border
    expected_count = w*h - 2*b*(w + h) + 4*b**2
    assert count == expected_count

@pytest.mark.selenium
def test_get_screenshot_as_png_with_fractional_sizing__issue_12611(webdriver: WebDriver) -> None:
    div = Div(text="Something", styles=dict(width="100.64px", height="50.34px"))
    png = bie.get_screenshot_as_png(div, driver=webdriver)
    assert len(png.tobytes()) > 0

@pytest.mark.selenium
def test_get_screenshot_as_png_with_scale_factor_equal_to_dpr__issue_8807(
        webdriver_with_scale_factor: WebDriver) -> None:
    div = Div(text="Something", styles=dict(width="100px", height="100px"))
    png = bie.get_screenshot_as_png(div, driver=webdriver_with_scale_factor, scale_factor=2.5)
    assert png.width == 250

@pytest.mark.selenium
def test_get_screenshot_as_png_with_scale_factor_less_than_dpr__issue_8807(
        webdriver_with_scale_factor: WebDriver) -> None:
    div = Div(text="Something", styles=dict(width="100px", height="100px"))
    png = bie.get_screenshot_as_png(div, driver=webdriver_with_scale_factor, scale_factor=1.5)
    assert png.width == 150

@pytest.mark.selenium
def test_get_screenshot_as_png_with_scale_factor_greater_than_dpr__issue_8807(
        webdriver_with_scale_factor: WebDriver) -> None:
    div = Div(text="Something", styles=dict(width="100px", height="100px"))
    with pytest.raises(ValueError):
        _ = bie.get_screenshot_as_png(div, driver=webdriver_with_scale_factor, scale_factor=3.5)

@pytest.mark.selenium
def test_get_screenshot_as_png_with_unicode_minified(webdriver: WebDriver) -> None:
    p = figure(title="유니 코드 지원을위한 작은 테스트")

    with silenced(MISSING_RENDERERS):
        png = bie.get_screenshot_as_png(p, driver=webdriver, resources=Resources(mode="inline", minified=True))

    assert len(png.tobytes()) > 0

@pytest.mark.selenium
def test_get_screenshot_as_png_with_unicode_unminified(webdriver: WebDriver) -> None:
    p = figure(title="유니 코드 지원을위한 작은 테스트")

    with silenced(MISSING_RENDERERS):
        png = bie.get_screenshot_as_png(p, driver=webdriver, resources=Resources(mode="inline", minified=False))

    assert len(png.tobytes()) > 0

@pytest.mark.selenium
def test_get_svg_no_svg_present(webdriver: WebDriver) -> None:
    layout = Plot(
        x_range=Range1d(), y_range=Range1d(),
        height=20, width=20, toolbar_location=None,
        outline_line_color=None, border_fill_color=None,
        background_fill_color="red", output_backend="canvas",
    )

    with silenced(MISSING_RENDERERS):
        svgs = bie.get_svg(layout, driver=webdriver)

    def output(data: str) -> list[str]:
        return [
            '<svg version="1.1" xmlns="http://www.w3.org/2000/svg" width="20" height="20">'
                '<defs/>'
                f'<image width="20" height="20" preserveAspectRatio="none" href="data:image/png;base64,{data}"/>'
            '</svg>',
        ]

    chrome_data = (
        "iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAAAXNSR0IArs4c6QAAAFNJ"
        "REFUOE9jZKAyYKSyeQyjBkJC9D8DgwMDBBMCBxgZGA4gK8Iahv8ZGBoYGBjqCZnGwMDQ"
        "yAhRCwejBsIjZTQMcSaggUs21M0pROQQnEpGYPEFALJrIRXAq4rZAAAAAElFTkSuQmCC"

    )
    firefox_data = (
        "iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAAUUlEQVQ4T2NkoDJgpLJ5D"
        "KMGQkL0PwODA5ACYULgADDMDiArwhqGQAMbgIrqCZkGlG8EGgBSCwejBsIjZTQMcSaggUs"
        "21M0pROQQnEpGYPEFALJrIRV3ULevAAAAAElFTkSuQmCC"
    )

    if webdriver.name == "chrome":
        assert svgs == output(chrome_data)
    else:
        assert svgs == output(firefox_data)

@pytest.mark.selenium
def test_get_svg_with_svg_present(webdriver: WebDriver) -> None:
    def plot(color: str):
        return Plot(
            x_range=Range1d(), y_range=Range1d(),
            height=20, width=20, toolbar_location=None,
            outline_line_color=None, border_fill_color=None,
            background_fill_color=color, output_backend="svg",
        )

    layout = row([plot("red"), plot("blue")])

    with silenced(MISSING_RENDERERS):
        svgs0 = bie.get_svg(layout, driver=webdriver)
        svgs1 = bie.get_svg(layout, driver=webdriver)

    svgs2 = [
        '<svg version="1.1" xmlns="http://www.w3.org/2000/svg" width="40" height="20">'
            '<defs/>'
            '<path fill="rgb(0,0,0)" stroke="none" paint-order="stroke" d="M 0 0 L 40 0 L 40 20 L 0 20 L 0 0 Z" fill-opacity="0"/>'
            '<path fill="rgb(255,0,0)" stroke="none" paint-order="stroke" d="M 5.5 5.5 L 15.5 5.5 L 15.5 15.5 L 5.5 15.5 L 5.5 5.5 Z" fill-opacity="1"/>'
            '<g transform="matrix(1, 0, 0, 1, 20, 0)">'
                '<path fill="rgb(0,0,255)" stroke="none" paint-order="stroke" d="M 5.5 5.5 L 15.5 5.5 L 15.5 15.5 L 5.5 15.5 L 5.5 5.5 Z" fill-opacity="1"/>'
            '</g>'
        '</svg>',
    ]

    assert svgs0 == svgs2
    assert svgs1 == svgs2

@pytest.mark.selenium
def test_get_svg_with_implicit_document_and_theme(webdriver: WebDriver) -> None:
    state = curstate()
    state.reset()
    try:
        state.document.theme = Theme(json={
            "attrs": {
                "Plot": {
                    "background_fill_color": "#2f3f4f",
                },
            },
        })

        def p(color: str):
            plot = Plot(
                x_range=Range1d(-1, 1), y_range=Range1d(-1, 1),
                height=200, width=200,
                toolbar_location=None,
                output_backend="svg",
            )
            plot.add_glyph(Circle(x=0, y=0, radius=1, fill_color=color))
            return plot

        [svg] = bie.get_svg(row([p("red"), p("blue")]), driver=webdriver)
        assert len(re.findall(r'fill="rgb\(47,63,79\)"', svg)) == 2
    finally:
        state.reset()

@pytest.mark.selenium
def test_get_svgs_no_svg_present() -> None:
    layout = Plot(x_range=Range1d(), y_range=Range1d(), height=20, width=20, toolbar_location=None)

    with silenced(MISSING_RENDERERS):
        svgs = bie.get_svgs(layout)

    assert svgs == []

@pytest.mark.selenium
def test_get_svgs_with_svg_present(webdriver: WebDriver) -> None:
    def plot(color: str):
        return Plot(
            x_range=Range1d(), y_range=Range1d(),
            height=20, width=20, toolbar_location=None,
            outline_line_color=None, border_fill_color=None,
            background_fill_color=color, output_backend="svg",
        )

    layout = row([plot("red"), plot("blue")])

    with silenced(MISSING_RENDERERS):
        svgs0 = bie.get_svgs(layout, driver=webdriver)
        svgs1 = bie.get_svgs(layout, driver=webdriver)

    svgs2 = [
        '<svg version="1.1" xmlns="http://www.w3.org/2000/svg" width="20" height="20">'
            '<defs/>'
            '<path fill="rgb(255,0,0)" stroke="none" paint-order="stroke" d="M 5.5 5.5 L 15.5 5.5 L 15.5 15.5 L 5.5 15.5 L 5.5 5.5 Z" fill-opacity="1"/>'
        '</svg>',
        '<svg version="1.1" xmlns="http://www.w3.org/2000/svg" width="20" height="20">'
            '<defs/>'
            '<path fill="rgb(0,0,255)" stroke="none" paint-order="stroke" d="M 5.5 5.5 L 15.5 5.5 L 15.5 15.5 L 5.5 15.5 L 5.5 5.5 Z" fill-opacity="1"/>'
        '</svg>',
    ]

    assert svgs0 == svgs2
    assert svgs1 == svgs2

def test_get_layout_html_resets_plot_dims() -> None:
    initial_height, initial_width = 200, 250

    layout = Plot(x_range=Range1d(), y_range=Range1d(),
                  height=initial_height, width=initial_width)

    with silenced(MISSING_RENDERERS):
        bie.get_layout_html(layout, height=100, width=100)

    assert layout.height == initial_height
    assert layout.width == initial_width

def test_layout_html_on_child_first() -> None:
    p = Plot(x_range=Range1d(), y_range=Range1d())

    with silenced(MISSING_RENDERERS):
        bie.get_layout_html(p, height=100, width=100)

    with silenced(MISSING_RENDERERS):
        layout = row(p)
        bie.get_layout_html(layout)

def test_layout_html_on_parent_first() -> None:
    p = Plot(x_range=Range1d(), y_range=Range1d())

    with silenced(MISSING_RENDERERS):
        layout = row(p)
        bie.get_layout_html(layout)

    with silenced(MISSING_RENDERERS):
        bie.get_layout_html(p, height=100, width=100)

#-----------------------------------------------------------------------------
# Private API
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Code
#-----------------------------------------------------------------------------
