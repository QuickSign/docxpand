FROM nvidia/cuda:11.7.1-cudnn8-devel-ubuntu22.04
RUN apt-get -y update && DEBIAN_FRONTEND=noninteractive apt-get -y install --no-install-recommends git curl make cmake xz-utils pkg-config build-essential wget locales libxi-dev libxrandr-dev libfreetype6-dev libfontconfig1-dev python3.10-dev libjpeg-dev libcairo2-dev liblcms2-dev libboost-dev libopenjp2-7-dev libopenjp2-tools libleptonica-dev imagemagick qpdf pdftk libdmtx0b mesa-common-dev libgl1-mesa-dev libglu1-mesa-dev libgl1-mesa-glx libmagic1
# poetry environment variable (https://python-poetry.org/docs/configuration/#using-environment-variables)
ENV POETRY_VERSION=1.6.1 \
    # make poetry install to this location
    POETRY_HOME="/opt/poetry" \
    # avoid poetry creating virtual environment in the project's root
    POETRY_VIRTUALENVS_IN_PROJECT=false \
    # do not ask any interactive question
    POETRY_NO_INTERACTION=1

# install poetry - respects $POETRY_VERSION & $POETRY_HOME
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="${POETRY_HOME}/bin:$PATH"
COPY . /app
WORKDIR /app
RUN poetry install
