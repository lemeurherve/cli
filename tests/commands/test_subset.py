import os
import tempfile
from unittest import mock
import responses
from launchable.utils.http_client import get_base_url
from tests.cli_test_case import CliTestCase


class SubsetTest(CliTestCase):
    @responses.activate
    @mock.patch.dict(os.environ, {"LAUNCHABLE_TOKEN": CliTestCase.launchable_token})
    def test_subset_with_get_tests_from_previous_full_runs(self):
        responses.replace(responses.POST, "{}/intake/organizations/{}/workspaces/{}/subset".format(get_base_url(), self.organization, self.workspace),
                          json={
            "testPaths": [
                [{"type": "file", "name": "test_aaa.py"}],
                [{"type": "file", "name": "test_bbb.py"}],
                [{"type": "file", "name": "test_ccc.py"}],
            ],
            "rest": [
                [{"type": "file", "name": "test_eee.py"}],
                [{"type": "file", "name": "test_fff.py"}],
                [{"type": "file", "name": "test_ggg.py"}],
            ],
            "subsettingId": 123,
            "summary": {
                "subset": {"duration": 10, "candidates": 3, "rate": 50},
                "rest": {"duration": 10, "candidates": 3, "rate": 50}
            },
        }, status=200)

        rest = tempfile.NamedTemporaryFile(delete=False)
        result = self.cli("subset", "--target", "30%", "--session",
                          self.session, "--rest", rest.name, "--get-tests-from-previous-full-runs",  "file", mix_stderr=False)

        self.assertEqual(result.exit_code, 0)
        self.assertEqual(
            result.stdout, "test_aaa.py\ntest_bbb.py\ntest_ccc.py\n")
        self.assertEqual(
            rest.read().decode(), os.linesep.join(["test_eee.py", "test_fff.py", "test_ggg.py"]))
        rest.close()
        os.unlink(rest.name)

    @responses.activate
    @mock.patch.dict(os.environ, {"LAUNCHABLE_TOKEN": CliTestCase.launchable_token})
    def test_subset_with_output_exclusion_rules(self):
        pipe = "test_aaa.py\ntest_111.py\ntest_bbb.py\ntest_222.py\ntest_ccc.py\ntest_333.py\n"
        responses.replace(responses.POST, "{}/intake/organizations/{}/workspaces/{}/subset".format(get_base_url(), self.organization, self.workspace),
                          json={
            "testPaths": [
                [{"type": "file", "name": "test_aaa.py"}],
                [{"type": "file", "name": "test_bbb.py"}],
                [{"type": "file", "name": "test_ccc.py"}],
            ],
            "rest": [
                [{"type": "file", "name": "test_111.py"}],
                [{"type": "file", "name": "test_222.py"}],
                [{"type": "file", "name": "test_333.py"}],
            ],
            "subsettingId": 123,
            "summary": {
                "subset": {"duration": 15, "candidates": 3, "rate": 70},
                "rest": {"duration": 6, "candidates": 3, "rate": 30}
            },
        }, status=200)

        rest = tempfile.NamedTemporaryFile(delete=False)
        result = self.cli("subset", "--target", "70%", "--session",
                          self.session, "--rest", rest.name,  "file", input=pipe, mix_stderr=False)

        self.assertEqual(result.exit_code, 0)
        self.assertEqual(
            result.stdout, "test_aaa.py\ntest_bbb.py\ntest_ccc.py\n")
        self.assertEqual(
            rest.read().decode(), os.linesep.join(["test_111.py", "test_222.py", "test_333.py"]))
        rest.close()
        os.unlink(rest.name)

        rest = tempfile.NamedTemporaryFile(delete=False)
        result = self.cli("subset", "--target", "70%", "--session",
                          self.session, "--rest", rest.name, "--output-exclusion-rules", "file", input=pipe, mix_stderr=False)

        self.assertEqual(result.exit_code, 0)
        self.assertEqual(
            result.stdout, "test_111.py\ntest_222.py\ntest_333.py\n")

        self.assertEqual(
            rest.read().decode(), os.linesep.join(["test_aaa.py", "test_bbb.py", "test_ccc.py"]))
        rest.close()
        os.unlink(rest.name)
