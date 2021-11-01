import pytest
from docker_cookiecutter import pathmap


@pytest.mark.parametrize(
    "given,want",
    [
        pytest.param(["a"], ["./a"], id="single - relative - trivial"),
        pytest.param(["./a"], ["./a"], id="single - explicit relative - trivial"),
        pytest.param(["."], ["."], id="single - cwd - trivial"),
        pytest.param(["../a"], ["../a"], id="single - relative - parent - linux"),
        pytest.param(["..\\a"], ["../a"], id="single - relative - parent - win"),
        pytest.param(["/"], ["/"], id="single - root - linux"),
        pytest.param(["/a"], ["/a"], id="single - absolute - linux"),
        pytest.param(["c:\\"], ["c:/"], id="single - root - win"),
        pytest.param(["c:\\a"], ["c:/a"], id="single - absolute - win"),
        pytest.param(["a", "b"], ["./a", "./b"], id="multi - no overlap"),
        pytest.param(
            ["a", "a/b"], ["./a"], id="multi - mounting both parent and child"
        ),
        pytest.param(
            ["a", "a/b/c"],
            ["./a"],
            id="multi - mounting both parent and indirect child",
        ),
        pytest.param(
            ["a/b", "a"],
            ["./a"],
            id="multi - mounting both parent and child - out of order",
        ),
        pytest.param(
            [".", "sub/folder"], ["."], id="multi - cwd and sub just mounts cwd"
        ),
    ],
)
def test_reduce_mounts(given, want):
    result = pathmap.reduce_mounts(given)
    assert set(result) == set(want)


@pytest.mark.parametrize(
    "given,want",
    [
        pytest.param("a", "./a", id="trivial"),
        pytest.param(".", ".", id="trivial - cwd"),
        pytest.param("a/.", "./a", id="trivial - redundant dot"),
        pytest.param("a/", "./a", id="trailing - linux"),
        pytest.param("a\\", "./a", id="trailing - win"),
        pytest.param("/", "/", id="root - linux"),
        pytest.param("///", "/", id="root - repeated - linux"),
        pytest.param("c:\\", "c:/", id="root - win"),
        pytest.param("c:\\\\\\", "c:/", id="root - repeated - win"),
        pytest.param("a/b", "./a/b", id="inner - trivial - linux"),
        pytest.param("a///b", "./a/b", id="inner - repeated - linux"),
        pytest.param("/a/b/../c", "/a/c", id="absolute - redundant relative - linux"),
        pytest.param(
            "d:\\a\\b\\..\\c", "d:/a/c", id="absolute - redundant relative - win"
        ),
    ],
)
def test_normalize_path(given, want):
    result = pathmap.normalize_path(given)
    assert result == want


@pytest.mark.parametrize(
    "given,want",
    [
        pytest.param("a", "./a", id="trivial"),
        pytest.param(".", ".", id="trivial - cwd"),
        pytest.param("a/.", "./a", id="trivial - redundant dot"),
        pytest.param("./a", "./a", id="single - cwd + sub - trivial"),
        pytest.param("a/", "./a", id="trailing - linux"),
        pytest.param("a\\", "./a", id="trailing - win"),
        pytest.param("\\\\host\\computer\\dir", "/host/computer/dir", id="unc - win"),
        pytest.param("//host/computer/dir", "/host/computer/dir", id="unc - linux"),
        pytest.param("/", "/", id="root - linux"),
        pytest.param("///", "/", id="root - repeated - linux"),
        pytest.param("c:\\", "/", id="root - win"),
        pytest.param("c:\\\\\\", "/", id="root - repeated - win"),
        pytest.param("a/b", "./a/b", id="inner - trivial - linux"),
        pytest.param("a///b", "./a/b", id="inner - repeated - linux"),
        pytest.param("/a/b/../c", "/a/c", id="absolute - redundant relative - linux"),
        pytest.param(
            "d:\\a\\b\\..\\c", "/a/c", id="absolute - redundant relative - win"
        ),
    ],
)
def test_transform_to_nix_path(given, want):
    result = pathmap.transform_to_nix_path(given)
    assert result == want


@pytest.mark.parametrize(
    "given_paths,want_mappings",
    [
        pytest.param(["/a"], {"/a": "/h/abs/a"}, id="absolute - trivial - linux"),
        pytest.param(["D:\\a"], {"D:\\a": "/h/abs/a"}, id="absolute - trivial - win"),
        pytest.param(["a"], {"a": "/h/rel/a"}, id="relative - sub - trivial"),
        pytest.param(["."], {".": "/h/rel"}, id="relative - cwd - trivial"),
        pytest.param(["../a"], {"../a": "/h/rel/a"}, id="relative - parent - trivial"),
        pytest.param(
            ["../a", "e/f", "../../b", "d/g/h", "../a/c", "d"],
            {
                "../a": "/h/rel/dd/a",
                "e/f": "/h/rel/dd/dd/e/f",
                "../../b": "/h/rel/b",
                "d/g/h": "/h/rel/dd/dd/d/g/h",
                "../a/c": "/h/rel/dd/a/c",
                "d": "/h/rel/dd/dd/d",
            },
            id="relative - parent - multi",
        ),
        pytest.param(
            ["/a/b/", "/c", "c:\\d"],
            {
                "/a/b/": "/h/abs/a/b",
                "/c": "/h/abs/c",
                "c:\\d": "/h/abs/d",
            },
            id="absolute - multiple - mix linux and win",
        ),
    ],
)
def test_map_host_to_container(given_paths, want_mappings):
    # given
    sut = pathmap.PathMap(given_paths, container_abs="/h/abs", container_rel="/h/rel")

    # when
    mounts = sut.get_mounts()
    result_mappings = {
        host_path: sut.get_container_path(host_path)
        for host_path in want_mappings.keys()
    }

    # then
    for mount_host in mounts:
        mount_container = sut.get_container_path(mount_host)
        assert (
            len(mount_container.strip()) > 0
        ), "reduced mount should have a non-empty mapping"
        assert (
            mount_host != mount_container
        ), "reduced mount should be mapped to container path"

    assert result_mappings == want_mappings
