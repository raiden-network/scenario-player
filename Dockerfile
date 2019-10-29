FROM python:3.7-slim AS compile-image

LABEL maintainer=devops@brainbot.com

################################################################################
# COMPILATION STAGE (compile-image)                                            #
################################################################################
#
# Install the raiden client and scenario player from their github repositoires.
#
# This stage supports the following, optional build args:
#
#   - RAIDEN_VERSION (default: develop)
#     The version of the Raiden client to run the nightlies against.
#
#   - SP_VERSION (default: master)
#     The version of the SP to run the nightlies with.
#
#   - SCENARIOS_VERSION (default: develop)
#     The branch or commit from which the scenarios should be checked out of the
#     raiden repository.
#
# The build stage uses a virtual environment to install the raiden client
# and scenario player tool, which can be copied to subsequent build stages,
# in order to reduce image size.

ARG RAIDEN_VERSION=develop
ARG SP_VERSION=master
ARG SCENARIOS_VERSION=develop

# Set up the build stage
RUN apt-get update
RUN apt-get install -y --no-install-recommends build-essential gcc git
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install the Scenario Player
RUN git clone https://github.com/raiden-network/scenario-player.git /sp
WORKDIR /sp
RUN git checkout ${SP_VERSION}
RUN pip install .

# Install the Raiden Client
RUN git clone https://github.com/raiden-network/raiden.git /raiden
WORKDIR /raiden
RUN git checkout ${RAIDEN_VERSION}
RUN pip install .

# Install scenarios
RUN git checkout ${SCENARIOS_VERSION}
RUN cp -r /raiden/raiden/tests/scenarios /scenarios

FROM python:3.7-slim as execution-image
WORKDIR /

################################################################################
# PREPARATION STEP (execution-image)                                           #
################################################################################
#
# Copies the raiden client, scenario player and scenario defnition files from the
# compilation stage, and configure further environment variables required to run
# the nightlies.
#
# This stage copies the virtual environment created in the previous stage,
# and prepends its location to the $PATH environment variable.
#
# Scenario definition files are also copied from the previous stage, and the
# working directory is set to /scenarios, allowing users to specify the name
# of the scenario yaml without a path.

# Copy virtual env and scenario definition files.
COPY --from=compile-image /opt/venv /opt/venv
COPY --from=compile-image /scenarios /scenarios
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /scenarios
ENTRYPOINT ["scenario_player", "--data-path", "/raw"]