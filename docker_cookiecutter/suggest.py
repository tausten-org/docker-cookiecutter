import argparse
import os
import sys

from docker_cookiecutter import pathmap
from docker_cookiecutter.templates import (
    TemplateSourceInfo,
    decode_template_sources,
    encode_template_sources,
)


# Work around python's lack of consts
class CONST(object):
    __slots__ = ()
    DOCKER_PREAMBLE = ["docker", "run", "-it", "--rm"]
    DOCKER_USER = ["--user", '"$(id -u):$(id -g)"']
    DOCKER_ARGS_TO_PRUNE = DOCKER_PREAMBLE + ["-i", "-t"]
    CC = "cookiecutter"
    CCS = "cookiecutters"
    CC_REPLAY_FILE = "/.cookiecutter_replay/in.json"


CONST = CONST()


def split_docker_from_cookiecutter(given):
    got_docker = got_cookiecutter = []

    for i, v in enumerate(given):
        if v == CONST.CC or v == CONST.CCS:
            got_docker = given[:i]
            got_cookiecutter = given[i:]
            break
    else:
        got_docker = given

    return got_docker, got_cookiecutter


def docker_mount_args(host: str, container: str) -> "list[str]":
    if host.startswith(".") or not host.startswith("/") and "$(pwd)" not in host:
        tail = host.lstrip("./") if not host.startswith("..") else host
        host = '"$(pwd)"'
        if len(tail) > 0:
            host += "/" + quote_if_necessary(tail)

    container = quote_if_necessary(container)

    return ["--mount", "type=bind,source=" + host + ",target=" + container]


def is_fs_template(template: str) -> bool:
    if template is None or template.isspace():
        return False

    if template.startswith("file://"):
        return True

    if (
        "" == template
        or "://" in template
        or template.startswith("gh:")
        or template.startswith("bb:")
        or template.startswith("gl:")
    ):
        return False

    return True


def parse_docker(args):
    # TODO: split things out better (i.e. handle any conflicting volume mounts)
    image = args[-1]

    # hacky pruning of the --rm and -it because we'll add them back explicitly later
    extra = [x for x in args[:-1] if x not in CONST.DOCKER_ARGS_TO_PRUNE]

    return [], image, extra


# For the options that we're attempting to process and pass through,
# see: https://cookiecutter.readthedocs.io/en/1.7.3/advanced/cli_options.html
def prepare_cookiecutter_option_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", "-V", action="store_true")
    parser.add_argument("--no-input", action="store_true")
    parser.add_argument("--checkout", "-c")
    parser.add_argument("--directory")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--replay", action="store_true")
    parser.add_argument("--replay-file")
    parser.add_argument("--overwrite-if-exists", "-f", action="store_true")
    parser.add_argument("--skip-if-file-exists", "-s", action="store_true")
    parser.add_argument("--output-dir", "-o")
    parser.add_argument("--config-file")
    parser.add_argument("--default-config", action="store_true")
    parser.add_argument("--debug-file")
    parser.add_argument("ITEM_AND_EXTRA", nargs=argparse.REMAINDER)
    return parser


def parse_cookiecutter(args):
    parser = prepare_cookiecutter_option_parser()
    ns, _ = parser.parse_known_args(args)

    item = None
    if len(ns.ITEM_AND_EXTRA) > 0:
        item = ns.ITEM_AND_EXTRA[0]

    extra = None
    if len(ns.ITEM_AND_EXTRA) > 1:
        extra = ns.ITEM_AND_EXTRA[1:]

    return (ns, item, extra)


def quote_if_necessary(val: str) -> str:
    if (
        not val.startswith('"')
        and not val.startswith("'")
        and (" " in val or "$" in val)
    ):
        if "'" in val:
            return '"' + val + '"'
        return "'" + val + "'"

    return val


def get_root_basename(filepath):
    return os.path.join("/", os.path.basename(filepath))


def get_from_path_map_quoted(path_map: pathmap.PathMap, path: str) -> str:
    return quote_if_necessary(path_map.get_container_path(path))


