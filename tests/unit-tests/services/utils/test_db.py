import json

from unittest import mock

import pytest
from scenario_player.services.common.factories import construct_flask_app
from scenario_player.services.utils.db import JSONRedis
from scenario_player.exceptions.db import CorruptedDBEntry


db_import_path = 'scenario_player.services.utils.db'


@pytest.fixture
def app():
    app = construct_flask_app(test_config={"TESTING": True})
    with app.app_context():
        yield


@mock.patch(f'{db_import_path}.Redis.hmget')
@mock.patch(f'{db_import_path}.Redis.hmset')
class TestJSONRedis:

    @mock.patch(f'{db_import_path}.JSONRedis.set_json')
    def test_tset_method_calls_set_json_with_table_attr_and_given_encode_kwargs(self, mock_set_json, _, __, app):
        instance = JSONRedis('test_table')

        instance.tset('my-key', {'key': 'value'})
        expected_args = ('test_table', 'my-key', {'key': 'value'})
        mock_set_json.assert_called_once()
        actual_args, _ = mock_set_json.call_args
        assert actual_args == expected_args

    @mock.patch(f'{db_import_path}.JSONRedis.get_json')
    def test_tget_method_calls_get_json_with_table_attr_and_given_decode_kwargs(self, mock_get_json, _, __, app):
        instance = JSONRedis('test_table')

        instance.tget('my-key')
        expected_args = ('test_table', 'my-key')
        mock_get_json.assert_called_once()
        actual_args, _ = mock_get_json.call_args
        assert actual_args == expected_args

    def test_set_json_calls_hmset_method_with_json_encoded_string(self, patched_hmset, __, app):
        instance = JSONRedis('test_table')
        instance.set_json('test_table', 'key', {'k': 'v'})
        patched_hmset.assert_called_once_with('test_table', {"key": '{"k": "v"}'})

    @mock.patch(f'{db_import_path}.json.loads')
    def test_get_json_applies_decoding_options_to_json_string(self, mock_loads, _, patched_hmget, app):
        patched_hmget.return_value = '{"sth": "blah"}'
        instance = JSONRedis('test_table', decoding_options={'option': 'value'})
        instance.get_json('test_table', 'key')
        mock_loads.assert_called_once_with('{"sth": "blah"}', option='value')

    @mock.patch(f'{db_import_path}.json.dumps')
    def test_set_json_applies_encoding_options_to_json_string(self, mock_dumps, _, __, app):
        instance = JSONRedis('test_table', encoding_options={'option': 'value'})
        instance.set_json('test_table', 'key', {'sth': 'blah'})
        mock_dumps.assert_called_once_with({'sth': 'blah'}, option='value')

    @mock.patch(f'{db_import_path}.json.dumps')
    def test_encode_kwargs_passed_directly_to_set_json_take_precedence_over_encoding_options_stored_in_instance(self, mock_dumps, _, __, app):
        instance = JSONRedis('test_table', encoding_options={'option': 'value'})
        instance.set_json('test_table', 'key', {'sth': 'blah'}, option='nugget')
        mock_dumps.assert_called_once_with({'sth': 'blah'}, option='nugget')

    @mock.patch(f'{db_import_path}.json.loads')
    def test_decode_kwargs_passed_directly_to_get_json_take_precedence_over_decoding_options_stored_in_instance(self, mock_loads, _, patched_hmget, app):
        patched_hmget.return_value = '{"sth": "blah"}'
        instance = JSONRedis('test_table', decoding_options={'option': 'value'})
        instance.get_json('test_table', 'key', option='nugget')
        mock_loads.assert_called_once_with('{"sth": "blah"}', option='nugget')

    @mock.patch(f'{db_import_path}.json.dumps', side_effect=ValueError('from mock'))
    def test_tset_method_propagates_ValueError_during_json_encoding_from_downstream(self, _, __, ___, app):
        instance = JSONRedis('test_table')
        with pytest.raises(ValueError, match=r".*from mock.*"):
            instance.tset('key', {'k': 'v'})

    @mock.patch(f'{db_import_path}.json.loads', side_effect=json.JSONDecodeError('from mock', "", 0))
    def test_tget_method_raises_CorruptedDBEntry_exception_if_JSONDecodeError_is_raised_downstream(self, _, __, ___, app):
        instance = JSONRedis('test_table')
        with pytest.raises(CorruptedDBEntry):
            instance.tget('key')

    @mock.patch(f'{db_import_path}.json.dumps', side_effect=ValueError('from mock'))
    def test_set_json_propagates_ValueError_during_json_encoding(self, _, __, ___, app):
        instance = JSONRedis('test_table')
        with pytest.raises(ValueError, match=r".*from mock.*"):
            instance.set_json('test_table', 'key', {"k": "v"})

    @mock.patch(f'{db_import_path}.json.loads', side_effect=json.JSONDecodeError('from mock', "", 0))
    def test_get_json_propagates_JSONDecodeError(self, _, __, ___, app):
        instance = JSONRedis('test_table')
        with pytest.raises(json.JSONDecodeError, match=r".*from mock.*"):
            instance.get_json('test_table', 'key')
