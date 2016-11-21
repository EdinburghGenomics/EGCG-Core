import requests
from urllib.parse import urljoin
from egcg_core.config import cfg
from egcg_core.app_logging import AppLogger
from egcg_core.exceptions import RestCommunicationError


class Communicator(AppLogger):
    table = {' ': '', '\'': '"', 'None': 'null'}
    successful_statuses = (200, 201, 202)

    def __init__(self, auth=None, baseurl=None):
        self._baseurl = baseurl
        self._auth = auth

    @property
    def baseurl(self):
        if self._baseurl is None:
            self._baseurl = cfg['rest_api']['url'].rstrip('/')
        return self._baseurl

    @property
    def auth(self):
        if self._auth is None and 'username' in cfg['rest_api'] and 'password' in cfg['rest_api']:
            self._auth = (cfg['rest_api']['username'], cfg['rest_api']['password'])
        return self._auth

    @classmethod
    def _translate(cls, s):
        for k, v in cls.table.items():
            s = s.replace(k, v)
        return s

    def api_url(self, endpoint, **query_args):
        url = '{base_url}/{endpoint}/'.format(
            base_url=self.baseurl, endpoint=endpoint
        )
        if query_args:
            query = '?' + '&'.join('%s=%s' % (k, v) for k, v in query_args.items())
            url += self._translate(query)
        return url

    @staticmethod
    def _parse_query_string(query_string, requires=None):
        if '?' not in query_string:
            return {}

        if query_string.count('?') != 1:
            raise RestCommunicationError('Bad query string: ' + query_string)

        href, query = query_string.split('?')
        query = dict(x.split('=') for x in query.split('&'))
        if requires and not all(r in query for r in requires):
            raise RestCommunicationError('%s did not contain all required fields: %s' % (query_string, requires))
        return query

    def _req(self, method, url, quiet=False, **kwargs):
        if type(self.auth) is tuple:
            kwargs.update(auth=self.auth)
        elif type(self.auth) is str:
            # noinspection PyTypeChecker
            kwargs.update(headers={'Authorization': 'Token ' + self.auth})

        r = requests.request(method, url, **kwargs)

        kwargs.pop('auth', None)
        kwargs.pop('headers', None)
        # e.g: 'POST <url> ({"some": "args"}) -> {"some": "content"}. Status code 201. Reason: CREATED
        report = '%s %s (%s) -> %s. Status code %s. Reason: %s' % (
            r.request.method, r.request.path_url, kwargs, r.content.decode('utf-8'), r.status_code, r.reason
        )
        if r.status_code in self.successful_statuses:
            if not quiet:
                self.debug(report)
        else:
            self.error(report)
            raise RestCommunicationError('Encountered a %s status code: %s' % (r.status_code, r.reason))
        return r

    def get_content(self, endpoint, paginate=True, quiet=False, **query_args):
        if paginate:
            query_args.update(
                max_results=query_args.pop('max_results', 100),  # default to page size of 100
                page=query_args.pop('page', 1)
            )
        url = self.api_url(endpoint, **query_args)
        return self._req('GET', url, quiet=quiet).json()

    def get_documents(self, endpoint, paginate=True, all_pages=False, quiet=False, **query_args):
        content = self.get_content(endpoint, paginate, quiet, **query_args)
        elements = content['data']

        if all_pages and 'next' in content['_links']:
            next_query = self._parse_query_string(content['_links']['next']['href'], requires=('max_results', 'page'))
            query_args.update(next_query)
            elements.extend(self.get_documents(endpoint, all_pages=True, quiet=quiet, **query_args))

        return elements

    def get_document(self, endpoint, idx=0, **query_args):
        documents = self.get_documents(endpoint, **query_args)
        if documents:
            return documents[idx]
        else:
            self.warning('No document found in endpoint %s for %s', endpoint, query_args)

    def post_entry(self, endpoint, payload):
        r = self._req('POST', self.api_url(endpoint), json=payload)
        return r.status_code in self.successful_statuses

    def put_entry(self, endpoint, element_id, payload):
        r = self._req('PUT', urljoin(self.api_url(endpoint), element_id), json=payload)
        return r.status_code in self.successful_statuses

    def _patch_entry(self, endpoint, doc, payload, update_lists=None):
        """
        Patch a specific database item (specified by doc) with the given data payload.
        :param str endpoint:
        :param dict doc: The entry in the database to patch (contains the relevant _id and _etag)
        :param dict payload: Data with which to patch doc
        :param list update_lists: Doc items listed here will be appended rather than replaced by the patch
        """
        url = urljoin(self.api_url(endpoint), doc['_id'])
        _payload = dict(payload)
        headers = {'If-Match': doc.get('_etag')}
        if update_lists:
            for l in update_lists:
                content = doc.get(l, [])
                new_content = [x for x in _payload.get(l, []) if x not in content]
                _payload[l] = content + new_content
        r = self._req('PATCH', url, headers=headers, json=_payload)
        return r.status_code in self.successful_statuses

    def patch_entry(self, endpoint, payload, id_field, element_id, update_lists=None):
        """
        Retrieve a document at the given endpoint with the given unique ID, and patch it with some data.
        :param str endpoint:
        :param dict payload:
        :param str id_field: The name of the unique identifier (e.g. 'run_element_id', 'proc_id', etc.)
        :param element_id: The value of id_field to retrieve (e.g. '160301_2_ATGCATGC')
        :param list update_lists:
        """
        doc = self.get_document(endpoint, where={id_field: element_id})
        if doc:
            return self._patch_entry(endpoint, doc, payload, update_lists)
        return False

    def patch_entries(self, endpoint, payload, update_lists=None, **query_args):
        """
        Retrieve many documents and patch them all with the same data.
        :param str endpoint:
        :param dict payload:
        :param list update_lists:
        :param query_args: Database query args to pass to get_documents
        """
        docs = self.get_documents(endpoint, **query_args)
        if docs:
            success = True
            nb_docs = 0
            for doc in docs:
                if self._patch_entry(endpoint, doc, payload, update_lists):
                    nb_docs += 1
                else:
                    success = False
            self.info('Updated %s documents matching %s', nb_docs, query_args)
            return success
        return False

    def post_or_patch(self, endpoint, input_json, id_field=None, update_lists=None):
        """
        For each document supplied, either post to the endpoint if the unique id doesn't yet exist there, or
        patch if it does.
        :param str endpoint:
        :param input_json: A single document or list of documents to post or patch to the endpoint.
        :param str id_field: The field to use as the unique ID for the endpoint.
        :param list update_lists:
        """
        success = True
        for payload in input_json:
            _payload = dict(payload)
            doc = self.get_document(endpoint, where={id_field: _payload[id_field]})
            if doc:
                _payload.pop(id_field)
                s = self._patch_entry(endpoint, doc, _payload, update_lists)
            else:
                s = self.post_entry(endpoint, _payload)
            success = success and s
        return success


default = Communicator()
api_url = default.api_url
get_content = default.get_content
get_documents = default.get_documents
get_document = default.get_document
post_entry = default.post_entry
put_entry = default.put_entry
patch_entry = default.patch_entry
patch_entries = default.patch_entries
post_or_patch = default.post_or_patch
