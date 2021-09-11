from dataclasses import dataclass
from typing import AnyStr


"""Gather complete set of information about the template source.

template - the base uri of the template (eg. directory, or repository address)
checkout - [optional] - branch, tag or commit within the repo
directory - [optional] - directory within the repo
"""


@dataclass
class TemplateSourceInfo:
    template: AnyStr
    checkout: AnyStr = None
    directory: AnyStr = None


# Work around python's lack of consts
class CONST(object):
    __slots__ = ()
    TEMPLATE_DELIM = ",,"
    COMPONENT_DELIM = ","
    CHECKOUT_PREFIX = "checkout="
    DIRECTORY_PREFIX = "directory="


CONST = CONST()


def encode_template_sources(sources):
    templates = []
    for t in sources:
        template = t.template
        if t.checkout:
            template += CONST.COMPONENT_DELIM + CONST.CHECKOUT_PREFIX + t.checkout
        if t.directory:
            template += CONST.COMPONENT_DELIM + CONST.DIRECTORY_PREFIX + t.directory
        templates.append(template)
    return CONST.TEMPLATE_DELIM.join(templates)


def decode_template_sources(template):
    result = []
    if template is not None and len(template) > 0:
        template_strings = template.split(CONST.TEMPLATE_DELIM)

        for t in template_strings:
            template = None
            checkout = None
            directory = None

            for c in t.split(CONST.COMPONENT_DELIM):
                if c.startswith(CONST.CHECKOUT_PREFIX):
                    checkout = c[len(CONST.CHECKOUT_PREFIX) :]
                elif c.startswith(CONST.DIRECTORY_PREFIX):
                    directory = c[len(CONST.DIRECTORY_PREFIX) :]
                else:
                    template = c

            result.append(TemplateSourceInfo(template, checkout, directory))

    return result
