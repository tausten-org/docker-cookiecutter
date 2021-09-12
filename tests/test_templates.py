import pytest
from docker_cookiecutter import templates


@pytest.mark.parametrize(
    "given,want",
    [
        pytest.param("a", [templates.TemplateSourceInfo("a")], id="single"),
        pytest.param(
            "a,checkout=branch",
            [templates.TemplateSourceInfo("a", checkout="branch")],
            id="single with checkout",
        ),
        pytest.param(
            "a,directory=dir",
            [templates.TemplateSourceInfo("a", directory="dir")],
            id="single with directory",
        ),
        pytest.param(
            "a,directory=dir,checkout=branch",
            [templates.TemplateSourceInfo("a", checkout="branch", directory="dir")],
            id="single - all 3 components",
        ),
        pytest.param(
            "a,,b",
            [templates.TemplateSourceInfo("a"), templates.TemplateSourceInfo("b")],
            id="multi",
        ),
        pytest.param(
            "a,checkout=abranch,,b,directory=bdir",
            [
                templates.TemplateSourceInfo("a", checkout="abranch"),
                templates.TemplateSourceInfo("b", directory="bdir"),
            ],
            id="multi - a-checkout, b-directory",
        ),
        pytest.param(
            "a,checkout=abranch,,b,,c,directory=cdir",
            [
                templates.TemplateSourceInfo("a", checkout="abranch"),
                templates.TemplateSourceInfo("b"),
                templates.TemplateSourceInfo("c", directory="cdir"),
            ],
            id="multi - mix",
        ),
    ],
)
def test_decode_template_sources(given, want):
    got = templates.decode_template_sources(given)
    assert got == want
