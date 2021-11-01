import ntpath
import os
import posixpath
import re
from typing import Tuple

# Regex for finding separators
UNKNOWN_SEP_CHARS_REGEX = re.compile(r"[/\\]+")


class PathMap:
    """
    Maps host paths to container paths.
    """

    def __init__(
        self,
        host_paths: "list[str]",
        container_abs: str = "/h/abs",
        container_rel: str = "/h/rel",
        container_rel_dd: str = "dd",
    ) -> None:
        """
        Args:
            host_paths: list of host paths to map to container mounts and paths
            container_abs: the container folder under which absolute host paths will be mapped
            container_rel: the container folder under which relative host paths will be mapped
            container_rel_dd: a folder name to use to stand in for ".." which will force
                additional levels of sub-folders to be included under container_rel
        """
        normalized_host_paths = [normalize_path(host_path) for host_path in host_paths]
        self.mounts, self.mappings = PathMap.__map_host_to_container(
            normalized_host_paths, container_abs, container_rel, container_rel_dd
        )

    def get_mounts(self) -> "list[str]":
        """
        Returns the list of mounts that should be made to accomodate the host paths used to
        construct this PathMap
        """
        return self.mounts

    def get_container_path(self, host_path: str) -> str:
        """
        Return the already-mapped container_path for the specified host_path.
        """
        normalized_host_path = normalize_path(host_path)
        return self.mappings[normalized_host_path]

    @staticmethod
    def __map_host_to_container(
        host_paths, container_abs, container_rel, container_rel_dd
    ):
        """
        Takes a set of host paths, and computes the list of host paths needing mounting, and
        a mapping of all related host_paths (those explicitly provided, and those needing mounting)
        to container paths.
        """
        min_mounts = reduce_mounts(host_paths)
        map_host_to_container_paths = {}
        relative_path_tuples = []

        for path in host_paths:
            nix_path = transform_to_nix_path(path)

            if nix_path.startswith("/"):
                container_path = posixpath.join(
                    container_abs, nix_path.lstrip(posixpath.sep)
                )
                map_host_to_container_paths[path] = container_path
            else:
                relative_path_tuples.append((nix_path, path))

        # now handle the relative paths
        relative_path_tuples.sort()
        relative_path_prefix = container_rel
        current_relative_path_head = None
        for relative, host_path in relative_path_tuples:
            head, tail = split_relative(relative)

            if (
                current_relative_path_head is not None
                and current_relative_path_head != head
            ):
                relative_path_prefix = posixpath.join(
                    relative_path_prefix, container_rel_dd
                )

            current_relative_path_head = head

            container_path = normalize_path(posixpath.join(relative_path_prefix, tail))

            map_host_to_container_paths[host_path] = container_path

        return min_mounts, map_host_to_container_paths


class PathMapBuilder:
    """Accumulates paths and then builds a PathMap when asked."""

    def __init__(self) -> None:
        self.paths = []

    def add_path(self, path: str):
        self.paths.append(path)

    def build(
        self, container_abs: str, container_rel: str, container_dd: str
    ) -> PathMap:
        return PathMap(self.paths, container_abs, container_rel, container_dd)


def split_relative(path: str) -> Tuple[str, str]:
    """
    Takes a normalized potentially relative path and splits it into the relative portion
    """
    rel = None
    tail = path
    pos = path.rfind("../")
    if pos >= 0:
        split_pos = pos + len("../")
        rel = path[:split_pos]
        tail = path[split_pos:]

    return (rel, tail)


def normalize_path(candidate: str) -> str:
    """
    Path origin is unknown, but we wish to collapse consecutive separators down to singles
    and trim any final trailing separator (but only if the path is not for "root" folder)
    """
    # CAUTION: Making simplifying assumption that any and all "\" characters are just folder
    # separators (eg. from windows path), and not actually meant to be escaping anything.
    norm = UNKNOWN_SEP_CHARS_REGEX.sub(posixpath.sep, candidate)

    norm = posixpath.normpath(norm)

    # Special case - we've hit a root path, so add the slash back
    if len(norm) == 0 or norm.endswith(posixpath.pathsep):
        norm += posixpath.sep

    return make_explicit_relative(norm)


def make_explicit_relative(candidate: str) -> str:
    # If we're an absolute path or explicit relative path, then all done
    if candidate.startswith(posixpath.sep) or candidate.startswith("."):
        return candidate

    # If relative path without "." then add that explicitly
    if posixpath.pathsep not in candidate:
        candidate = "." + posixpath.sep + candidate

    return candidate


def transform_to_nix_path(candidate: str) -> str:
    """
    Path origin is unknown, but we wish to transform it to a comparable *nix path
    """
    # CAUTION: Making simplifying assumption that any and all "\" characters are just folder
    # separators (eg. from windows path), and not actually meant to be escaping anything.
    norm = UNKNOWN_SEP_CHARS_REGEX.sub(posixpath.sep, candidate)

    # let's ensure we skip any possible windows / UNC drive bit
    _, tail = ntpath.splitdrive(norm)
    norm = tail

    # finally, we normalize to unix
    norm = posixpath.normpath(norm)

    return make_explicit_relative(norm)


def reduce_mounts(inputs):
    """
    Given a set of input paths intended to be mounted, reduce this to the subset that need mounting.
    (eg. avoid mounting children of folders already being mounted).
    """
    has_mount_or_parent_mount = {}
    reduced_mounts = []

    # make sure our inputs are sorted so that we get to parents before children
    inputs = [normalize_path(p) for p in inputs]
    inputs.sort()

    for mount in inputs:
        parent, _ = parse_parent_child(mount)
        # if we're mounting a folder other than root, we should strip trailing separators
        # parent_trimmed = parent.rstrip(PATH_SEP_CHARS) if not is_root_mount else None
        if not has_mount_or_parent_mount_recurse(
            parent, reduced_mounts, has_mount_or_parent_mount
        ):
            reduced_mounts.append(mount)

    return reduced_mounts


def is_root(parent: str, child: str) -> bool:
    return len(child) < 1 and (len(parent) < 1 or parent.endswith(posixpath.sep))


def has_mount_or_parent_mount_recurse(
    candidate, explicit_mounts, has_mount_or_parent_mount_map
):
    if candidate is None:
        return False

    status = has_mount_or_parent_mount_map.get(candidate)
    if status is not None:
        # We've already computed this one, so return directly
        return status

    # We don't know yet
    if candidate in explicit_mounts:
        status = True
    else:
        parent, child = parse_parent_child(candidate)
        if is_root(parent, child):
            status = False
        else:
            status = has_mount_or_parent_mount_recurse(
                parent, explicit_mounts, has_mount_or_parent_mount_map
            )

    # Store in the memo and return
    has_mount_or_parent_mount_map[candidate] = status
    return status


def parse_parent_child(mount):
    return posixpath.split(mount)
