.PHONY: lint style black black-check isort isort-check flake8

black:
	black scenario_player

isort:
	isort --recursive scenario_player

isort-check:
	isort --recursive --diff --check-only scenario_player

black-check:
	black --check --diff scenario_player

flake8:
	flake8 scenario_player

style: isort black

lint: flake8 black-check isort-check
