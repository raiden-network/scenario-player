import pathlib
from unittest.mock import patch, Mock, PropertyMock

import pytest

from scenario_player.scenario import ScenarioYAML
from scenario_player.setup.nodes.flags import RaidenFlags, OPTION_TYPE
from scenario_player.exceptions.setup import NotInstalled

ETH_RPC_ENDPOINT = "127.0.0.:6666"
TEST_NET = "testnet"


@pytest.fixture
def raiden_flags(wallet, minimal_yaml_dict, tmp_path):
    with patch("scenario_player.scenario.yaml.safe_load", return_value=minimal_yaml_dict):
        return RaidenFlags(
            loaded_yaml=ScenarioYAML(minimal_yaml_dict, tmp_path),
            index=1,
            chain=TEST_NET,
            client_addr=ETH_RPC_ENDPOINT,
            run_number=1,
        )


class RaidenFlagsTestBase:
    @pytest.fixture(autouse=True)
    def setup_raiden_flags_test_class(self, raiden_flags, minimal_yaml_dict, tmp_path):
        self.instance = raiden_flags
        self.loaded_yaml = minimal_yaml_dict
        self.data_dir = tmp_path


class TestRaidenFlagsGetOptionMethod(RaidenFlagsTestBase):

    @pytest.mark.parametrize("given, expected", argvalues=[(bool, OPTION_TYPE.SWITCH), (None, OPTION_TYPE.SWITCH), ("something", "something"), (11, 11)])
    def test_get_option_returns_switch_sentinel_value_for_qualified_value(self, given, expected):
        """Stating cli options without a value, or passing a boolean as their value
        identifies them as cli switches. Any other value is returned as is."""
        self.instance._yaml.nodes.default_options.dict["default_options"] = {"a-test-value": given}
        assert self.instance.get_option("a-test-value") == expected

    def test_get_option_prioritizes_node_options_over_default_node_options(self):
        self.instance._yaml.nodes.dict["node_options"] = {"1": {"a-test-value": "a"}}
        self.instance._yaml.nodes.default_options.dict["default_options"] = {"a-test-value": "b"}
        assert self.instance.get_option("a-test-value") == "a"

    def test_get_option_falls_back_to_default_options_if_option_not_in_node_options(self):
        self.instance._yaml.nodes.dict["node_options"] = {}
        self.instance._yaml.nodes.default_options.dict["default_options"] = {"a-test-value": "b"}
        assert self.instance.get_option("a-test-value") == "b"

        # Make sure this also works if the node index exists, but no option is found under the given name for it.
        self.instance._yaml.nodes.dict["node_options"] = {"1": {}}
        assert self.instance.get_option("a-test-value") == "b"

    def test_get_option_returns_missing_option_sentinel_if_the_queried_option_was_not_defined(self):
        assert self.instance.get_option("chuggaloo") is OPTION_TYPE.MISSING

    def test_get_option_prioritizes_pfs_address_stated_in_node_config_section_over_other_section_statements(self):
        """Make sure the load-priority of the cli setting `pathfinding-service-address` is as follows:

            1. <scenario definition file>.nodes.node_options.<node_index>.pathfinding-service-address
            2. <scenario definition file>.nodes.default_options.pathfinding-service-address
            3. <scenario definition file>.settings.services.pfs.url

        """
        expected_global_pfs = "THE-pfs-addr"
        expected_default = "my-pfs-addr"
        expected_node_specific = "other-pfs-addr"

        self.instance._yaml.settings.services.pfs.dict["url"] = expected_global_pfs
        assert self.instance.get_option("pathfinding-service-address") == expected_global_pfs, "should have loaded from <scenario definition file>.settings.services.pfs.url"

        self.instance._yaml.nodes.default_options.dict["default_options"] = {"pathfinding-service-address": expected_default}
        assert self.instance.get_option("pathfinding-service-address") == expected_default, "should have loaded from <scenario definition file>.nodes.default_options"

        self.instance._yaml.nodes.dict["node_options"] = {"1": {"pathfinding-service-address": expected_node_specific}}
        assert self.instance.index == 1, "Sanity check failed - assumed instance under test has node index 1, but didn't"
        assert self.instance.get_option("pathfinding-service-address") == expected_node_specific, "should have loaded from <scenario definition file>.nodes.node_options.1"

    def test_get_option_prioritizes_gas_price_stated_in_node_config_section_over_other_section_statements(self):
        """Make sure the load-priority of the cli setting `gas-price` is as follows:

            1. <scenario definition file>.nodes.node_options.<node_index>.gas-price
            2. <scenario definition file>.nodes.default_options.gas-price
            3. <scenario definition file>.settings.gas_price

        """
        expected_global = "global-gp"
        expected_default = "default-gp"
        expected_node_specific = "node-gp"

        self.instance._yaml.settings.dict["gas-price"] = expected_global
        assert self.instance.get_option("gas-price") == expected_global, "should have loaded from <scenario definition file>.settings.gas_price"

        self.instance._yaml.nodes.default_options.dict["default_options"] = {"gas-price": expected_default}
        assert self.instance.get_option("gas-price") == expected_default, "should have loaded from <scenario definition file>.nodes.default_options"

        self.instance._yaml.nodes.dict["node_options"] = {"1": {"gas-price": expected_node_specific}}
        assert self.instance.index == 1, "Sanity check failed - assumed instance under test has node index 1, but didn't"
        assert self.instance.get_option("gas-price") == expected_node_specific, "should have loaded from <scenario definition file>.nodes.node_options.1"


