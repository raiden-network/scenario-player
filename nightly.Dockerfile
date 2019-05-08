FROM raidennetwork/raiden:nightly

COPY . /app/scenario-player
RUN /opt/venv/bin/pip3 install -r /app/scenario-player/requirements.txt /app/scenario-player

WORKDIR ["/app"]

ENTRYPOINT ["/opt/venv/bin/scenario-player"]
