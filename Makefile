.PHONY: lint style black black-check isort isort-check flake8

black:
	black scenario_player

isort:
	isort scenario_player

isort-check:
	isort --diff --check-only scenario_player

black-check:
	black --check --diff scenario_player

flake8:
	flake8 scenario_player

pylint:
	pylint scenario_player

style: isort black

lint: mypy flake8 pylint black-check isort-check

format: isort black

mypy:
	mypy scenario_player tests

install:
	poetry install

unit-tests:
	pytest --cov=scenario_player

test: unit-tests

install-post-commit-hook:
	cat .post-commit > .git/hooks/post-commit
	chmod +x .git/hooks/post-commit
	@echo "Isort and black are now automatically applied to commited .py files!"