@patch("scenario_player.setups.nodes.flags.socket.socket", autospec=True)
class TestRaidenFlagsAPIAddressProperty(RaidenFlagsTestBase):

    def test_property_prioritizes_value_set_in_scenario_definition_file(self, mock_socket):
        assert self.instance._api_address is None, "Sanity check failed - value for _api_address already present!"

        unexpected = "localhost:999"
        expected = "localhost:666"
        self.instance._yaml.settings.node_options[self.instance.index] = {"api-address": expected}
        self.instance._yaml.settings.default_options = {"api-address": unexpected}
        assert self.instance.api_address == expected, "Did not load expected API address!"
        assert mock_socket.called is False, "Called socket library, but should not have!"

    def test_property_falls_back_to_default_node_options_if_node_option_does_not_contain_api_address(self, mock_socket):
        assert self.instance._api_address is None, "Sanity check failed - value for _api_address already present!"

        expected = "localhost:666"
        self.instance._yaml.settings.node_options[self.instance.index] = {}
        self.instance._yaml.settings.default_options = {"api-address": expected}
        assert self.instance.api_address == expected, "Did not load expected API address!"
        assert mock_socket.called is False, "Called socket library, but should not have!"

    def test_property_randomly_assigns_port_using_socket_library_if_api_address_is_not_defined_anywhere(self, mock_socket):
        """When `api-address` isn't defined anywhere, we need to create a netloc address ourselves.

        For this, we need to find any random free port and use it to generate an api address on
        the localhost.
        """
        assert self.instance._api_address is None, "Sanity check failed - value for _api_address already present!"
        expected = 666
        mock_socket.configure_mock(**{"getsockname.return_value": [None, expected]})
        assert self.instance.api_address == "127.0.0.1:666"


