from unittest import mock
from stat import S_IRUSR, S_IWUSR, S_IXUSR

import pytest

from scenario_player.releases import RAIDEN_RELEASES_URL, RAIDEN_RELEASES_LATEST_FILE
from scenario_player.releases import get_latest_release, is_executable


class TestGetLatestRelease:

    @mock.patch('scenario_player.releases.requests.get', autospec=True)
    def test_get_latest_release_is_cached(self, mock_request):
        get_latest_release()
        get_latest_release()
        mock_request.assert_called_once()

    @mock.patch('scenario_player.releases.requests', autospec=True)
    def test_get_latest_release_sends_request_to_correct_url(self, mock_request):
        mock_request.configure_mock(text=str())
        get_latest_release()
        mock_request.assert_called_once_with(RAIDEN_RELEASES_URL + RAIDEN_RELEASES_LATEST_FILE)


INPUT_OUTPUT = {
    'read-only': (S_IRUSR, False),
    'read-write': (S_IRUSR & S_IWUSR, False),
    'read-write-exec': (S_IRUSR & S_IWUSR & S_IXUSR, True),
    'read-exec': (S_IRUSR & S_IXUSR, True),
    'write-exec': (S_IWUSR & S_IXUSR, True),
    'exec-only': (S_IXUSR, True),
    'write-only': (S_IWUSR, False),
}


@pytest.mark.parametrize('set_bits, result', INPUT_OUTPUT.values(), ids=list(INPUT_OUTPUT.keys()))
def test_is_executable_detects_bits_correctly(set_bits, result, tmp_path):
    test_file = tmp_path.joinpath('test.file')
    test_file.touch()
    test_file.chmod(set_bits)
    assert is_executable(test_file) is result