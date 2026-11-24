import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from verify_global_interest_publication import MAX_BYTES, matches_publication, verify


class PublicVerificationTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 24, 22, 0, tzinfo=timezone.utc)
        self.payload = {"lastSuccessfulCloudflareRetrievalAt": "2026-11-24T21:26:31Z",
                        "lastCheckedAt": "2026-11-24T21:26:31Z", "countries": []}
        self.data = json.dumps(self.payload).encode()

    def test_matching_fresh_dataset_passes(self):
        self.assertTrue(matches_publication(self.data, self.data, self.now))

    def test_different_stale_future_and_oversized_data_are_rejected(self):
        self.assertTrue(matches_publication(self.data, self.data + b" ", self.now))
        different = json.dumps({**self.payload, "countries": [{"iso": "SK", "status": "high"}]}).encode()
        self.assertFalse(matches_publication(self.data, different, self.now))
        self.assertFalse(matches_publication(self.data, b"not json", self.now))
        self.assertFalse(matches_publication(self.data, b"x" * (MAX_BYTES + 1), self.now))
        for date in ("2026-11-20T00:00:00Z", "2026-11-25T00:00:00Z", "bad"):
            data = json.dumps({**self.payload, "lastSuccessfulCloudflareRetrievalAt": date}).encode()
            self.assertFalse(matches_publication(data, data, self.now))

    @patch("verify_global_interest_publication.retrieve_public", side_effect=OSError("offline"))
    @patch("verify_global_interest_publication.validate")
    def test_network_failure_is_not_reported_as_success(self, _validate, _retrieve):
        with unittest.mock.patch.object(Path, "read_bytes", return_value=self.data):
            self.assertFalse(verify(Path("unused.json"), max_wait=0))

    @patch("verify_global_interest_publication.retrieve_public")
    @patch("verify_global_interest_publication.validate")
    def test_live_data_must_match(self, _validate, retrieve):
        now = datetime.now(timezone.utc).isoformat()
        data = json.dumps({"lastSuccessfulCloudflareRetrievalAt": now, "lastCheckedAt": now}).encode()
        retrieve.return_value = data
        with unittest.mock.patch.object(Path, "read_bytes", return_value=data):
            self.assertTrue(verify(Path("unused.json"), max_wait=0))
        retrieve.return_value = b'{}'
        with unittest.mock.patch.object(Path, "read_bytes", return_value=data):
            self.assertFalse(verify(Path("unused.json"), max_wait=0))


if __name__ == "__main__":
    unittest.main()