def cookiecutter_to_docker_args(
    args: "list[str]",
    container_abs: str = "/h/abs",
    container_rel: str = "/h/rel",
    container_dd: str = "dd",
):
    docker, cookiecutter = split_docker_from_cookiecutter(args)

    _, docker_image, docker_extra = parse_docker(docker[1:])
    cc_parsed, cc_template, cc_extra = parse_cookiecutter(cookiecutter[1:])

    result = CONST.DOCKER_PREAMBLE + docker_extra + CONST.DOCKER_USER

    cc_templates = decode_template_sources(cc_template)

    # Build up a path map of host-to-container paths we'll use for volume mounting and
    # argument adjustments later
    path_map_builder = pathmap.PathMapBuilder()

    # Add the file-based template(s) to teh builder
    for template_path in [
        t.template for t in cc_templates if is_fs_template(t.template)
    ]:
        path_map_builder.add_path(template_path)

    # Add the other path-based arguments to the builder
    if not cc_parsed.output_dir:
        cc_parsed.output_dir = "."
    path_map_builder.add_path(cc_parsed.output_dir)

    if cc_parsed.config_file:
        path_map_builder.add_path(cc_parsed.config_file)

    if cc_parsed.debug_file:
        path_map_builder.add_path(cc_parsed.debug_file)

    # Now that we've accumulated all the paths we need, build the path map so we can look mounts
    # and mappings up
    path_map = path_map_builder.build(container_abs, container_rel, container_dd)

    # Add the mounts
    for mount_host_path in path_map.get_mounts():
        result.extend(
            docker_mount_args(
                mount_host_path, path_map.get_container_path(mount_host_path)
            )
        )

    # volume mount for replay-file
    # This is a special case in that although cookiecutter docs indicate this is a supported
    # commandline option, it doesn't appear to actually be supported in latest...  so we can
    # fake it into existence by volume mount trickery knowing where the file ends up
    if cc_parsed.replay_file:
        result.extend(docker_mount_args(cc_parsed.replay_file, CONST.CC_REPLAY_FILE))

    # Handle containerizing the templates param
    container_mapped_templates = []
    for template_info in cc_templates:
        # If it's a filesystem input, update to container-path
        if is_fs_template(template_info.template):
            container_mapped_templates.append(
                TemplateSourceInfo(path_map.get_container_path(template_info.template))
            )
        else:
            container_mapped_templates.append(template_info)

    cc_template = encode_template_sources(container_mapped_templates)

    # wrap up the docker portion with the image
    result.append(docker_image)

    # Build up the cookiecutter(s) portion now
    result.append(CONST.CC if len(cc_templates) < 2 else CONST.CCS)

    # Add the output folder
    result.extend(["-o", get_from_path_map_quoted(path_map, cc_parsed.output_dir)])

    # Handle all the flag args
    if cc_parsed.no_input:
        result.append("--no-input")
    if cc_parsed.verbose:
        result.append("--verbose")
    if cc_parsed.replay:
        result.append("--replay")
    if cc_parsed.overwrite_if_exists:
        result.append("--overwrite-if-exists")
    if cc_parsed.skip_if_file_exists:
        result.append("--skip-if-file-exists")
    if cc_parsed.default_config:
        result.append("--default-config")

    # handle the parameterized args
    if cc_parsed.checkout:
        result.extend(["--checkout", cc_parsed.checkout])
    if cc_parsed.directory:
        result.extend(["--directory", cc_parsed.directory])
    if cc_parsed.config_file:
        result.extend(
            ["--config-file", get_from_path_map_quoted(path_map, cc_parsed.config_file)]
        )
    if cc_parsed.debug_file:
        result.extend(
            ["--debug-file", get_from_path_map_quoted(path_map, cc_parsed.debug_file)]
        )

    # add the (possibly updated) template param
    if cc_template is not None and len(cc_template) > 0 and not cc_template.isspace():
        result.append(cc_template)

    # add any extra context
    if cc_extra is not None and len(cc_extra) > 0:
        result.extend(cc_extra)

    return result


if __name__ == "__main__":
    # It is required that the commandline being passed in be of the form:
    #  {bunch of docker-related commandline args} {dockerImage} cookiecutter {cookiecutterArgs}
    #
    # in this way we can use the 'cookiecutter' as boundary between the two worlds,
    # and get out {dockerImage} so that we can put it on proper place in regenerated cmdline
    #
    # so we get input like:
    #
    #  docker run -it --rm tausten/exp-cc:0.0.1 cookiecutter -f https://github.com/audreyfeldroy/cookiecutter-pypackage.git
    #
    # and we can properly transform that into:
    #
    #  docker run -it --rm --user "$(id -u):$(id -g)" -v "$(pwd)":/out tausten/exp-cc:0.0.1 cookiecutter -o /out --overwrite-if-exists https://github.com/audreyfeldroy/cookiecutter-pypackage.git
    #
    sys.exit(" ".join(cookiecutter_to_docker_args(sys.argv[1:])))  # pragma: no cover
