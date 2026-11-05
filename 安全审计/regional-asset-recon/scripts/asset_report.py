#!/usr/bin/env python3
"""Build a regional asset workbook from normalized, evidence-bearing JSON."""

import argparse
import json
import re
import sys
from collections import OrderedDict
from datetime import datetime
from pathlib import Path

try:
    from openpyxl import Workbook, load_workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
except ImportError:
    Workbook = None
    load_workbook = None

MAIN_HEADERS = [
    "规范单位名称", "资产类型", "域名/主机", "FOFA domain字段", "IP", "IP属地",
    "端口/协议", "服务/产品/版本", "页面标题", "ICP备案号", "证书序列号",
    "证书Subject CN", "重点标注", "关联依据", "置信度", "更新时间", "数据来源",
]
APPENDIX_HEADERS = OrderedDict([
    ("下属单位补充", ["属地", "上级单位", "下属单位", "官方依据要点", "域名线索", "资产核验状态", "依据链接1", "依据链接2"]),
    ("ICP备案候选", ["关联单位", "域名/主机", "FOFA domain字段", "IP", "端口/协议", "服务/产品", "页面标题", "ICP备案号", "证书序列号", "证书Subject CN", "关联依据", "置信度", "数据来源"]),
    ("网段候选", ["前缀长度", "网段", "相关单位/主机样例", "网段内已知目标IP数", "已知目标FOFA记录数", "FOFA整段结果数量", "置信度", "说明"]),
    ("供应商关联", ["属地", "关联单位", "目标主机", "观察到的IP集合", "端口/协议", "关系依据", "置信度", "范围判定", "范围边界"]),
    ("泛解析候选", ["根域", "测试标签", "返回A", "返回AAAA", "返回CNAME", "结论", "数据来源"]),
    ("单位名称映射", ["原始名称", "规范单位名称/归属", "来源类型", "归并状态", "来源文件"]),
    ("待核源线索", ["名称/归属线索", "标题/系统", "属地", "关系说明", "来源文件"]),
    ("覆盖说明", ["项目", "结果", "状态"]),
])
SYSTEM_KEYWORDS = (
    "系统", "平台", "管理后台", "业务办理", "业务系统", "监管平台", "服务平台",
    "申报系统", "公共服务平台", "交易平台", "信息平台", "数据平台",
)
GENERIC_SITE_MARKERS = ("官方网站", "门户网站", "信息公开", "新闻中心", "网站首页", "首页")


def text(value):
    if value is None:
        return ""
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value).strip()


def join_values(*values):
    parts = []
    seen = set()
    for value in values:
        if isinstance(value, (list, tuple, set)):
            candidates = value
        else:
            candidates = [value]
        for candidate in candidates:
            item = text(candidate)
            if item and item not in seen:
                seen.add(item)
                parts.append(item)
    return "；".join(parts)


def asset_key(row):
    host = text(row.get("host") or row.get("domain_or_host")).lower().rstrip(".")
    ip = text(row.get("ip"))
    port = text(row.get("port"))
    protocol = text(row.get("protocol")).lower()
    endpoint_port = port
    if host:
        return ("host", host, endpoint_port, protocol)
    if ip:
        return ("ip", ip, endpoint_port, protocol)
    return ("unkeyed", text(row.get("unit")), text(row.get("title")), text(row.get("source")))


def deduplicate_assets(rows):
    merged = OrderedDict()
    for raw in rows:
        row = dict(raw)
        key = asset_key(row)
        if key not in merged:
            merged[key] = row
            continue
        current = merged[key]
        for field in set(current) | set(row):
            if field in {"source", "sources", "relation_basis", "notes"}:
                current[field] = join_values(current.get(field), row.get(field))
            elif not text(current.get(field)) and text(row.get(field)):
                current[field] = row[field]
            elif text(current.get(field)) and text(row.get(field)) and current[field] != row[field]:
                current[field] = join_values(current[field], row[field])
    return list(merged.values())


def title_is_priority(title):
    title = text(title)
    if not title or not any(keyword in title for keyword in SYSTEM_KEYWORDS):
        return False
    if any(marker in title for marker in GENERIC_SITE_MARKERS):
        has_specific = any(keyword in title for keyword in ("系统", "平台", "管理后台", "业务办理", "监管", "申报", "交易"))
        if not has_specific:
            return False
    return True


def value(row, *keys):
    for key in keys:
        item = row.get(key)
        if item is not None and item != "":
            return item
    return ""


def port_protocol(row):
    port = text(row.get("port"))
    protocol = text(row.get("protocol")).lower()
    if port and protocol:
        return port + "/" + protocol
    if port:
        return port
    return protocol


