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
            "--mount type=bind,source=/some/path,target=/in",
            id="normal",
        ),
        pytest.param(
            '"$(pwd)"/stuff',
            "/in",
            '--mount type=bind,source="$(pwd)"/stuff,target=/in',
            id="already has pwd",
        ),
        pytest.param(
            "relative/path",
            "/out",
            '--mount type=bind,source="$(pwd)"/relative/path,target=/out',
            id="relative path",
        ),
        pytest.param(
            "./relative/path",
            "/jiggy",
            '--mount type=bind,source="$(pwd)"/relative/path,target=/jiggy',
            id="single dotted relative path",
        ),
        pytest.param(
            "../relative/path",
            "/jiggy",
            '--mount type=bind,source="$(pwd)"/../relative/path,target=/jiggy',
            id="single upward relative path",
        ),
    ],
)
def test_docker_mount_args(given_host, given_container, want):
    got = suggest.docker_mount_args(given_host, given_container)
    assert " ".join(got) == want


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
            "docker run some:image",
            'docker run -it --rm --user "$(id -u):$(id -g)" some:image',
            id="normal - input without -it --rm",
        ),
    ],
)
def test_cookiecutter_to_docker_args_docker_preamble_except_mounts(
    given: str, want: str
):
    # given
    given_args = given.split(" ")

    # when
    got = suggest.cookiecutter_to_docker_args(given_args)
    cc_index = get_cookiecutter_index(got)
    got_docker = " ".join(got[:cc_index])

    got_mounts = get_mounts_as_strings(got)
    for mount in got_mounts:
        got_docker = got_docker.replace(mount + " ", "")

    # then
    assert got_docker == want


@pytest.mark.parametrize(
    "given_cookiecutter,want_cookiecutter,want_mounts",
    [
        pytest.param(
            "cookiecutter -o /output/folder /some/path/someTemplate",
            "cookiecutter -o /h/abs/output/folder /h/abs/some/path/someTemplate",
            [
                "--mount type=bind,source=/output/folder,target=/h/abs/output/folder",
                "--mount type=bind,source=/some/path/someTemplate,target=/h/abs/some/path/someTemplate",
            ],
            id="absolute - simple",
        ),
        pytest.param(
            "cookiecutter some/path/someTemplate",
            "cookiecutter -o /h/rel /h/rel/some/path/someTemplate",
            [
                '--mount type=bind,source="$(pwd)",target=/h/rel',
            ],
            id="relative - wd and below",
        ),
        pytest.param(
            "cookiecutter -f -s tmpl",
            "cookiecutter -o /h/rel --overwrite-if-exists --skip-if-file-exists /h/rel/tmpl",
            [
                '--mount type=bind,source="$(pwd)",target=/h/rel',
            ],
            id="cc args - some flags",
        ),
        pytest.param(
            "cookiecutter -o ../../output ../../../some/path/someTemplate",
            "cookiecutter -o /h/rel/dd/output /h/rel/some/path/someTemplate",
            [
                '--mount type=bind,source="$(pwd)"/../../output,target=/h/rel/dd/output',
                '--mount type=bind,source="$(pwd)"/../../../some/path/someTemplate,target=/h/rel/some/path/someTemplate',
            ],
            id="relative - above wd - collapses dotted relations",
        ),
        pytest.param(
            "cookiecutter tmpl1,,tmpl2",
            "cookiecutters -o /h/rel /h/rel/tmpl1,,/h/rel/tmpl2",
            [
                '--mount type=bind,source="$(pwd)",target=/h/rel',
            ],
            id="relative - multi cookiecutters templates",
        ),
        pytest.param(
            "cookiecutter /tmpl1,,/tmpl2",
            "cookiecutters -o /h/rel /h/abs/tmpl1,,/h/abs/tmpl2",
            [
                '--mount type=bind,source="$(pwd)",target=/h/rel',
                "--mount type=bind,source=/tmpl1,target=/h/abs/tmpl1",
                "--mount type=bind,source=/tmpl2,target=/h/abs/tmpl2",
            ],
            id="absolute - multi cookiecutters templates",
        ),
        pytest.param(
            "cookiecutter " + some_gh_template,
            "cookiecutter -o /h/rel " + some_gh_template,
            [
                '--mount type=bind,source="$(pwd)",target=/h/rel',
            ],
            id="remote - simple",
        ),
        pytest.param(
            "cookiecutter /tmpl1,," + some_gh_template + ",,/tmpl2",
            "cookiecutters -o /h/rel /h/abs/tmpl1,,"
            + some_gh_template
            + ",,/h/abs/tmpl2",
            [
                '--mount type=bind,source="$(pwd)",target=/h/rel',
                "--mount type=bind,source=/tmpl1,target=/h/abs/tmpl1",
                "--mount type=bind,source=/tmpl2,target=/h/abs/tmpl2",
            ],
            id="local + remote - multi cookiecutters templates",
        ),
    ],
)
def test_cookiecutter_to_docker_args_paths(
    given_cookiecutter: str, want_cookiecutter: str, want_mounts: "list[str]"
):
    # given
    given_args = (
        "docker run -it --rm tausten/docker-cookiecutter:latest " + given_cookiecutter
    )
    split_given_args = given_args.split()

    # when
    got = suggest.cookiecutter_to_docker_args(split_given_args)
    cc_index = get_cookiecutter_index(got)
    got_cookiecutter = " ".join(got[cc_index:])

    got_mounts = get_mounts_as_strings(got)

    # then
    assert got_cookiecutter == want_cookiecutter
    assert set(got_mounts) == set(want_mounts)


def get_cookiecutter_index(args: "list[str]") -> int:
    return next((i for i, x in enumerate(args) if x.startswith("cookiecutter")))


def get_mounts_as_strings(args: "list[str]") -> "list[str]":
    # combine the --mount and next element from the returned list so we can do simple
    # string comparisons
    return [
        " ".join(args[i : i + 2]) for i, x in enumerate(args) if x.startswith("--mount")
    ]
