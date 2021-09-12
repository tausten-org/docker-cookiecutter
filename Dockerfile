ARG PYTHON_VARIANT="3-alpine"
FROM python:${PYTHON_VARIANT} AS build

# Take care of pip requirements
COPY requirements.txt /tmp/pip-tmp/
RUN pip3 --disable-pip-version-check --no-cache-dir install -r /tmp/pip-tmp/requirements.txt \
   && rm -rf /tmp/pip-tmp

# Need git installed
RUN apk --update add git less openssh mercurial && \
    rm -rf /var/lib/apt/lists/* && \
    rm /var/cache/apk/*

# Install the custom python package from source
COPY . /tmp/pypackage/
RUN pip3 install /tmp/pypackage \
    && rm -rf /tmp/pypackage

RUN mkdir -p /.cookiecutters/ \
    && chmod 777 /.cookiecutters

RUN mkdir -p /.cookiecutter_replay \
    && chmod 777 /.cookiecutter_replay

WORKDIR /app
COPY ./entrypoint.sh /entrypoint.sh

ENTRYPOINT [ "/entrypoint.sh" ]
CMD [ "cookiecutter", "--help" ]
