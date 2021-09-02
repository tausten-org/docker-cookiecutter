import sys
import argparse

docker_preamble = ["run", "-it", "--rm", "--user", '"$(id -u):$(id -g)"']
cookiecutter_cmd_and_preamble = ["cookiecutter", "-o", "/out"]

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
        or template.startswith("hg:") \
        or template.startswith("bb:") \
        or template.startswith("gl:"):
        return False
    
    return True

# For the options that we're attempting to process and pass through,
# see: https://cookiecutter.readthedocs.io/en/1.7.3/advanced/cli_options.html
def prepare_option_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', '-V', action='store_true')
    parser.add_argument('--no-input', action='store_true')
    parser.add_argument('--checkout', '-c')
    parser.add_argument('--directory')
    parser.add_argument('--verbose', '-v', action='store_true')
    parser.add_argument('--replay', action='store_true')
    parser.add_argument('--overwrite-if-exists', '-f', action='store_true')
    parser.add_argument('--skip-if-file-exists', '-s', action='store_true')
    parser.add_argument('--output-dir', '-o')
    parser.add_argument('--config-file')
    parser.add_argument('--default-config', action='store_true')
    parser.add_argument('--debug-file')
    parser.add_argument('TEMPLATE_AND_EXTRA', nargs=argparse.REMAINDER)
    return parser

def parse(args):
    parser = prepare_option_parser()
    ns, _ = parser.parse_known_args(args)
    
    template = None
    if len(ns.TEMPLATE_AND_EXTRA) > 0:
        template = ns.TEMPLATE_AND_EXTRA[0]
    
    extra = None
    if len(ns.TEMPLATE_AND_EXTRA) > 1:
        extra = ns.TEMPLATE_AND_EXTRA[1:]

    return (ns, template, extra)

def quote_if_necessary(val):
    if not val.startswith('"') and not val.startswith("'") and " " in val:
        if "'" in val:
            return '"' + val + '"'
        return "'" + val + "'"

    return val

def cookiecutter_to_docker_args(args):
    ns, template, extra = parse(args)

    result = [] + docker_preamble

    # volume mount for template if it's a filesystem input
    if is_fs_template(template):
        new_template = "/in"
        result += docker_v_args(template, new_template)
        template = new_template

    # special handling of output - the preamble with always specify `-o /out`, and 
    # we just need to make sure we include the volume mount as needed
    host_output_folder = ns.output_dir if ns.output_dir else '"$(pwd)"'
    result += docker_v_args(host_output_folder, "/out")
    
    # volume mount for config-file
    config_file = None
    if ns.config_file:
        config_file = "/user_cookiecutter_config.yml"
        result += docker_v_args(ns.config_file, config_file)
    
    # volume mount for debug-file
    debug_file = None
    if ns.debug_file:
        debug_file = "/cookiecutter_debug.log"
        result += docker_v_args(ns.debug_file, debug_file)

    # TODO: need to add the docker image

    result += cookiecutter_cmd_and_preamble

    # Handle all the flag args
    if ns.no_input: result.append('--no-input')
    if ns.verbose: result.append('--verbose')
    if ns.replay: result.append('--replay')
    if ns.overwrite_if_exists: result.append('--overwrite-if-exists')
    if ns.skip_if_file_exists: result.append('--skip-if-file-exists')
    if ns.default_config: result.append('--default-config')

    # handle the parameterized args
    if ns.checkout: result += ['--checkout', ns.checkout]
    if ns.directory: result += ['--directory', ns.directory]
    if ns.config_file: result += ['--config-file', config_file]
    if ns.debug_file: result += ['--debug-file', debug_file]

    # add the (possibly updated) template param
    if template is not None and not template.isspace():
        result.append(template)

    # add any extra context
    if extra is not None and len(extra) > 0:
        result += extra

    return [quote_if_necessary(x) for x in result]

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
