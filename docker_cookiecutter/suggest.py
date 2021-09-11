import os
import sys
import argparse
from docker_cookiecutter.templates import TemplateSourceInfo, decode_template_sources, encode_template_sources

# Work around python's lack of consts
class CONST(object):
    __slots__ = ()
    DOCKER_PREAMBLE = ["docker", "run", "-it", "--rm"]
    DOCKER_USER = ["--user", '"$(id -u):$(id -g)"']
    DOCKER_ARGS_TO_PRUNE = DOCKER_PREAMBLE + ["-i", "-t"]
    CC = "cookiecutter"
    CCS = "cookiecutters"
    CC_OUT = ["-o", "/out"]
    CC_CMD_AND_PREAMBLE = [CC] + CC_OUT
    CCS_CMD_AND_PREAMBLE = [CCS] + CC_OUT
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

def docker_mount_args(host, container):
    if host.startswith(".") or not host.startswith("/") and '$(pwd)' not in host:
        host = '"$(pwd)"/' + host
    # return ["-v", host + ":" + container]
    return ["--mount", "type=bind,source=" + host + ",target=" + container]

def is_fs_template(template):
    if template is None or template.isspace():
        return False

    if template.startswith("file://"):
        return True

    if "" == template \
        or "://" in template \
        or template.startswith("gh:") \
        or template.startswith("bb:") \
        or template.startswith("gl:"):
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
    parser.add_argument('--version', '-V', action='store_true')
    parser.add_argument('--no-input', action='store_true')
    parser.add_argument('--checkout', '-c')
    parser.add_argument('--directory')
    parser.add_argument('--verbose', '-v', action='store_true')
    parser.add_argument('--replay', action='store_true')
    parser.add_argument('--replay-file')
    parser.add_argument('--overwrite-if-exists', '-f', action='store_true')
    parser.add_argument('--skip-if-file-exists', '-s', action='store_true')
    parser.add_argument('--output-dir', '-o')
    parser.add_argument('--config-file')
    parser.add_argument('--default-config', action='store_true')
    parser.add_argument('--debug-file')
    parser.add_argument('ITEM_AND_EXTRA', nargs=argparse.REMAINDER)
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

def quote_if_necessary(val):
    if not val.startswith('"') and not val.startswith("'") and " " in val:
        if "'" in val:
            return '"' + val + '"'
        return "'" + val + "'"

    return val

def quote_args(args):
    return [quote_if_necessary(x) for x in args]

def get_root_basename(filepath):
    return os.path.join("/", os.path.basename(filepath))

def cookiecutter_to_docker_args(args):
    docker, cookiecutter = split_docker_from_cookiecutter(args)

    _, docker_image, docker_extra = parse_docker(docker[1:])
    cc_parsed, cc_template, cc_extra = parse_cookiecutter(cookiecutter[1:])
    cc_templates = decode_template_sources(cc_template)
    new_templates = []

    result = CONST.DOCKER_PREAMBLE + docker_extra + CONST.DOCKER_USER

    for i, t in enumerate(cc_templates):
        # volume mount for template if it's a filesystem input
        if is_fs_template(cc_template):
            new_template = "/in"
            if len(cc_templates) > 1:
                new_template += f"-{i}"
            
            result += docker_mount_args(t.template, new_template)
            new_templates.append(TemplateSourceInfo(new_template))
        else:
            new_templates.append(t)

    cc_template = encode_template_sources(new_templates)

    # special handling of output - the preamble with always specify `-o /out`, and 
    # we just need to make sure we include the volume mount as needed
    host_output_folder = cc_parsed.output_dir if cc_parsed.output_dir else '"$(pwd)"'
    result += docker_mount_args(host_output_folder, "/out")
    
    # volume mount for config-file
    config_file = None
    if cc_parsed.config_file:
        config_file = get_root_basename(cc_parsed.config_file)
        result += docker_mount_args(cc_parsed.config_file, config_file)
    
    # volume mount for debug-file
    debug_file = None
    if cc_parsed.debug_file:
        debug_file = get_root_basename(cc_parsed.debug_file)
        result += docker_mount_args(cc_parsed.debug_file, debug_file)
    
    # volume mount for replay-file 
    # This is a special case in that although cookiecutter docs indicate this is a supported
    # commandline option, it doesn't appear to actually be supported in latest...  so we can
    # fake it into existence by volume mount trickery knowing where the file ends up
    if cc_parsed.replay_file:
        result += docker_mount_args(cc_parsed.replay_file, CONST.CC_REPLAY_FILE)

    # wrap up the docker portion with the image
    result += [ docker_image ]

    result += CONST.CC_CMD_AND_PREAMBLE if len(cc_templates) < 2 else CONST.CCS_CMD_AND_PREAMBLE

    # Handle all the flag args
    if cc_parsed.no_input: result.append('--no-input')
    if cc_parsed.verbose: result.append('--verbose')
    if cc_parsed.replay: result.append('--replay')
    if cc_parsed.overwrite_if_exists: result.append('--overwrite-if-exists')
    if cc_parsed.skip_if_file_exists: result.append('--skip-if-file-exists')
    if cc_parsed.default_config: result.append('--default-config')

    # handle the parameterized args
    if cc_parsed.checkout: result += ['--checkout', cc_parsed.checkout]
    if cc_parsed.directory: result += ['--directory', cc_parsed.directory]
    if cc_parsed.config_file: result += ['--config-file', config_file]
    if cc_parsed.debug_file: result += ['--debug-file', debug_file]

    # add the (possibly updated) template param
    if cc_template is not None and len(cc_template) > 0 and  not cc_template.isspace():
        result.append(cc_template)

    # add any extra context
    if cc_extra is not None and len(cc_extra) > 0:
        result += cc_extra

    return quote_args(result)

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
