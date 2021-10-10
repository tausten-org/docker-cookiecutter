import re

PATH_SEP_CHARS = "/\\"

# Regex to detect groups of repeated separator-like chars, and pull out the first char as a capture group
CONSECUTIVE_UNKNOWN_SEP_CHARS_REGEX = re.compile(r"([/\\])(?:[/\\]+)")

# Regex to split a path (of unkown origin - windows or linux) into (parent, sep, child) groups
UNKNOWN_PATH_TYPE_SPLIT_REGEX = re.compile(r"^(.*[/\\]+)([^/\\]+[/\\]*)$")


def normalize_path(candidate):
    """
    Path origin is unknown, but we wish to collapse consecutive separators down to singles
    and trim any final trailing separator (but only if the path is not for "root" folder)
    """
    norm = CONSECUTIVE_UNKNOWN_SEP_CHARS_REGEX.sub(r"\1", candidate).rstrip(
        PATH_SEP_CHARS
    )

    # Special case - we've hit a root path, so add the slash back
    if len(norm) == 0 or norm.endswith(":"):
        norm += candidate[-1]

    return norm


def reduce_mounts(inputs):
    """
    Given a set of input paths intended to be mounted, reduce this to the subset that need mounting.
    (eg. avoid mounting children of folders already being mounted).
    """
    explicit_mounts = set([normalize_path(x) for x in inputs])
    has_mount_or_parent_mount = {}
    reduced_mounts = []

    for mount in explicit_mounts:
        parent, _ = parse_parent_child(mount)
        if not has_mount_or_parent_mount_recurse(
            parent, explicit_mounts, has_mount_or_parent_mount
        ):
            reduced_mounts.append(mount)

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
        status = has_mount_or_parent_mount_recurse(
            parent, explicit_mounts, has_mount_or_parent_mount_map
        ) or has_mount_or_parent_mount_recurse(
            parent.rstrip(PATH_SEP_CHARS),
            explicit_mounts,
            has_mount_or_parent_mount_map,
        )

    # Store in the memo and return
    has_mount_or_parent_mount_map[candidate] = status
    return status


def parse_parent_child(mount):
    match = UNKNOWN_PATH_TYPE_SPLIT_REGEX.match(mount)
    if match is None:
        return None, mount

    return match.group(0), match.group(1)