def main_row(row, region, now):
    relation = text(row.get("relation_status")).lower()
    scope = text(row.get("scope_status")).lower()
    confirmed = relation == "confirmed" and scope == "in_scope"
    priority = (
        confirmed
        and row.get("ip_geo_match") is True
        and title_is_priority(value(row, "title", "page_title"))
    )
    return [
        value(row, "unit", "owner", "规范单位名称"),
        value(row, "asset_type", "类型") or ("域名" if value(row, "host", "domain_or_host") else "IP"),
        value(row, "host", "domain_or_host"),
        value(row, "fofa_domain"),
        value(row, "ip"),
        value(row, "ip_geo", "geo"),
        port_protocol(row),
        value(row, "product", "service", "product_version"),
        value(row, "title", "page_title"),
        value(row, "icp"),
        value(row, "cert_serial"),
        value(row, "cert_cn"),
        "重点" if priority else "",
        value(row, "relation_basis", "relationship_evidence"),
        value(row, "confidence") or "低",
        value(row, "updated_at") or now,
        value(row, "source", "sources"),
    ]


def safe_sheet_title(name, used):
    title = re.sub(r"[\[\]:*?/\\]", "_", text(name)).strip("'") or "未分类"
    title = title[:31]
    base = title
    suffix = 2
    while title in used:
        marker = "_" + str(suffix)
        title = base[:31 - len(marker)] + marker
        suffix += 1
    used.add(title)
    return title


def append_rows(sheet, headers, rows):
    safe_append(sheet, headers)
    for row in rows:
        normalized = list(row) if not isinstance(row, dict) else [row.get(header, "") for header in headers]
        normalized = normalized[:len(headers)] + [""] * max(0, len(headers) - len(normalized))
        safe_append(sheet, [text(value) for value in normalized])
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions
    sheet.row_dimensions[1].height = 28
    for cell in sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="1F4E78")
        cell.alignment = Alignment(vertical="center", wrap_text=True)
    for column in sheet.columns:
        cells = list(column)
        if not cells:
            continue
        width = min(max(max(len(text(cell.value)) for cell in cells[:300]) + 2, 12), 42)
        sheet.column_dimensions[get_column_letter(cells[0].column)].width = width
        for cell in cells[1:]:
            cell.alignment = Alignment(vertical="top", wrap_text=True)


def safe_append(sheet, values):
    sheet.append(values)
    for cell in sheet[sheet.max_row]:
        if isinstance(cell.value, str):
            cell.data_type = "s"


def candidate_record(row):
    return {
        "关联单位": value(row, "unit", "owner"),
        "域名/主机": value(row, "host", "domain_or_host"),
        "FOFA domain字段": value(row, "fofa_domain"),
        "IP": value(row, "ip"),
        "端口/协议": port_protocol(row),
        "服务/产品": value(row, "product", "service"),
        "页面标题": value(row, "title", "page_title"),
        "ICP备案号": value(row, "icp"),
        "证书序列号": value(row, "cert_serial"),
        "证书Subject CN": value(row, "cert_cn"),
        "关联依据": value(row, "relation_basis", "relationship_evidence"),
        "置信度": value(row, "confidence") or "低",
        "数据来源": value(row, "source", "sources"),
    }


