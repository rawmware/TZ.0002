import json
from pathlib import Path
import tempfile
import unittest
import urllib.request
import urllib.error
from unittest.mock import patch

from app.tz_agent import Agent


class AstraTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.agent = Agent(self.root, emit=lambda *a, **k: None, confirm=lambda _: True)

    def tearDown(self):
        self.agent.preview.close()
        self.tmp.cleanup()

    def test_workspace_change_trust_and_write_boundary(self):
        new = self.root / 'new project'; new.mkdir()
        self.agent.messages = [{'role': 'user', 'content': 'old context'}]
        self.agent.confirm = lambda _: False
        with self.assertRaisesRegex(ValueError, 'declined'): self.agent.turn('/workspace "' + str(new) + '"')
        self.assertEqual(self.agent.workspace, self.root)
        self.agent.confirm = lambda _: True
        self.agent.turn('/workspace "' + str(new) + '"')
        self.assertEqual(self.agent.messages, [])
        self.agent.tool('file_write', {'path': 'test.txt', 'content': 'new'})
        self.assertTrue((new / 'test.txt').is_file())
        with self.assertRaisesRegex(ValueError, 'inside'):
            self.agent.tool('file_write', {'path': '../escape.txt', 'content': 'no'})

    def test_preview_edit_same_tab_revision_and_boundary(self):
        def get(url):
            with urllib.request.urlopen(url) as response: return response.read()
        with patch('app.tz_preview.webbrowser.open', return_value=True) as browser:
            first = self.agent.tool('file_write', {'path': 'a b.html', 'content': '<h1>Before</h1>'})
            url = first['preview']['url']
            page = get(url)
            self.assertIn(b'location.reload()', page)
            before = get(url + '?tz_revision')
            self.agent.tool('file_write', {'path': 'a b.html', 'content': '<h1>After</h1>'})
            self.assertNotEqual(before, get(url + '?tz_revision'))
            self.assertIn(b'After', get(url))
            browser.assert_called_once()
            with self.assertRaises(urllib.error.HTTPError): get(url.rsplit('/', 1)[0] + '/%2e%2e/outside')
            self.assertEqual((self.root / 'a b.html').read_text(), '<h1>After</h1>')

    def test_preview_failure_preserves_successful_write(self):
        with patch.object(self.agent.preview, 'start', side_effect=OSError('port unavailable')), patch('app.tz_preview.webbrowser.open', return_value=True) as browser:
            result = self.agent.tool('file_write', {'path': 'x.htm', 'content': 'saved'})
            self.assertTrue(result['verified'])
            self.assertFalse(result['preview']['live_reload'])
            self.assertTrue(browser.call_args.args[0].startswith('file:'))

    def test_locality_blocks_remote_endpoint_and_cloud_models(self):
        with patch.object(self.agent, 'api') as api:
            self.agent.base_url = 'http://example.com:11434'
            with self.assertRaisesRegex(ValueError, 'loopback'): self.agent.local_model()
            api.assert_not_called()
            self.agent.base_url = 'http://127.0.0.1:11434'
            self.agent.model = 'test:cloud'
            with self.assertRaisesRegex(ValueError, 'Cloud'): self.agent.local_model()
            self.agent.model = 'test:latest'
            api.return_value = {'remote_host': 'https://example.com'}
            with self.assertRaisesRegex(ValueError, 'remote'): self.agent.local_model()


if __name__ == '__main__': unittest.main()
