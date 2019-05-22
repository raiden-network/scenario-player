.PHONY: lint style black isort isort-check flake8 clean

clean:
	find . -name '*.pyc' -delete

black:
	black scenario_player

isort:
	isort --recursive scenario_player

isort-check:
	isort --recursive --diff --check-only scenario_player

flake8:
	flake8 scenario_player

style: isort black

lint: flake8 isort-check
