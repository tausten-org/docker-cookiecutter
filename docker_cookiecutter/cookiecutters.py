from cookiecutter.main import cookiecutter

from docker_cookiecutter.templates import decode_template_sources


# TODO: Actually implement this..  right now, this is mostly a stub
def cookiecutters(templates: str) -> "list[str]":
    sources = decode_template_sources(templates)
    result = []

    for t in sources:
        result.append(cookiecutter(t.template))

    return result
