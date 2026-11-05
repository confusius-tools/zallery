# syntax=docker/dockerfile:1.7
# The environment mybinder.org builds for the "Launch in Binder" buttons of the docs
# examples: zallery, what the examples import, and JupyterLab opening the
# percent-format scripts as notebooks.
FROM python:3.13-slim-bookworm

# Binder requires a user named jovyan with UID 1000.
ARG NB_USER=jovyan
ARG NB_UID=1000
ENV USER=${NB_USER} \
    NB_UID=${NB_UID} \
    HOME=/home/${NB_USER}

RUN groupadd -g ${NB_UID} ${NB_USER} \
 && useradd --create-home --uid ${NB_UID} --gid ${NB_UID} --shell /bin/bash ${NB_USER}

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# Use the image's Python, which matches `.python-version`. If the two ever differ,
# the build fails here instead of downloading another Python.
ENV UV_PYTHON_DOWNLOADS=never

COPY --chown=${NB_UID}:${NB_UID} . ${HOME}/
USER ${NB_USER}
WORKDIR ${HOME}

# zallery and the libraries its examples import (the `docs` group), without the dev
# tools. notebook (>=7 bundles JupyterLab) provides the `jupyter notebook` CLI that
# repo2docker launches; jupytext and ipykernel come with zallery.
RUN uv sync --frozen --no-dev --group docs \
 && uv pip install notebook

# Server-side: register jupytext as the contents manager so percent-format .py
# files are exposed as notebooks over the API.
RUN mkdir -p ${HOME}/.jupyter \
 && printf '%s\n' \
        'c.ServerApp.contents_manager_class = "jupytext.TextFileContentsManager"' \
        'c.ContentsManager.preferred_jupytext_formats_read = "py:percent"' \
        > ${HOME}/.jupyter/jupyter_server_config.py

# Frontend: make JupyterLab open .py files with the Jupytext Notebook viewer
# by default, so ?urlpath=lab/tree/<file>.py lands in a notebook view.
RUN mkdir -p ${HOME}/.jupyter/labconfig \
 && printf '%s\n' \
        '{' \
        '  "@jupyterlab/docmanager-extension:plugin": {' \
        '    "defaultViewers": {' \
        '      "python": "Jupytext Notebook"' \
        '    }' \
        '  }' \
        '}' \
        > ${HOME}/.jupyter/labconfig/default_setting_overrides.json

ENV PATH=${HOME}/.venv/bin:${PATH}
