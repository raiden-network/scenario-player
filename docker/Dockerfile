################################################################################
# Scenario-Player Executable Docker Image                                      #
################################################################################
#
# Builds an executable image of the scenario-player, offering options to customize
# the raiden and scenario versions to run against.
ARG SP_VERSION=master
ARG RAIDEN_VERSION=develop
ARG SCENARIOS_VERSION=develop


################################################################################
# COMPILE & INSTALL SCENARIO-PLAYER (sp-image)                                 #
################################################################################
#
# Install the scenario player at version ${SP_VERSION} from its github
# repository.
#
# This stage supports the following, optional build args:
#
#   - SP_VERSION (default: master)
#     The version of the SP to run the nightlies with. It must be a `git ref`
#     (tag, branch name, commit sha) present on the github repository.
#
# This stage also pulls the virtual environment from the raiden-image stage,
# as it installs the scenario-player via pip.


FROM python:3.7 AS sp-image
ARG SP_VERSION

RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Pull the Git repository for the scenario-player, and install it to the venv
RUN git clone https://github.com/raiden-network/scenario-player.git /sp
WORKDIR /sp
RUN git checkout ${SP_VERSION}
RUN pip install .

################################################################################
# COMPILE & INSTALL RAIDEN (raiden-image)                                                #
################################################################################
#
# Install the Raiden client from the `raidennetwork/raiden` GitHub repository.
#
# This stage supports the following, optional build args:
#
#   - RAIDEN_VERSION (default: develop)
#     The version of the Raiden client to run the nightlies against. This must be
#     a valid git-ref.
#
# This stage comes with a virtual environment; it needs to be copied to
# sub-sequent build stages if they install one or more packages via `pip`.
# It also always needs to be copied in the `execution-image` build stage.

# FROM python:3.7 AS raiden-image
ARG RAIDEN_VERSION

# Copy the virtual env from the sp-image build stage.
# COPY --from=sp-image /opt/venv /opt/venv
# ENV PATH="/opt/venv/bin:$PATH"

# Install raiden from Github
RUN pip uninstall raiden -y
RUN pip install git+https://github.com/raiden-network/raiden.git@${RAIDEN_VERSION}
RUN pip install --force-reinstall urwid!=2.1.0

################################################################################
# DOWNLOAD SCENARIOS (scenarios-image)                                         #
################################################################################
#
# Download scenarios provisioned by the raiden github repository.
#
# This stage supports the following, optional build args:
#
#   - SCENARIOS_VERSION (default: develop)
#     The branch or commit from which the scenarios should be checked out of the
#     raiden repository.
#

# FROM python:3.7 AS scenarios-image
ARG SCENARIOS_VERSION

# Fetch and copy scenarios
RUN git clone https://github.com/raiden-network/raiden.git /raiden
WORKDIR /raiden
RUN git checkout ${SCENARIOS_VERSION}
RUN cp -r /raiden/raiden/tests/scenarios /scenarios


################################################################################
# BUILD EXECUTION IMAGE (execution-image)                                      #
################################################################################
#
# This stage copies the virtual environment from the build stage the venv was
# last modified in and prepends its path to the $PATH environment variable.
#
# Scenario definition files are copied from the scenarios-image, and the
# working directory is set to /scenarios, allowing users to specify the name
# of the scenario yaml without a path.
#
# Finally, it sets the entrypoint for this image at the `scenario_player` command.
#

# FROM python:3.7 as execution-image
ARG SP_VERSION
ARG RAIDEN_VERSION
ARG SCENARIOS_VERSION

LABEL maintainer=devops@brainbot.com
LABEL org.label-schema.name="Raide Network Scenario Player"
LABEL org.label-schema.description="An executable Scenario-player instance, complete with a raiden client and scenarios."
LABEL org.label-schema.version="0.6.5"
LABEL org.label-schema.vcs-url="https://github.com/raiden-network/scenario-player"
LABEL org.label-schema.vendor="Brainbot Laboratories"

LABEL org.label-schema.build-args.raiden_version=${RAIDEN_VERSION}
LABEL org.label-schema.build-args.sp_version=${SP_VERSION}
LABEL org.label-schema.build-args.scenarios_version=${SCENARIOS_VERSION}

# Copy virtual environment and update $PATH
# COPY --from=sp-image /opt/venv /opt/venv
# ENV PATH="/opt/venv/bin:$PATH"

# Copy scenarios
# COPY --from=scenarios-image /scenarios /scenarios

# Set the workdir and entrypoint.
WORKDIR /scenarios
ENTRYPOINT ["scenario_player"]