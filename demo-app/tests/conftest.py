import base64
import os
import pytest
import pytest_html
from pytest_metadata.plugin import metadata_key


def pytest_html_report_title(report):
    report.title = "Pytest HTML Report"


def pytest_configure(config):
    config.stash[metadata_key]["Project"] = "Forex Trading Platform API"


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item):
    outcome = yield
    report = outcome.get_result()
    extras = getattr(report, "extras", [])
    if report.when == "call":
        xfail = hasattr(report, "wasxfail")
        if (report.skipped and xfail) or (report.failed and not xfail):
            # only add additional html on failure
            extras.append(pytest_html.extras.html("<div>Additional HTML</div>"))
        report.extras = extras
