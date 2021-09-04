import os
import sys
import argparse

docker_preamble = ["docker", "run", "-it", "--rm"]
docker_user = ["--user", '"$(id -u):$(id -g)"']
cookiecutter_cmd_and_preamble = ["cookiecutter", "-o", "/out"]

def split_docker_from_cookiecutter(given):
    got_docker = got_cookiecutter = []
    
    for i, v in enumerate(given):
        if v == "cookiecutter":
            got_docker = given[:i]
            got_cookiecutter = given[i:]
            break
    else:
        got_docker = given

    return got_docker, got_cookiecutter

def docker_v_args(host, container):
    if host.startswith(".") or not host.startswith("/") and '$(pwd)' not in host:
        host = '"$(pwd)"/' + host
    return ["-v", host + ":" + container]

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

docker_args_to_prune = docker_preamble + ["-i", "-t"]

def parse_docker(args):
    # TODO: split things out better (i.e. handle any conflicting volume mounts)
    image = args[-1]

    # hacky pruning of the --rm and -it because we'll add them back explicitly later
    extra = [x for x in args[:-1] if x not in docker_args_to_prune]

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

    result = docker_preamble + docker_extra + docker_user

    # volume mount for template if it's a filesystem input
    if is_fs_template(cc_template):
        new_template = "/in"
        result += docker_v_args(cc_template, new_template)
        cc_template = new_template

    # special handling of output - the preamble with always specify `-o /out`, and 
    # we just need to make sure we include the volume mount as needed
    host_output_folder = cc_parsed.output_dir if cc_parsed.output_dir else '"$(pwd)"'
    result += docker_v_args(host_output_folder, "/out")
    
    # volume mount for config-file
    config_file = None
    if cc_parsed.config_file:
        config_file = get_root_basename(cc_parsed.config_file)
        result += docker_v_args(cc_parsed.config_file, config_file)
    
    # volume mount for debug-file
    debug_file = None
    if cc_parsed.debug_file:
        debug_file = get_root_basename(cc_parsed.debug_file)
        result += docker_v_args(cc_parsed.debug_file, debug_file)
    
    # volume mount for replay-file
    replay_file = None
    if cc_parsed.replay_file:
        replay_file = get_root_basename(cc_parsed.replay_file)
        result += docker_v_args(cc_parsed.replay_file, replay_file)

    # wrap up the docker portion with the image
    result += [ docker_image ]

    result += cookiecutter_cmd_and_preamble

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
    if cc_parsed.replay_file: result += ['--replay-file', replay_file]

    # add the (possibly updated) template param
    if cc_template is not None and not cc_template.isspace():
        result.append(cc_template)

    # add any extra context
    if cc_extra is not None and len(cc_extra) > 0:
        result += cc_extra

    return quote_args(result)

if __name__ == "__main__":
    # TODO: require that the commandline being passed in be of the form:
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
