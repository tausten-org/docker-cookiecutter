from typing import Dict, List

import pytest
from docker_cookiecutter import pathmap


@pytest.mark.parametrize(
    "given,want",
    [
        pytest.param(["a"], ["a"], id="single"),
        pytest.param(["/"], ["/"], id="single - root - linux"),
        pytest.param(["c:\\"], ["c:\\"], id="single - root - windows"),
        pytest.param(["a", "b"], ["a", "b"], id="multi - no overlap"),
        pytest.param(["a", "a/b"], ["a"], id="multi - mounting both parent and child"),
        pytest.param(
            ["a", "a/b/c"], ["a"], id="multi - mounting both parent and indirect child"
        ),
        pytest.param(["a/", "a"], ["a"], id="trailing slash deduped"),
    ],
)
def test_reduce_mounts(given, want):
    result = pathmap.reduce_mounts(given)
    assert set(result) == set(want)


@pytest.mark.parametrize(
    "given,want",
    [
        pytest.param("a", "a", id="trivial"),
        pytest.param("a/", "a", id="trailing - linux"),
        pytest.param("a\\", "a", id="trailing - windows"),
        pytest.param("/", "/", id="root - linux"),
        pytest.param("///", "/", id="root - repeated - linux"),
        pytest.param("c:\\", "c:\\", id="root - windows"),
        pytest.param("c:\\\\\\", "c:\\", id="root - repeated - windows"),
        pytest.param("a/b", "a/b", id="inner - trivial - linux"),
        pytest.param("a///b", "a/b", id="inner - repeated - linux"),
    ],
)
def test_normalize_path(given, want):
    result = pathmap.normalize_path(given)
    assert result == want
