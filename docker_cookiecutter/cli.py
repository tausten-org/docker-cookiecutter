"""Console script for docker_cookiecutter."""

import sys

from docker_cookiecutter.suggest import cookiecutter_to_docker_args


def main():
    print(" ".join(cookiecutter_to_docker_args(sys.argv[1:])))


if __name__ == "__main__":
    main()  # pragma: no cover
