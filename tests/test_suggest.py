import pytest
from docker_cookiecutter import suggest


def split_to_args(args_string):
    return args_string.split()


@pytest.mark.parametrize(
    "given,want_docker,want_cookiecutter",
    [
        pytest.param(
            "docker params some-image:some-tag cookiecutter params",
            "docker params some-image:some-tag",
            "cookiecutter params",
            id="basic",
        ),
        pytest.param(
            "some-image:some-tag cookiecutter params",
            "some-image:some-tag",
            "cookiecutter params",
            id="image and cookiecutter",
        ),
        pytest.param(
            "cookiecutter params", "", "cookiecutter params", id="just cookiecutter"
        ),
        pytest.param(
            "some generic stuff", "some generic stuff", "", id="no cookiecutter"
        ),
    ],
)
def test_split_docker_from_cookiecutter(given, want_docker, want_cookiecutter):
    given_args = split_to_args(given)

    got_docker, got_cookiecutter = suggest.split_docker_from_cookiecutter(given_args)

    assert got_docker == split_to_args(want_docker)
    assert got_cookiecutter == split_to_args(want_cookiecutter)


@pytest.mark.parametrize(
    "given_host,given_container,want",
    [
        pytest.param(
            "/some/path",
            "/in",
            ["--mount", "type=bind,source=/some/path,target=/in"],
            id="normal",
        ),
        pytest.param(
            '"$(pwd)"/stuff',
            "/in",
            ["--mount", 'type=bind,source="$(pwd)"/stuff,target=/in'],
            id="already has pwd",
        ),
        pytest.param(
            "relative/path",
            "/out",
            ["--mount", 'type=bind,source="$(pwd)"/relative/path,target=/out'],
            id="relative path",
        ),
        pytest.param(
            "./relative/path",
            "/jiggy",
            ["--mount", 'type=bind,source="$(pwd)"/./relative/path,target=/jiggy'],
            id="single dotted relative path",
        ),
    ],
)
def test_docker_mount_args(given_host, given_container, want):
    got = suggest.docker_mount_args(given_host, given_container)
    assert got == want


some_image = "some-image:some-tag"

input_docker_preamble_base = ["docker", "run"]

input_docker_preamble_expanded = input_docker_preamble_base + ["-it", "--rm"]

expected_docker_preamble = input_docker_preamble_expanded + [
    "--user",
    '"$(id -u):$(id -g)"',
]

expected_o = ["-o", "/out"]

expected_cmd_preamble = ["cookiecutter"] + expected_o

some_gh_template = "gh:audreyr/cookiecutter-pypackage"


@pytest.mark.parametrize(
    "given,want",
    [
        pytest.param(
            input_docker_preamble_expanded + [some_image, "cookiecutter", "-f", "-s"],
            expected_docker_preamble
            + suggest.docker_mount_args('"$(pwd)"', "/out")
            + [some_image]
            + expected_cmd_preamble
            + ["--overwrite-if-exists", "--skip-if-file-exists"],
            id="normal",
        ),
        pytest.param(
            input_docker_preamble_base + [some_image, "cookiecutter", "-f", "-s"],
            expected_docker_preamble
            + suggest.docker_mount_args('"$(pwd)"', "/out")
            + [some_image]
            + expected_cmd_preamble
            + ["--overwrite-if-exists", "--skip-if-file-exists"],
            id="normal - input missing -it --rm",
        ),
        pytest.param(
            input_docker_preamble_base + [some_image, "cookiecutter", some_gh_template],
            expected_docker_preamble
            + suggest.docker_mount_args('"$(pwd)"', "/out")
            + [some_image]
            + expected_cmd_preamble
            + [some_gh_template],
            id="simple gh",
        ),
        pytest.param(
            input_docker_preamble_expanded
            + [some_image, "cookiecutter", "--verbose", "-o", "/some/path"],
            expected_docker_preamble
            + suggest.docker_mount_args("/some/path", "/out")
            + [some_image]
            + expected_cmd_preamble
            + ["--verbose"],
            id="-o maps to docker --mount",
        ),
        pytest.param(
            input_docker_preamble_expanded
            + [some_image, "cookiecutter", "-c", "the-branch", "/some/path"],
            expected_docker_preamble
            + suggest.docker_mount_args("/some/path", "/in")
            + suggest.docker_mount_args('"$(pwd)"', "/out")
            + [some_image]
            + expected_cmd_preamble
            + ["--checkout", "the-branch", "/in"],
            id="local template maps to docker --mount",
        ),
        pytest.param(
            input_docker_preamble_expanded + [some_image, "cookiecutters", "a,,b"],
            expected_docker_preamble
            + suggest.docker_mount_args("a", "/in-0")
            + suggest.docker_mount_args("b", "/in-1")
            + suggest.docker_mount_args('"$(pwd)"', "/out")
            + [some_image]
            + ["cookiecutters"]
            + expected_o
            + ["/in-0,,/in-1"],
            id="cookiecutters - local templates map to docker --mounts",
        ),
    ],
)
def test_cookiecutter_to_docker_args(given, want):
    got = suggest.cookiecutter_to_docker_args(given)

    assert got == want
