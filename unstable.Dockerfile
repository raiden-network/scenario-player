FROM raidennetwork/raiden:unstable

RUN apt-get update && apt-get install -y git

COPY . /app/scenario-player
RUN /opt/venv/bin/pip3 install -r /app/scenario-player/requirements.txt /app/scenario-player

EXPOSE 5001


ENTRYPOINT ["/opt/venv/bin/scenario-player"]
