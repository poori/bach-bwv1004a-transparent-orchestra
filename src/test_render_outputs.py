"""Guard against accepting stale or truncated exports after an application crash."""
import tempfile
import time
from pathlib import Path
import unittest
from render_score import fresh_complete_outputs


class ExportRecoveryTests(unittest.TestCase):
    def test_stale_pdf_cannot_mask_a_failed_export(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'old.pdf'
            path.write_bytes(b'%PDF-1.7\n%%EOF\n')
            self.assertFalse(fresh_complete_outputs([path], time.time_ns() + 1))

    def test_truncated_native_container_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'partial.mscz'
            path.write_bytes(b'PK\x03\x04unfinished')
            self.assertFalse(fresh_complete_outputs([path], 0))

    def test_failed_audio_export_is_never_recovered_this_way(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'partial.mp3'
            path.write_bytes(b'ID3unfinished')
            self.assertFalse(fresh_complete_outputs([path], 0))


if __name__ == '__main__':
    unittest.main()
