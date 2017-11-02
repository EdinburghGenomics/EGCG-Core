import os
import json
import pytest
from unittest.mock import patch
from tests import FakeRestResponse, TestEGCG
from egcg_core import rest_communication
from egcg_core.util import check_if_nested
from egcg_core.exceptions import RestCommunicationError


def rest_url(endpoint):
    return 'http://localhost:4999/api/0.1/' + endpoint + '/'


def ppath(extension):
    return 'egcg_core.rest_communication.Communicator.' + extension


test_endpoint = 'an_endpoint'
test_nested_request_content = {'data': ['some', {'test': 'content'}]}
test_flat_request_content = {'key1': 'value1', 'key2': 'value2'}
test_patch_document = {
    '_id': '1337', '_etag': 1234567, 'uid': 'a_unique_id', 'list_to_update': ['this', 'that', 'other']
}


def fake_request(method, url, **kwargs):
    if kwargs.get('files'):
        if 'json' in kwargs:
            raise Exception
        if 'data' in kwargs and check_if_nested(kwargs['data']):
            raise Exception
    return FakeRestResponse(status_code=200, content=test_nested_request_content)


patched_response = patch(
    'requests.request',
    side_effect=fake_request
)


auth = ('a_user', 'a_password')


class TestRestCommunication(TestEGCG):
    def setUp(self):
        self.comm = rest_communication.Communicator(auth=auth, baseurl='http://localhost:4999/api/0.1')

    def test_api_url(self):
        assert self.comm.api_url('an_endpoint') == rest_url('an_endpoint')

    def test_parse_query_string(self):
        query_string = 'http://a_url?this=that&other={"another":"more"}&things=1'
        dodgy_query_string = 'http://a_url?this=that?other=another'

        assert self.comm._parse_query_string('http://a_url') == {}
        assert self.comm._parse_query_string(query_string) == {
            'this': 'that', 'other': '{"another":"more"}', 'things': '1'
        }

        with pytest.raises(RestCommunicationError) as e:
            self.comm._parse_query_string(dodgy_query_string)
            assert str(e) == 'Bad query string: ' + dodgy_query_string

        with pytest.raises(RestCommunicationError) as e2:
            self.comm._parse_query_string(query_string, requires=['thangs'])
            assert str(e2) == query_string + " did not contain all required fields: ['thangs']"

    def test_detect_files_in_json(self):
        json_no_files = {'k1': 'v1', 'k2': 'v2'}
        obs_files, obs_json = self.comm._detect_files_in_json(json_no_files)
        file_path = os.path.join(self.assets_path, 'test_to_upload.txt')
        assert obs_files is None
        assert obs_json == json_no_files

        json_with_files = {'k1': 'v1', 'k2': ('file', file_path)}
        obs_files, obs_json = self.comm._detect_files_in_json(json_with_files)
        assert obs_files == {'k2': (file_path, b'test content', 'text/plain')}
        assert obs_json == {'k1': 'v1'}

        json_list = [json_with_files, json_with_files]
        obs_files, obs_json = self.comm._detect_files_in_json(json_list)
        assert obs_files == [
            {'k2': (file_path, b'test content', 'text/plain')},
            {'k2': (file_path, b'test content', 'text/plain')}
        ]
        assert obs_json == [{'k1': 'v1'}, {'k1': 'v1'}]

    @patched_response
    def test_req(self, mocked_response):
        json_content = ['some', {'test': 'json'}]
        response = self.comm._req('METHOD', rest_url(test_endpoint), json=json_content)
        assert response.status_code == 200
        assert json.loads(response.content.decode('utf-8')) == response.json() == test_nested_request_content
        mocked_response.assert_called_with('METHOD', rest_url(test_endpoint), auth=auth, json=json_content)

    def test_get_documents_depaginate(self):
        docs = (
            FakeRestResponse(content={'data': ['this', 'that'], '_links': {'next': {'href': 'an_endpoint?max_results=101&page=2'}}}),
            FakeRestResponse(content={'data': ['other', 'another'], '_links': {'next': {'href': 'an_endpoint?max_results=101&page=3'}}}),
            FakeRestResponse(content={'data': ['more', 'things'], '_links': {}})
        )
        with patch(ppath('_req'), side_effect=docs) as mocked_req:
            assert self.comm.get_documents('an_endpoint', all_pages=True, max_results=101) == [
                'this', 'that', 'other', 'another', 'more', 'things'
            ]
            assert all([a[0][1].startswith(rest_url('an_endpoint')) for a in mocked_req.call_args_list])
            assert [a[1] for a in mocked_req.call_args_list] == [
                # Communicator.get_content passes ints
                {'params': {'page': 1, 'max_results': 101}, 'quiet': False},
                # url parsing passes strings, but requests removes the quotes anyway
                {'params': {'page': '2', 'max_results': '101'}, 'quiet': False},
                {'params': {'page': '3', 'max_results': '101'}, 'quiet': False}
            ]

        docs = [
            FakeRestResponse(
                content={
                    'data': ['data%s' % d],
                    '_links': {'next': {'href': 'an_endpoint?max_results=101&page=%s' % d}}
                }
            )
            for d in range(1, 1200)
        ]
        docs.append(FakeRestResponse(content={'data': ['last piece'], '_links': {}}))

        with patch(ppath('_req'), side_effect=docs):
            ret = self.comm.get_documents('an_endpoint', all_pages=True, max_results=101)
            assert len(ret) == 1200

    @patched_response
    def test_get_content(self, mocked_response):
        data = self.comm.get_content(test_endpoint, max_results=100, where={'a_field': 'thing'})
        assert data == test_nested_request_content
        assert mocked_response.call_args[0][1].startswith(rest_url(test_endpoint))
        assert mocked_response.call_args[1] == {
            'auth': ('a_user', 'a_password'),
            'params': {'max_results': 100, 'where': '{"a_field": "thing"}', 'page': 1}
        }

    def test_get_documents(self):
        with patched_response:
            data = self.comm.get_documents(test_endpoint, max_results=100, where={'a_field': 'thing'})
            assert data == test_nested_request_content['data']

    def test_get_document(self):
        expected = test_nested_request_content['data'][0]
        with patched_response:
            observed = self.comm.get_document(test_endpoint, max_results=100, where={'a_field': 'thing'})
            assert observed == expected

    @patched_response
    def test_post_entry(self, mocked_response):
        self.comm.post_entry(test_endpoint, payload=test_nested_request_content)
        mocked_response.assert_called_with(
            'POST',
            rest_url(test_endpoint),
            auth=auth,
            json=test_nested_request_content,
            files=None
        )
        file_path = os.path.join(self.assets_path, 'test_to_upload.txt')
        test_request_content_plus_files = dict(test_flat_request_content)
        test_request_content_plus_files['f'] = ('file', file_path)
        self.comm.post_entry(test_endpoint, payload=test_request_content_plus_files)
        mocked_response.assert_called_with(
            'POST',
            rest_url(test_endpoint),
            auth=auth,
            data=test_flat_request_content,
            files={'f': (file_path, b'test content', 'text/plain')}
        )

        self.comm.post_entry(test_endpoint, payload=test_flat_request_content, use_data=True)
        mocked_response.assert_called_with(
            'POST',
            rest_url(test_endpoint),
            auth=auth,
            data=test_flat_request_content,
            files=None
        )

        self.comm.post_entry(test_endpoint, payload=test_request_content_plus_files, use_data=True)
        mocked_response.assert_called_with(
            'POST',
            rest_url(test_endpoint),
            auth=auth,
            data=test_flat_request_content,
            files={'f': (file_path, b'test content', 'text/plain')}
        )

    @patched_response
    def test_put_entry(self, mocked_response):
        self.comm.put_entry(test_endpoint, 'an_element_id', payload=test_nested_request_content)
        mocked_response.assert_called_with(
            'PUT',
            rest_url(test_endpoint) + 'an_element_id',
            auth=auth,
            json=test_nested_request_content,
            files=None
        )

        file_path = os.path.join(self.assets_path, 'test_to_upload.txt')
        test_request_content_plus_files = dict(test_flat_request_content)
        test_request_content_plus_files['f'] = ('file', file_path)
        self.comm.put_entry(test_endpoint, 'an_element_id', payload=test_request_content_plus_files)
        mocked_response.assert_called_with(
            'PUT',
            rest_url(test_endpoint) + 'an_element_id',
            auth=auth,
            data=test_flat_request_content,
            files={'f': (file_path, b'test content', 'text/plain')}
        )

    @patch(ppath('get_document'), return_value=test_patch_document)
    @patched_response
    def test_patch_entry(self, mocked_response, mocked_get_doc):
        patching_payload = {'list_to_update': ['another']}
        self.comm.patch_entry(
            test_endpoint,
            payload=patching_payload,
            id_field='uid',
            element_id='a_unique_id',
            update_lists=['list_to_update']
        )

        mocked_get_doc.assert_called_with(test_endpoint, where={'uid': 'a_unique_id'})
        mocked_response.assert_called_with(
            'PATCH',
            rest_url(test_endpoint) + '1337',
            headers={'If-Match': 1234567},
            auth=auth,
            json={'list_to_update': ['this', 'that', 'other', 'another']},
            files=None
        )

    @patch(ppath('get_document'), return_value=test_patch_document)
    @patched_response
    def test_auth_token_and_if_match(self, mocked_response, mocked_get_doc):
        self.comm._auth = 'an_auth_token'
        self.comm.patch_entry(test_endpoint, {'this': 'that'}, 'uid', 'a_unique_id')
        mocked_get_doc.assert_called_with(test_endpoint, where={'uid': 'a_unique_id'})
        mocked_response.assert_called_with(
            'PATCH',
            rest_url(test_endpoint) + '1337',
            headers={'If-Match': 1234567, 'Authorization': 'Token an_auth_token'},
            json={'this': 'that'},
            files=None
        )

    def test_post_or_patch(self):
        test_post_or_patch_payload = {'uid': '1337', 'list_to_update': ['more'], 'another_field': 'that'}
        test_post_or_patch_payload_no_uid = {'list_to_update': ['more'], 'another_field': 'that'}
        test_post_or_patch_doc = {
            'uid': 'a_uid', '_id': '1337', '_etag': 1234567, 'list_to_update': ['things'], 'another_field': 'this'
        }
        patched_post = patch(ppath('post_entry'), return_value=True)
        patched_patch = patch(ppath('_patch_entry'), return_value=True)
        patched_get = patch(ppath('get_document'), return_value=test_post_or_patch_doc)
        patched_get_none = patch(ppath('get_document'), return_value=None)

        with patched_get as mget, patched_patch as mpatch:
            self.comm.post_or_patch(
                'an_endpoint',
                [test_post_or_patch_payload],
                id_field='uid',
                update_lists=['list_to_update']
            )
            mget.assert_called_with('an_endpoint', where={'uid': '1337'})
            mpatch.assert_called_with(
                'an_endpoint',
                test_post_or_patch_doc,
                test_post_or_patch_payload_no_uid,
                ['list_to_update']
            )

        with patched_get_none as mget, patched_post as mpost:
            self.comm.post_or_patch(
                'an_endpoint', [test_post_or_patch_payload], id_field='uid', update_lists=['list_to_update']
            )
            mget.assert_called_with('an_endpoint', where={'uid': '1337'})
            mpost.assert_called_with('an_endpoint', test_post_or_patch_payload)

    def test_token_auth(self):
        hashed_token = '{"some": "hashed"}.tokenauthentication'
        self.comm._auth = hashed_token
        with patched_response as p:
            self.comm._req('GET', self.comm.baseurl + 'an_endpoint')
            p.assert_called_with(
                'GET',
                self.comm.baseurl + 'an_endpoint',
                headers={'Authorization': 'Token ' + hashed_token}
            )


def test_default():
    d = rest_communication.default
    assert d.baseurl == 'http://localhost:4999/api/0.1'
    assert d.auth == ('a_user', 'a_password')
