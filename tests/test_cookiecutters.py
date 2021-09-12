from unittest.mock import call

import pytest
from docker_cookiecutter.cookiecutters import cookiecutters


@pytest.mark.parametrize(
    "given,want_templates",
    [
        pytest.param("a", ["a"], id="single"),
        pytest.param("a,,b", ["a", "b"], id="multi"),
    ],
)
def test_calls_cookiecutter_once_per_template(mocker, given, want_templates):
    mocked_cookiecutter = mocker.patch(
        "docker_cookiecutter.cookiecutters.cookiecutter", return_value="ignored for now"
    )

    result = cookiecutters(given)

    expected_calls = [call(x) for x in want_templates]

    mocked_cookiecutter.assert_has_calls(expected_calls)
    assert result is not None
