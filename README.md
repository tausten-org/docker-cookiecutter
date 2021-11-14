# docker-cookiecutter

## Table of Contents

- [docker-cookiecutter](#docker-cookiecutter)
  - [Table of Contents](#table-of-contents)
  - [About](#about)
  - [Getting Started](#getting-started)
    - [Prerequisites](#prerequisites)
    - [Usage (cookiecutter)](#usage-cookiecutter)
    - [Usage (suggest)](#usage-suggest)
    - [Examples](#examples)
  - [Maintenance](#maintenance)
    - [Contributing](#contributing)
    - [Testing](#testing)
    - [CI/CD](#cicd)
    - [Support](#support)
  - [License](#license)
  - [Acknowledgements](#acknowledgements)

## About

Cookiecutter in docker with helpers for constructing / adjusting the docker commandline for execution.

## Getting Started

### Prerequisites

- docker
- (currently if you will use the `suggest` script's recommendation directly) *nix shell for executing docker..  otherwise, be prepared to do a bit of extra translation of the suggested commandline to its Windows equivalent

### Usage (cookiecutter)

At the basic level, these are the necessary steps to leverage the container successfully.

1. Identify the `cookiecutter` commandline you'd like to execute
   - eg. `cookiecutter -o /tmp/out -f https://github.com/BruceEckel/HelloCookieCutter1`
2. Consider identify any local filesystem inputs and/or outputs the command will be using:
   - eg. `-o /tmp/out`
3. Identify the user:group you intend to manage ownership and access to these local resources
   - eg. `echo "$(id -u):$(id -g)"`
4. Pre-create local output target (if it doesn't already exist)
   - eg. `mkdir -p /tmp/out`
5. Prepare the `docker run` portion of the command execution:
   - eg. `docker run -it --rm --user "$(id -u):$(id -g)" --mount type=bind,source=/tmp/out,target=/tmp/out tausten/docker-cookiecutter:latest`
   - NOTE: the `--user` is very important in order for the output to have the correct ownership
6. Combine the two together and execute:
   - eg. `docker run -it --rm --user "$(id -u):$(id -g)" --mount type=bind,source=/tmp/out,target=/tmp/out tausten/docker-cookiecutter:latest cookiecutter -o /tmp/out -f https://github.com/BruceEckel/HelloCookieCutter1`

### Usage (suggest)

For help in coming up with the full docker commandline, you can lean on the `suggest` helper script. To use it, do the following:

1. Come up with simplist form of your docker command to to start:
   - eg. `docker run tausten/docker-cookiecutter:latest cookiecutter -o /tmp/out -f /some/local/template`
2. Execute the `suggest` script with this whole simplified commandline as input:
   - eg. `docker run -it --rm tausten/docker-cookiecutter:latest suggest docker run tausten/docker-cookiecutter:latest cookiecutter -o /tmp/out -f /some/local/template`
3. Look over the suggested commandline that is returned, make any adjustments you see fit, then execute that
   - eg. `docker run -it --rm --user "$(id -u):$(id -g)" --mount type=bind,source=/some/local/template,target=/in --mount type=bind,source=/tmp/out,target=/out tausten/docker-cookiecutter:latest cookiecutter -o /out --overwrite-if-exists /in`

### Examples

Here are some simple examples based on the [Cookiecutter Docs](https://cookiecutter.readthedocs.io/en/1.7.3/usage.html).

- Get cookiecutter version, help, etc...:

```sh
# in general, you can execute cookiecutter commands as you normally would, with the caveat that any local filesystem-based resources need special attention as described previously
$ docker run -it --rm tausten/docker-cookiecutter:latest cookiecutter --version
$ docker run -it --rm tausten/docker-cookiecutter:latest cookiecutter --help
```

- Simple local template example - `cookiecutter cookiecutter-pypackage/`

```sh
# Get suggestion for how to execute your desired command
$ docker run -it --rm tausten/docker-cookiecutter:latest suggest docker run tausten/docker-cookiecutter:latest cookiecutter cookiecutter-pypackage/

# Review the returned suggestion:
docker run -it --rm --user "$(id -u):$(id -g)" --mount type=bind,source="$(pwd)",target=/h/rel tausten/docker-cookiecutter:latest cookiecutter -o /h/rel /h/rel/cookiecutter-pypackage

# If it looks good, go ahead and execute it..  otherwise, make your desired adjustments then proceed.
```

- Github template example - `cookiecutter gh:audreyfeldroy/cookiecutter-pypackage`

```sh
# Get suggestion for how to execute your desired command
$ docker run -it --rm tausten/docker-cookiecutter:latest suggest docker run tausten/docker-cookiecutter:latest cookiecutter gh:audreyfeldroy/cookiecutter-pypackage

# Review the returned suggestion:
docker run -it --rm --user "$(id -u):$(id -g)" --mount type=bind,source="$(pwd)",target=/h/rel tausten/docker-cookiecutter:latest cookiecutter -o /h/rel gh:audreyfeldroy/cookiecutter-pypackage

# If it looks good, go ahead and execute it..  otherwise, make your desired adjustments then proceed.
```

## Maintenance

Preferred mode is to use VSCode + the devcontainer.

### Contributing

If you're a developer, feel free to clone/fork the repo and submit PR requests. Please include at least one unit test covering the bug, and showing that your fix addresses the problem.

### Testing

Testing is done with pytest, and tests are gathered under the `tests` folder. You can execute the tests via the makefile with `make test.unit`, `make test.integration`, or `make test` (which will execute any unit and integration tests).

### CI/CD

This repo itself leverages github actions to perform basic CI/CD for maintainance. The repo is set up as a python (+ vscode devcontainer) development and uses pytest for testing.

### Support

Please report any issues/feature requests/feedback [here](https://github.com/tausten/docker-cookiecutter/issues). Please be detailed and provide reproduction steps, examples, etc..

## License

See [LICENSE](LICENSE) for more information.

## Acknowledgements

Special thanks to the maintainers of the following resources that were used during the development of `docker-cookiecutter`.

- [docker](https://www.docker.com/) - container tech
- [cookiecutter](https://github.com/cookiecutter/cookiecutter) - the excellent original project template support
- [pytest-cookies](https://github.com/hackebrot/pytest-cookies) - fixture for simpler testing of cookiecutters
- [Cookie Patcher](https://pypi.org/project/cookiepatcher) - nice project for making it easier to re-apply templates to a project
- [Python Project Wizard](https://zillionare.github.io/cookiecutter-pypackage/) - a cookiecutter template for setting up python projects
