import sys
import tempfile
import unittest
from pathlib import Path
from openpyxl import load_workbook

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from asset_report import MAIN_HEADERS, build_workbook, title_is_priority


class AssetReportTests(unittest.TestCase):
    def test_dedupe_scope_priority_and_formula_safety(self):
        data = {
            "region": "西藏自治区",
            "subregions": ["拉萨市", "日喀则市"],
            "scope": {
                "authorization_reference": "模拟演练授权编号",
                "authorized_units": ["测试住建单位", "部门"],
                "authorized_vendors": ["供应商"],
            },
            "assets": [
                {"unit": "测试住建单位", "host": "market.example.gov.cn", "ip": "192.0.2.10", "port": "443", "protocol": "https", "title": "建筑市场监管平台", "ip_geo": "中国/西藏自治区/拉萨市", "ip_geo_match": True, "relation_status": "confirmed", "scope_status": "in_scope", "relation_basis": "官方页面列出域名", "confidence": "高", "source": "FOFA", "subregion": "拉萨市"},
                {"unit": "测试住建单位", "host": "market.example.gov.cn", "ip": "192.0.2.10", "port": "443", "protocol": "https", "title": "建筑市场监管平台", "ip_geo": "中国/西藏自治区/拉萨市", "ip_geo_match": True, "relation_status": "confirmed", "scope_status": "in_scope", "relation_basis": "官方页面列出域名", "confidence": "高", "source": "Shodan", "subregion": "拉萨市"},
                {"unit": "测试住建单位", "host": "api.example.gov.cn", "ip": "192.0.2.10", "port": "443", "protocol": "https", "title": "业务系统", "ip_geo": "西藏自治区", "ip_geo_match": True, "relation_status": "confirmed", "scope_status": "in_scope", "relation_basis": "单位域名", "source": "FOFA", "subregion": "拉萨市"},
                {"unit": "测试单位", "host": "candidate.example.net", "ip": "198.51.100.4", "port": "443", "protocol": "https", "title": "交易平台", "icp": "藏ICP备000001号", "relation_status": "candidate", "scope_status": "in_scope", "relation_basis": "仅名称线索", "source": "FOFA"},
                {"unit": "供应商", "asset_type": "vendor", "host": "vendor.example.net", "ip": "203.0.113.20", "port": "443", "protocol": "https", "title": "系统平台", "relation_status": "confirmed", "scope_status": "scope_pending", "relation_basis": "范围待确认", "source": "网页线索"},
                {"unit": "部门", "host": "bureau.example.gov.cn", "ip": "192.0.2.22", "title": "拉萨市经济和信息化局", "ip_geo_match": True, "relation_status": "confirmed", "scope_status": "in_scope", "source": "官方页面", "subregion": "拉萨市"},
                {"unit": "部门", "host": "portal.example.gov.cn", "ip": "192.0.2.23", "port": "443", "protocol": "https", "title": "=HYPERLINK(\"https://invalid.example\",\"payload\")", "ip_geo_match": True, "relation_status": "confirmed", "scope_status": "in_scope", "source": "模拟", "subregion": "拉萨市"},
            ],
            "appendices": {"icp_candidates": [], "vendor_links": [], "coverage": []},
            "coverage": [["FOFA 请求", "1", "模拟"]],
        }
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "report.xlsx"
            result = build_workbook(data, output)
            self.assertEqual(result["main_assets"], 4)
            self.assertEqual(result["candidate_assets"], 2)
            workbook = load_workbook(output, data_only=False)
            self.assertEqual(workbook.sheetnames[:3], ["西藏自治区", "拉萨市", "日喀则市"])
            sheet = workbook["拉萨市"]
            self.assertEqual(tuple(cell.value for cell in sheet[1]), tuple(MAIN_HEADERS))
            rows = list(sheet.iter_rows(min_row=2, values_only=True))
            self.assertEqual(sum(row[2] == "market.example.gov.cn" for row in rows), 1)
            self.assertEqual(sum(row[2] == "api.example.gov.cn" for row in rows), 1)
            market = next(row for row in rows if row[2] == "market.example.gov.cn")
            self.assertEqual(market[12], "重点")
            self.assertIn("FOFA", market[16])
            self.assertIn("Shodan", market[16])
            bureau = next(row for row in rows if row[2] == "bureau.example.gov.cn")
            self.assertIn(bureau[12], (None, ""))
            formula_text = next(row for row in rows if row[2] == "portal.example.gov.cn")
            self.assertEqual(formula_text[8], '=HYPERLINK("https://invalid.example","payload")')
            self.assertFalse(any(cell.data_type == "f" for ws in workbook.worksheets for row in ws.iter_rows() for cell in row))
            self.assertTrue(any(row[1] == "candidate.example.net" for row in workbook["ICP备案候选"].iter_rows(min_row=2, values_only=True)))
            self.assertTrue(any(row[2] == "vendor.example.net" for row in workbook["供应商关联"].iter_rows(min_row=2, values_only=True)))

    def test_title_rules_are_fixed(self):
        self.assertTrue(title_is_priority("建筑市场监管平台"))
        self.assertFalse(title_is_priority("拉萨市经济和信息化局"))
        self.assertFalse(title_is_priority("政府门户网站"))

    def test_missing_scope_keeps_confirmed_assets_out_of_main_table(self):
        data = {
            "region": "测试区域",
            "assets": [{
                "unit": "测试单位", "host": "app.example.gov.cn",
                "relation_status": "confirmed", "scope_status": "in_scope",
                "relation_basis": "官方页面列出域名", "source": "模拟",
            }],
        }
        with tempfile.TemporaryDirectory() as temp:
            result = build_workbook(data, Path(temp) / "report.xlsx")
            self.assertEqual(result["main_assets"], 0)
            self.assertEqual(result["candidate_assets"], 1)


if __name__ == "__main__":
    unittest.main()
