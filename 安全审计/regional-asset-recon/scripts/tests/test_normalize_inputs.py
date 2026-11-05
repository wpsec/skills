import csv
import sys
import tempfile
import unittest
from pathlib import Path
from openpyxl import Workbook

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from normalize_inputs import process_directory


class NormalizeInputTests(unittest.TestCase):
    def test_xlsx_csv_txt_and_network_rows(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            workbook = Workbook()
            sheet = workbook.active
            sheet.append(["单位名称", "简称", "旧名", "英文名", "拼音", "域名/主机", "IP", "端口", "备注"])
            sheet.append(["住建局", "住建", "原建设厅", "Housing Bureau", "zhujianju", "https://market.example.gov.cn/a", "192.0.2.10", None, "平台"])
            workbook.save(root / "seed.xlsx")
            with (root / "seed.csv").open("w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["单位", "域名", "IP"])
                writer.writerow(["医院", "api.example.org", "198.51.100.7"])
            (root / "seed.txt").write_text("https://portal.example.cn/path 203.0.113.5:8443\n192.0.2.0/24\n", encoding="utf-8")
            result = process_directory(root, "西藏自治区")
            self.assertEqual(result["files_seen"], 3)
            self.assertTrue(any(row["unit"] == "住建局" and row["host"] == "market.example.gov.cn" for row in result["assets"]))
            self.assertTrue(any(row["host"] == "portal.example.cn" and row["port"] == "" for row in result["assets"]))
            self.assertTrue(any(row["ip"] == "203.0.113.5" and row["port"] == "8443" for row in result["assets"]))
            self.assertTrue(any(row["network"] == "192.0.2.0/24" for row in result["appendices"]["network_candidates"]))
            unit = next(row for row in result["units"] if row["unit"] == "住建局")
            self.assertEqual([item["type"] for item in unit["name_variants"]], ["简称", "旧名", "英文名", "拼音"])
            self.assertEqual(result["errors"], [])

    def test_url_port_is_not_guessed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "seed.txt").write_text("https://www.example.gov.cn/path\n", encoding="utf-8")
            result = process_directory(root, "测试区域")
            self.assertEqual(result["assets"][0]["host"], "www.example.gov.cn")
            self.assertEqual(result["assets"][0]["port"], "")

    def test_xls_missing_dependency_is_reported_without_stopping_other_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "legacy.xls").write_bytes(b"not-an-xls")
            (root / "seed.txt").write_text("www.example.gov.cn\n", encoding="utf-8")
            result = process_directory(root, "测试区域")
            self.assertTrue(any(row["host"] == "www.example.gov.cn" for row in result["assets"]))
            if any("需要 xlrd" in row["error"] for row in result["errors"]):
                self.assertEqual(len(result["errors"]), 1)


if __name__ == "__main__":
    unittest.main()
