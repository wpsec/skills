import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import collect_passive


class PassiveCollectorTests(unittest.TestCase):
    def test_mock_fofa_response_never_writes_credentials(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "fofa.txt").write_text("person@example.invalid\nnot-a-real-key\n", encoding="utf-8")
            output = root / "records.jsonl"
            state_path = root / "state.json"
            state = {"_path": str(state_path), "api_totals": {"fofa": {"requests": 0, "records": 0}}}
            coverage = collect_passive.new_coverage()
            plan = {"region": "测试区域", "scope": {
                "authorization_reference": "模拟演练授权编号", "authorized_units": ["测试单位"],
            }, "fofa_queries": [{
                "query": 'domain="example.gov.cn"', "unit": "测试单位",
                "label": "root-domain", "fpoint_free_confirmed": True,
            }]}
            fields = collect_passive.FOFA_FIELDS.split(",")
            result = dict(zip(fields, [
                "www.example.gov.cn", "192.0.2.7", "443", "https", "系统平台",
                "example.gov.cn", "测试ICP备000001号", "SERIAL", "测试单位",
                "www.example.gov.cn", "server", "2026-09-25", "西藏自治区", "拉萨市",
                "nginx", "1.2.3", "",
            ]))
            def fake_http(provider, url, counters, current_state):
                self.assertEqual(provider, "fofa")
                self.assertIn("key=", url)
                counters[provider]["requests"] += 1
                return 200, {"error": False, "consumed_fpoint": 0, "required_fpoints": 0, "results": [result], "next": ""}
            with patch.object(collect_passive, "http_json", side_effect=fake_http):
                collect_passive.collect_fofa(plan, root, output, state, coverage)
            saved = json.loads(output.read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(saved["provider"], "FOFA")
            self.assertEqual(saved["record"]["ip"], "192.0.2.7")
            self.assertNotIn("not-a-real-key", output.read_text(encoding="utf-8"))
            self.assertEqual(coverage["fofa"]["records"], 1)
            self.assertEqual(coverage["fofa"]["status"], "complete")

    def test_unconfirmed_zero_cost_query_is_skipped(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "fofa.txt").write_text("person@example.invalid\nnot-a-real-key\n", encoding="utf-8")
            output = root / "records.jsonl"
            state = {"_path": str(root / "state.json")}
            coverage = collect_passive.new_coverage()
            plan = {"scope": {
                "authorization_reference": "模拟演练授权编号", "authorized_units": ["测试单位"],
            }, "fofa_queries": [{
                "query": 'title="test"', "unit": "测试单位", "fpoint_free_confirmed": False,
            }]}
            with patch.object(collect_passive, "http_json") as mocked:
                collect_passive.collect_fofa(plan, root, output, state, coverage)
            mocked.assert_not_called()
            self.assertEqual(coverage["fofa"]["skipped_fpoint_unverified"], 1)

    def test_scope_is_required_before_api_queries(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "fofa.txt").write_text("person@example.invalid\nnot-a-real-key\n", encoding="utf-8")
            output = root / "records.jsonl"
            state = {"_path": str(root / "state.json")}
            coverage = collect_passive.new_coverage()
            plan = {"fofa_queries": [{
                "query": 'title="test"', "unit": "测试单位", "fpoint_free_confirmed": True,
            }]}
            with patch.object(collect_passive, "http_json") as mocked:
                collect_passive.collect_fofa(plan, root, output, state, coverage)
            mocked.assert_not_called()
            self.assertEqual(coverage["fofa"]["status"], "scope_unconfirmed")

    def test_shodan_search_credit_estimate(self):
        self.assertFalse(collect_passive.shodan_search_requires_credit("some agency name", 1))
        self.assertTrue(collect_passive.shodan_search_requires_credit('org:"Some Agency"', 1))
        self.assertTrue(collect_passive.shodan_search_requires_credit("some agency name", 2))

    def test_mock_shodan_host_and_search_responses(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "shodan.txt").write_text("not-a-real-token\n", encoding="utf-8")
            output = root / "records.jsonl"
            state_path = root / "state.json"
            state = {"_path": str(state_path), "api_totals": {"shodan": {"requests": 0, "records": 0}}}
            coverage = collect_passive.new_coverage()
            plan = {
                "region": "测试区域",
                "scope": {
                    "authorization_reference": "模拟演练授权编号",
                    "authorized_units": ["测试单位"],
                    "authorized_ips": ["8.8.8.8"],
                },
                "shodan_ips": ["8.8.8.8"],
                "shodan_queries": [{"query": "test agency", "unit": "测试单位", "label": "name"}],
            }
            host_response = {
                "ip_str": "8.8.8.8",
                "hostnames": ["app.example.gov.cn"],
                "domains": ["example.gov.cn"],
                "location": {"country_name": "China", "region_code": "Tibet", "city": "Lhasa"},
                "data": [{"port": 443, "transport": "tcp", "product": "nginx", "version": "1.2", "http": {"title": "业务系统"}}],
            }
            search_match = {
                "ip_str": "8.8.8.8", "port": 443, "transport": "tcp", "product": "nginx",
                "hostnames": ["app.example.gov.cn"],
                "location": {"country_name": "China", "region_code": "Tibet", "city": "Lhasa"},
                "http": {"title": "业务系统"},
            }
            def fake_info(key, counters, current_state):
                self.assertEqual(key, "not-a-real-token")
                return {"query_credits": 0, "scan_credits": 0}
            def fake_http(provider, url, counters, current_state):
                self.assertEqual(provider, "shodan")
                self.assertIn("key=", url)
                counters[provider]["requests"] += 1
                if "/shodan/host/8.8.8.8?" in url:
                    return 200, host_response
                self.assertIn("/shodan/host/search?", url)
                return 200, {"matches": [search_match]}
            with patch.object(collect_passive, "shodan_info", side_effect=fake_info):
                with patch.object(collect_passive, "http_json", side_effect=fake_http):
                    collect_passive.collect_shodan(plan, root, output, state, coverage)
            records = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(records), 2)
            self.assertEqual(records[0]["provider"], "Shodan host lookup")
            self.assertEqual(records[1]["provider"], "Shodan search")
            self.assertTrue(all("not-a-real-token" not in json.dumps(row) for row in records))
            self.assertEqual(coverage["shodan"]["status"], "complete")


if __name__ == "__main__":
    unittest.main()
