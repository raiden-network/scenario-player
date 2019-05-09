import pathlib

import pytest


@pytest.fixture
def tmpdir_path(tmpdir):
    """Return the tmpdir fixture as a pathlib.Path object."""
    return pathlib.Path(tmpdir.abspath())
