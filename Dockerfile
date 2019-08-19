# Set the python version to use. This may be overriden during the build process by passing
# --build-arg PY_VERSION=<desired version>
# Note that the desired version must be of pattern <major>.<minor> .
ARG PY_VERSION=3.7
FROM python:$PY_VERSION AS cache

RUN pip install raiden

FROM python:${PY_VERSION}

ARG PY_VERSION

# Copy raiden repository and site-packages from build cache
COPY --from=cache /usr/local/lib/python${PY_VERSION}/dist-packages /usr/local/lib/python${PY_VERSION}/dist-packages

#  Copy SP folder and install.
CMD mkdir /scenario-player
ADD . /scenario-player

RUN pip install ./scenario-player

ENTRYPOINT ["/usr/local/bin/scenario_player"]
