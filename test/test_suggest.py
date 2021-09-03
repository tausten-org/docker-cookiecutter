import pytest

from util import suggest

def split_to_args(args_string):
    return args_string.split()

@pytest.mark.parametrize(
    "given,want_docker,want_cookiecutter", [
    pytest.param("docker params some-image:some-tag cookiecutter params", "docker params some-image:some-tag", "cookiecutter params" , id="basic"),
    pytest.param("some-image:some-tag cookiecutter params", "some-image:some-tag", "cookiecutter params" , id="image and cookiecutter"),
    pytest.param("cookiecutter params", "", "cookiecutter params" , id="just cookiecutter"),
    pytest.param("some generic stuff", "some generic stuff", "" , id="no cookiecutter"),
])
def test_split_docker_from_cookiecutter(given, want_docker, want_cookiecutter):
    given_args = split_to_args(given)

    got_docker, got_cookiecutter = suggest.split_docker_from_cookiecutter(given_args)
    
    assert got_docker == split_to_args(want_docker)
    assert got_cookiecutter == split_to_args(want_cookiecutter)

@pytest.mark.parametrize(
    "given_host,given_container,want", [
    pytest.param("/some/path", "/in", ["-v", "/some/path:/in"], id="normal"),
    pytest.param('"$(pwd)"/stuff', "/in", ["-v", '"$(pwd)"/stuff:/in'], id="already has pwd"),
    pytest.param("relative/path", "/out", ["-v", '"$(pwd)"/relative/path:/out'], id="relative path"),
    pytest.param("./relative/path", "/jiggy", ["-v", '"$(pwd)"/./relative/path:/jiggy'], id="single dotted relative path"),
])
def test_docker_v_args(given_host, given_container, want):
    got = suggest.docker_v_args(given_host, given_container)
    assert got == want

some_image = "some-image:some-tag"

input_docker_preamble = ["docker", "run", "-it", "--rm"]

expected_docker_preamble = input_docker_preamble + ["--user", '"$(id -u):$(id -g)"']

expected_o = ["-o", "/out"]

expected_cmd_preamble = ["cookiecutter"] + expected_o

@pytest.mark.parametrize(
    "given,want", [
    pytest.param(input_docker_preamble + [some_image, "cookiecutter", "-f", "-s"], 
        expected_docker_preamble 
        + suggest.docker_v_args('"$(pwd)"', "/out") 
        + [some_image]
        + expected_cmd_preamble + ["--overwrite-if-exists", "--skip-if-file-exists"], 
    id="normal"),

    pytest.param(input_docker_preamble + [some_image, "cookiecutter", "--verbose", "-o", "/some/path"], 
        expected_docker_preamble 
        + suggest.docker_v_args("/some/path", "/out") 
        + [some_image]
        + expected_cmd_preamble + ["--verbose"], 
    id="-o maps to docker -v"),

    pytest.param(input_docker_preamble + [some_image, "cookiecutter", "-c", "the-branch", "/some/path"], 
        expected_docker_preamble 
        + suggest.docker_v_args("/some/path", "/in") 
        + suggest.docker_v_args('"$(pwd)"', "/out") 
        + [some_image]
        + expected_cmd_preamble + ["--checkout", "the-branch", "/in"], 
    id="local template maps to docker -v"),
])
def test_cookiecutter_to_docker_args(given, want):
    got = suggest.cookiecutter_to_docker_args(given)

    assert got == want
