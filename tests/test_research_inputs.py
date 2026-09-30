import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import sentinel

class ResearchInputsTests(unittest.TestCase):
    def test_history_excludes_current_and_future_and_is_bounded(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            for day in range(1,10):
                (root/f'2026-09-{day:02}.md').write_text('# A topic\n• Evidence\nhttps://example.com/source\n')
            h=sentinel.recent_history('2026-09-09',root,limit=3)
            self.assertEqual([x['file'] for x in h],['2026-09-08.md','2026-09-07.md','2026-09-06.md'])
            self.assertIn('https://example.com/source',h[0]['urls'])

    def test_prompt_includes_memory_and_benchmark_status(self):
        p=sentinel.weekly_prompt('Sep 23–30, 2026',[{'file':'2026-09-20.md','titles':['Repeated topic']}])
        self.assertIn('Repeated topic',p)
        self.assertIn('user_named_peer',p)
        self.assertIn('competitive watchlist',p)

    def test_prepare_needs_no_secrets_calls_or_email(self):
        with TemporaryDirectory() as tmp, patch('sys.argv',['sentinel.py','--prepare-only','--as-of','2026-09-30','--output-dir',tmp]), patch.object(sentinel,'run_claude') as call, patch.object(sentinel,'send_email') as email:
            sentinel.main()
            call.assert_not_called();email.assert_not_called()
            self.assertTrue((Path(tmp)/'research-prompt.txt').exists())

    def test_no_email_run_saves_without_sending(self):
        with TemporaryDirectory() as tmp, patch('sys.argv',['sentinel.py','--no-email','--as-of','2026-09-30','--output-dir',tmp]), patch.object(sentinel,'run_claude',return_value='# Research brief') as call, patch.object(sentinel,'send_email') as email:
            sentinel.main();email.assert_not_called()
            self.assertTrue((Path(tmp)/'2026-09-30.md').exists())
            with self.assertRaises(FileExistsError):sentinel.main()
            self.assertEqual(call.call_count,1)

if __name__=='__main__':unittest.main()
