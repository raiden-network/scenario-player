import pathlib

import pytest

from scenario_player.utils.files.parsing import parse_architecture, parse_platform, parse_version


VERSIONS = [
    'v142.44.2',
    'v2.462.0',
    'v21.4.222',
]
ARCHITECTURES = [
    'x86_64',
    'i386',
    'armv6',
    'armv7',
    'armv8',
]

PLATFORMS = [
    'linux',
    'macOS',
    'win',
    'cygwin',
]

@pytest.mark.parametrize(
    'parse_func, expected',
    argvalues=[
        (parse_architecture, 'arch'),
        (parse_platform, 'platform'),
        (parse_version, 'version')
    ]
)
@pytest.mark.parametrize('version', argvalues=VERSIONS)
@pytest.mark.parametrize('arch', argvalues=ARCHITECTURES)
@pytest.mark.parametrize('platform', argvalues=PLATFORMS)
def test_parse_func_always_parses_correctly_independent_of_version_platform_and_architecture(
        version, arch, platform, parse_func, expected, tmp_path):
    """Make sure the parsing function always parses the expected value from a given path.

    The pattern expected is raiden_<version>_<platform>_<architecture>[.<ext>]

    This assumes a valid pattern for the `path`'s file name.
    """
    fname_sans_ext = f"raiden_{version}_{platform}_{arch}"
    fname_with_ext = f"raiden_{version}_{platform}_{arch}.extension"

    for fname in (fname_sans_ext, fname_with_ext):
        assert parse_func(tmp_path.joinpath('some_dir', fname)) == locals().get(expected, None)


@pytest.mark.parametrize('parse_func', argvalues=[parse_architecture, parse_platform, parse_version])
def test_parse_function_returns_None_if_no_match_was_found(parse_func, tmp_path):
    assert parse_func(tmp_path) is None