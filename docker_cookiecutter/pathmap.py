import re

PATH_SEP_CHARS = "/\\"

# Regex to detect groups of repeated separator-like chars, and pull out the first char as a
# capture group
REPETITION_OF_UNKNOWN_SEP_CHARS_REGEX = re.compile(r"([/\\])(?:[/\\]+)")

# Regex for finding separators
UNKNOWN_SEP_CHARS_REGEX = re.compile(r"[/\\]+")

# Regex to split a path (of unkown origin - windows or linux) into (parent, child) groups
UNKNOWN_PATH_TYPE_SPLIT_TO_PARENT_AND_CHILD_REGEX = re.compile(
    r"^(?P<parent>.*[/\\]+)(?P<child>[^/\\]+[/\\]*)?$"
)


def normalize_path(candidate):
    """
    Path origin is unknown, but we wish to collapse consecutive separators down to singles
    and trim any final trailing separator (but only if the path is not for "root" folder)
    """
    norm = REPETITION_OF_UNKNOWN_SEP_CHARS_REGEX.sub(r"\1", candidate).rstrip(
        PATH_SEP_CHARS
    )

    # Special case - we've hit a root path, so add the slash back
    if len(norm) == 0 or norm.endswith(":"):
        norm += candidate[-1]

    return norm


def transform_to_nix_path(candidate):
    """
    Path origin is unknown, but we wish to transform it to a comparable *nix path
    """
    norm = UNKNOWN_SEP_CHARS_REGEX.sub("/", candidate)

    # Special case - let's strip off any windowsy drive letter preamble
    drive_sep_pos = norm.find(":")
    if drive_sep_pos >= 0:
        norm = norm[drive_sep_pos + 1 :]

    # Let's trim trailing slash (unless it's root)
    norm = norm if len(norm) <= 1 else norm.rstrip(PATH_SEP_CHARS)

    return norm


def reduce_mounts(inputs):
    """
    Given a set of input paths intended to be mounted, reduce this to the subset that need mounting.
    (eg. avoid mounting children of folders already being mounted).
    """
    has_mount_or_parent_mount = {}
    reduced_mounts = []

    # make sure our inputs are sorted so that we get to parents before children
    inputs.sort()

    for mount in inputs:
        parent, child = parse_parent_child(mount)
        is_root = parent is None
        # if we're mounting a folder other than root, we should strip trailing separators
        parent_trimmed = parent.rstrip(PATH_SEP_CHARS) if not is_root else None
        if not has_mount_or_parent_mount_recurse(
            parent_trimmed, reduced_mounts, has_mount_or_parent_mount
        ):
            candidate = mount.rstrip(PATH_SEP_CHARS) if not is_root else child
            reduced_mounts.append(candidate)

    return reduced_mounts


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
        parent, _ = parse_parent_child(candidate)
        if parent is None:
            status = False
        else:
            status = has_mount_or_parent_mount_recurse(
                parent, explicit_mounts, has_mount_or_parent_mount_map
            )

    # Store in the memo and return
    has_mount_or_parent_mount_map[candidate] = status
    return status


def parse_parent_child(mount):
    mount_trimmed = mount.rstrip(PATH_SEP_CHARS)
    match = UNKNOWN_PATH_TYPE_SPLIT_TO_PARENT_AND_CHILD_REGEX.match(mount_trimmed)
    if match is None:
        return None, mount

    # strip away trailing slash on parent
    parent = match.group("parent")
    if parent is not None:
        parent_trimmed = parent.rstrip(PATH_SEP_CHARS)
        # deal with the "root" folder - we don't want to strip that slash
        if len(parent_trimmed) > 0 and not parent_trimmed.endswith(":"):
            parent = parent_trimmed

    return parent, match.group("child")


def map_host_to_container(host_paths, container_root_target):
    """
    Takes a set of host paths, and computes the list of host paths needing mounting, and
    a mapping of all related host_paths (those explicitly provided, and those needing mounting)
    to container paths.
    """
    min_mounts = reduce_mounts(host_paths)
    map_host_to_container_paths = {}

    for path in host_paths:
        container_path = transform_to_nix_path(path)
        if container_path.startswith("/"):
            container_path = container_root_target + container_path
        map_host_to_container_paths[path] = container_path

    return min_mounts, map_host_to_container_paths
