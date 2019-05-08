from unittest import mock

import pytest

from requests import Response

from raiden.scenario_player.services.releases.utils import download_archive


class DownloadArchiveTestCase:

    @mock.patch('raiden.scenario_player.services.releases.utils.requests.get')
    def test_downloading_archive_for_release_which_does_not_exist_locally_fetches_archive_from_raiden_cloud(self, mock_get):
        CLOUD_STORAGE_URL = ''
        RELEASE_VERSION = ''
        EXPECTED_URL = f'{CLOUD_STORAGE_URL}/{RELEASE_VERSION}-linux_amd64.tar.gz'
        download_archive(RELEASE_VERSION)
        mock_get.assert_called_once_with(EXPECTED_URL)

    @mock.patch('raiden.scenario_player.services.releases.utils.requests.get')
    def test_function_is_idempotent_by_default(self, mock_get):
        RELEASE_VERSION = ''
        download_archive(RELEASE_VERSION)
        assert mock_get.call_count == 1

        download_archive(RELEASE_VERSION)
        assert not mock_get.call_count == 1

    @mock.patch('raiden.scenario_player.services.releases.utils.requests.get')
    def test_func_downloads_archive_again_if_param_cached_is_false(self, mock_get):
        download_archive(RELEASE_VERSION)
        mock_get.reset_mock()

        download_archive(RELEASE_VERSION, cached=False)
        mock_get.assert_called_once_with(EXPECTED_URL)

    @mock.patch('raiden.scenario_player.services.releases.utils.requests.get')
    def test_func_raises_InvalidReleaseVersion_if_it_cannot_be_found_on_raiden_cloud(self, mock_get):
        mock_resp = Response()
        mock_resp.status_code = 404
        mock_get.return_value = mock_resp
        with pytest.raises(InvalidReleaseVersion):
            download_archive('42')
