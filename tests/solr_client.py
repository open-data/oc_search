from django.conf import settings
import unittest
from SolrClient2 import SolrClient, SolrResponse
from SolrClient2.exceptions import ConnectionError, SolrError


class SolrClientTest(unittest.TestCase):
    def test_ping(self):
        solr = SolrClient(settings.OPEN_DATA_SOLR_SERVER_URL)
        resp = solr.ping('search_unittest')
        self.assertEqual(resp['status'], 'OK', 'Ping failed')


if __name__ == '__main__':
    unittest.main()
