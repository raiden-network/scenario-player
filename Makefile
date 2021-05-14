.PHONY: black black-check flake8 format have-poetry install install-dev isort isort-check lint mypy pylint style tests

black:
	poetry run black scenario_player

black-check:
	poetry run black --check --diff scenario_player

flake8:
	poetry run flake8 scenario_player

isort:
	poetry run isort scenario_player

isort-check:
	poetry run isort --diff --check-only scenario_player

pylint:
	poetry run pylint scenario_player

tests:
	poetry run pytest --cov=scenario_player

mypy:
	poetry run mypy scenario_player tests

have-poetry:
	@command -v poetry > /dev/null 2>&1 || (echo "poetry is required. Installing." && python3 -m pip install --user poetry)

install: have-poetry
	poetry install --no-dev

install-dev: have-poetry
	poetry install

install-local-raiden:
	echo "This only works when Raiden is installed in ../raiden"
	echo "If pip install -e ."
	sed -i 's/^raiden = {.*/raiden = { path = "..\/raiden"}/' pyproject.toml
	poetry update raiden
	poetry install
	echo "If you get pkg_resources.ContextualVersionConflict, you need to update your egg-info by calling 'pip install -e ../raiden'."

format: style

lint: mypy flake8 pylint black-check isort-check

style: isort black

test: tests
