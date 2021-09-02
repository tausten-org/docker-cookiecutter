import pytest

from util import commandline

@pytest.mark.parametrize(
    "given_host,given_container,want", [
    pytest.param("/some/path", "/in", ["-v", "/some/path:/in"], id="normal"),
    pytest.param('"$(pwd)"/stuff', "/in", ["-v", '"$(pwd)"/stuff:/in'], id="already has pwd"),
    pytest.param("relative/path", "/out", ["-v", '"$(pwd)"/relative/path:/out'], id="relative path"),
    pytest.param("./relative/path", "/jiggy", ["-v", '"$(pwd)"/./relative/path:/jiggy'], id="single dotted relative path"),
])
def test_docker_v_args(given_host, given_container, want):
    got = commandline.docker_v_args(given_host, given_container)
    assert got == want

expected_preamble = ["run", "-it", "--rm", "--user", '"$(id -u):$(id -g)"']

expected_o = ["-o", "/out"]

expected_cmd_preamble = ["cookiecutter"] + expected_o

@pytest.mark.parametrize(
    "given,want", [
    pytest.param(["-f", "-s"], 
        expected_preamble 
        + commandline.docker_v_args('"$(pwd)"', "/out") 
        + expected_cmd_preamble + ["--overwrite-if-exists", "--skip-if-file-exists"], 
    id="normal"),

    pytest.param(["--verbose", "-o", "/some/path"], 
        expected_preamble 
        + commandline.docker_v_args("/some/path", "/out") 
        + expected_cmd_preamble + ["--verbose"], 
    id="-o maps to docker -v"),

    pytest.param(["-c", "the-branch", "/some/path"], 
        expected_preamble 
        + commandline.docker_v_args("/some/path", "/in") 
        + commandline.docker_v_args('"$(pwd)"', "/out") 
        + expected_cmd_preamble + ["--checkout", "the-branch", "/in"], 
    id="local template maps to docker -v"),
])
def test_cookiecutter_to_docker_args(given, want):
    got = commandline.cookiecutter_to_docker_args(given)

    assert got == want
