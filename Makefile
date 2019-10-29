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

install-dev:
	pip install ".[dev]"

install-raiden-develop:
	pip uninstall raiden -y
	pip install git+https://github.com/raiden-network/raiden.git@develop

unit-tests:
	pytest --cov=scenario_player

integration-tests:
	@echo Ran integration tests.

test-harness: unit-tests integration-tests

install-post-commit-hook:
	cat .post-commit > .git/hooks/post-commit
	chmod +x .git/hooks/post-commit
	@echo "Isort and black are now automatically applied to commited .py files!"