# Set the python version to use. This may be overriden during the build process by passing
# --build-arg PY_VERSION=<desired version>
# Note that the desired version must be of pattern <major>.<minor> .
ARG PY_VERSION=3.7
FROM python:$PY_VERSION AS cache

# Clone raiden repo and switch to its `develop` branch
RUN git clone https://github.com/raiden-network/raiden /raiden
RUN git --git-dir /raiden/.git checkout develop

# Install raiden's development dependencies.
RUN pip install -r /raiden/requirements/requirements-dev.txt

# Install the raiden package
RUN pip install ./raiden

FROM python:$PY_VERSION
# Copy raiden repository and site-packages from build cache
COPY --from=cache /raiden /raiden
COPY --from=cache /usr/local/lib/python$PY_VERSION/dist-packages /usr/local/lib/python$PY_VERSION/dist-packages

#  Copy SP folder and install.
ADD scenario-player /scenario-player

RUN pip install ./scenario-player

ENTRYPOINT ["/usr/local/bin/scenario_player"]