class TestRaidenFlagsExecutableProperty(RaidenFlagsTestBase):

    @pytest.mark.parametrize("version", ["latest", "1.5.6"])
    @patch("scenario_player.setup.nodes.flags.RaidenExecutable.download")
    def test_property_calls_raiden_executable_class_when_specifying_version(self, mock_download, version):
        self.instance._yaml.nodes.dict["raiden_version"] = version
        mock_download.return_value = pathlib.Path(f"raiden_{version}")
        assert self.instance.executable == mock_download.return_value

    @patch("scenario_player.setup.nodes.flags.shutil.which", return_value=None)
    def test_property_raises_exception_when_specifying_local_but_no_executable_is_found_on_path(self):
        self.instance._yaml.nodes.dict["raiden_version"] = "local"
        with pytest.raises(NotInstalled):
            self.instance.executable

    @patch("scenario_player.setup.nodes.flags.shutil.which", return_value="/my/executable")
    def test_property_returns_result_of_which_command_if_version_is_local(self):
        self.instance._yaml.nodes.dict["raiden_version"] = "local"
        expected = pathlib.Path(mock_which.return_value)
        assert self.instance.executable == expected


class TestRaidenNonOverridables(RaidenFlagsTestBase):
    """Test non-overridable cli flags.

    These are present on the RaidenFlags object as properties, and their logic contained therein.

    The properties to test include:

        - --address
        - --keystore-path
        - --password-file
        - --log-file
        - --data-dir
        - --network-id

    """

    def test_password_returns_an_empty_str(self):
        assert self.instance.password == ""

    @patch("scenario_player.setup.nodes.flags.to_checksum_address", return_value="checksummed")
    @patch("scenario_player.setup.nodes.flags.RaidenFlags.keystore", new_callable=PropertyMock(return_value=pathlib.Path("checksum.keystore")))
    def test_address_returns_stem_attribute_of_keystore_property(self, mock_prop, mock_to_checksum):
        """The :attr:`RaidenFlags.address` property must return a checksummed address of the account managed by a node.

        It should return the `stem` attribute of the :attr:`RaidenFlags.keystore` property to do so.
        This will trigger the underlying keystore to be created if it does not already exist.
        """
        assert self.instance.address == "checksummed"
        mock_to_checksum.assert_called_once_with(mock_prop.return_value)

    @patch("scenario_player.setup.nodes.flags.RaidenFlags.address", new_callable=PropertyMock(return_value="checksum"))
    def test_password_file_creates_new_pw_file_if_none_exists(self, mock_address):
        assert self.data_dir.joinpath("checksum.password").exists() is False, "Sanity check failed - a password file exists already!"
        actual = self.instance.password_file
        expected = self.data_dir.joinpath(f"{mock_address.return_value}.password")
        assert actual == expected, "Returned password file path is not at expected location!"
        assert actual.exists(), "Returned path is correct, but it was not created!"

    @patch("scenario_player.setup.nodes.flags.RaidenFlags.address", new_callable=PropertyMock(return_value="checksum"))
    @patch("scenario_player.setup.nodes.flags.RaidenFlags.keystore", new_callable=PropertyMock(return_value=pathlib.Path("checksum.keystore")))
    def test_password_file_looks_up_existing_file_in_correct_dir(self, _, mock_addr):
        """The property :attr:`RaidenFlags.password_file` looks for any existing password files in the correct dir.

        It also uses the :attr:`RaidenFlags.address` property to construct the name of the password file.
        """
        expected = self.data_dir.joinpath("checksum.password")
        expected.touch()
        assert self.instance.password_file == expected
        mock_addr.assert_called_once()

    @patch("scenario_player.setup.nodes.flags.RaidenFlags.password", new_callable=PropertyMock(return_value="custom_value"))
    def test_password_file_contains_return_value_of_password_property(self, mock_prop):
        assert self.instance.password_file.read_text() == mock_prop.return_value
        mock_prop.assert_called_once()

    @patch("scenario_player.setup.nodes.flags.create_keystore", return_value=pathlib.Path("checksum.wallet"))
    def test_keystore_property_creates_new_keystore_if_none_exists(self, mock_create_keystore):
        expected = mock_create_keystore.return_value
        actual = self.instance.keystore
        assert actual == expected
        mock_create_keystore.assert_called_once_with(
            run_rumber=self.instance.run_number,
            index=self.instance.index,
            scenario_name=self.instance._yaml.name,
            password=self.instance.password,
        )
