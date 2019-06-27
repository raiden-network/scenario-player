.PHONY: lint style black black-check isort isort-check flake8

black:
	black scenario_player analysis

isort:
	isort --recursive scenario_player analysis

isort-check:
	isort --recursive --diff --check-only scenario_player analysis

black-check:
	black --check --diff scenario_player analysis

flake8:
	flake8 scenario_player analysis

style: isort black

lint: flake8 black-check isort-check