def build_workbook(data, output_path):
    if Workbook is None:
        raise RuntimeError("生成 XLSX 需要 openpyxl；请安装 scripts/requirements.txt")
    region = text(data.get("region"))
    if not region:
        raise ValueError("report-data.json 缺少 region")
    subregions = [text(x) for x in data.get("subregions", []) if text(x)]
    now = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    coverage = [list(row) if isinstance(row, (list, tuple)) else row for row in data.get("coverage", [])]
    report_scope = data.get("scope") if isinstance(data.get("scope"), dict) else {}
    scope_confirmed = bool(text(report_scope.get("authorization_reference")).strip())
    raw_authorized_units = report_scope.get("authorized_units", [])
    raw_authorized_vendors = report_scope.get("authorized_vendors", [])
    if not isinstance(raw_authorized_units, list):
        raw_authorized_units = []
    if not isinstance(raw_authorized_vendors, list):
        raw_authorized_vendors = []
    authorized_units = {
        text(item).strip().casefold()
        for item in raw_authorized_units + raw_authorized_vendors
        if text(item).strip()
    }

    assets = deduplicate_assets(data.get("assets", []))
    main_by_sheet = OrderedDict((name, []) for name in [region] + subregions)
    candidate_rows = []
    excluded_scope = 0
    excluded_authorization = 0
    for row in assets:
        relation = text(row.get("relation_status")).lower()
        scope = text(row.get("scope_status")).lower()
        unit_is_authorized = text(row.get("unit") or row.get("owner")).strip().casefold() in authorized_units
        if relation == "confirmed" and scope == "in_scope" and scope_confirmed and unit_is_authorized:
            subregion = text(row.get("subregion"))
            sheet_name = subregion if subregion in main_by_sheet else region
            main_by_sheet[sheet_name].append(main_row(row, region, now))
        else:
            candidate_rows.append(row)
            if scope != "in_scope":
                excluded_scope += 1
            if not scope_confirmed or not unit_is_authorized:
                excluded_authorization += 1

    workbook = Workbook()
    workbook.remove(workbook.active)
    used_titles = set()
    for name, rows in main_by_sheet.items():
        sheet = workbook.create_sheet(safe_sheet_title(name, used_titles))
        append_rows(sheet, MAIN_HEADERS, rows)

    appendices = data.get("appendices") or {}
    for sheet_name, headers in APPENDIX_HEADERS.items():
        sheet = workbook.create_sheet(safe_sheet_title(sheet_name, used_titles))
        source_key = {
            "下属单位补充": "subunits",
            "ICP备案候选": "icp_candidates",
            "网段候选": "network_candidates",
            "供应商关联": "vendor_links",
            "泛解析候选": "wildcard_candidates",
            "单位名称映射": "name_mappings",
            "待核源线索": "leads",
            "覆盖说明": "coverage",
        }[sheet_name]
        rows = list(appendices.get(source_key, []))
        if sheet_name == "ICP备案候选":
            rows.extend(candidate_record(row) for row in candidate_rows if value(row, "icp"))
        elif sheet_name == "供应商关联":
            rows.extend(
                {
                    "属地": value(row, "ip_geo", "geo"),
                    "关联单位": value(row, "unit", "owner"),
                    "目标主机": value(row, "host", "domain_or_host"),
                    "观察到的IP集合": value(row, "ip"),
                    "端口/协议": port_protocol(row),
                    "关系依据": value(row, "relation_basis", "relationship_evidence"),
                    "置信度": value(row, "confidence") or "低",
                    "范围判定": value(row, "scope_status") or "范围待确认",
                    "范围边界": value(row, "scope_boundary"),
                }
                for row in candidate_rows
                if text(row.get("asset_type")).lower() in {"vendor", "供应商"} or text(row.get("scope_status")).lower() == "vendor_candidate"
            )
        elif sheet_name == "待核源线索":
            rows.extend(
                {
                    "名称/归属线索": value(row, "unit", "owner"),
                    "标题/系统": value(row, "title", "page_title"),
                    "属地": value(row, "ip_geo", "geo"),
                    "关系说明": value(row, "relation_basis", "relationship_evidence"),
                    "来源文件": value(row, "source", "sources"),
                }
                for row in candidate_rows
                if not value(row, "icp") and text(row.get("asset_type")).lower() != "vendor"
            )
        mapped = []
        for row in rows:
            if isinstance(row, dict):
                mapped.append([row.get(header, "") for header in headers])
            else:
                mapped.append(list(row))
        append_rows(sheet, headers, mapped)

    coverage_sheet = workbook["覆盖说明"]
    safe_append(coverage_sheet, ["报告区域", region, "完成"])
    safe_append(coverage_sheet, ["本次采集时间", now, "完成"])
    safe_append(coverage_sheet, ["主表资产行", str(sum(len(x) for x in main_by_sheet.values())), "已去重"])
    safe_append(coverage_sheet, ["候选资产行", str(len(candidate_rows)), "按关联强度分流"])
    safe_append(coverage_sheet, ["未确认范围记录", str(excluded_scope), "未进入主表"])
    safe_append(coverage_sheet, ["授权依据缺失或单位未列入范围", str(excluded_authorization), "未进入主表"])
    for row in coverage:
        if isinstance(row, dict):
            safe_append(coverage_sheet, [row.get("项目", ""), row.get("结果", ""), row.get("状态", "")])
        else:
            safe_append(coverage_sheet, list(row))
    coverage_sheet.auto_filter.ref = coverage_sheet.dimensions

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(output_path)
    return {
        "region": region,
        "sheets": workbook.sheetnames,
        "main_assets": sum(len(x) for x in main_by_sheet.values()),
        "candidate_assets": len(candidate_rows),
        "output": str(output_path),
    }


def main():
    parser = argparse.ArgumentParser(description="Generate a deduplicated regional asset workbook.")
    parser.add_argument("--input", required=True, type=Path, help="Normalized report-data.json")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    data = json.loads(args.input.read_text(encoding="utf-8"))
    result = build_workbook(data, args.output)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
