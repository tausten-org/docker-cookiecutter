from typing import AnyStr

from cookiecutter.main import cookiecutter
from docker_cookiecutter.templates import decode_template_sources


def cookiecutters(templates: AnyStr):
    sources = decode_template_sources(templates)
    result = []

    for t in sources:
        result.append(cookiecutter(t.template))

    return result
