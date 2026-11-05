#!/usr/bin/env python3
"""Normalize optional spreadsheets and text files into a small JSON seed inventory."""

import argparse
import csv
import ipaddress
import json
import re
import sys
import unicodedata
from pathlib import Path
from urllib.parse import urlsplit

try:
    from openpyxl import load_workbook
except ImportError:
    load_workbook = None

ALIASES = {
    "unit": ("单位名称", "单位", "单位全称", "组织", "组织名称", "所属单位", "规范单位名称", "目标单位", "部门", "机构名称", "owner", "organization", "org", "company"),
    "short_name": ("简称", "单位简称", "机构简称", "short name", "alias"),
    "former_name": ("旧名", "曾用名", "历史名称", "former name", "old name"),
    "english_name": ("英文名", "英文名称", "english name", "english_name"),
    "pinyin": ("拼音", "单位拼音", "pinyin"),
    "host": ("域名", "目标域名", "主机", "域名/主机", "网址", "网站地址", "网站链接", "资产地址", "资产信息", "域名信息", "url", "host", "hostname", "domain", "domain name", "fqdn"),
    "ip": ("ip", "ip地址", "目标ip", "公网ip", "ip/网段", "ip地址/网段", "服务器ip", "地址"),
    "port": ("端口", "port"),
    "protocol": ("协议", "protocol", "transport"),
    "source": ("来源", "数据来源", "source", "来源文件"),
    "source_url": ("来源链接", "依据链接", "链接", "url来源", "source url"),
    "notes": ("备注", "说明", "关系说明", "notes", "description"),
    "region": ("属地", "地区", "行政区", "区域", "city", "region"),
}
ENDPOINT_RE = re.compile(
    r"(?i)(?:https?://)?(?:\[[0-9a-f:]+\]|(?:\d{1,3}\.){3}\d{1,3}|"
    r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9-]{2,63})(?::\d{1,5})?"
)
NETWORK_RE = re.compile(r"(?<![0-9.])(?:[0-9]{1,3}\.){3}[0-9]{1,3}/[0-9]{1,2}(?![0-9])")


def clean(value):
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def header_key(value):
    value = unicodedata.normalize("NFKC", clean(value)).casefold()
    return re.sub(r"[\s_./\\（）()：:（）-]+", "", value)


def detect_columns(row):
    normalized = [header_key(value) for value in row]
    found = {}
    for field, names in ALIASES.items():
        candidates = {header_key(name) for name in names}
        for index, value in enumerate(normalized):
            if value in candidates:
                found[field] = index
                break
    return found


def parse_endpoint(raw):
    value = clean(raw).strip(" \t\r\n,，;；()（）<>\"'")
    if not value:
        return None
    candidate = value if "://" in value else "//" + value
    try:
        parts = urlsplit(candidate)
        host = (parts.hostname or "").strip().rstrip(".").lower()
        port = str(parts.port) if parts.port is not None else ""
    except ValueError:
        return None
    if not host:
        return None
    try:
        ipaddress.ip_address(host)
        is_ip = True
    except ValueError:
        is_ip = False
    if not is_ip:
        try:
            host = host.encode("idna").decode("ascii")
        except UnicodeError:
            return None
        if len(host) > 253 or "." not in host:
            return None
        if not all(re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label) for label in host.split(".")):
            return None
    return {"host": host, "ip": host if is_ip else "", "port": port, "is_ip": is_ip}


def extract_endpoints(value):
    found = []
    seen = set()
    for match in ENDPOINT_RE.finditer(clean(value)):
        item = parse_endpoint(match.group(0))
        if not item:
            continue
        key = (item["host"], item["port"])
        if key not in seen:
            seen.add(key)
            found.append(item)
    return found


def parse_ip_or_network(value):
    value = clean(value)
    if not value:
        return None, None
    try:
        address = ipaddress.ip_address(value)
        return str(address), None
    except ValueError:
        pass
    try:
        network = ipaddress.ip_network(value, strict=False)
        if "/" in value:
            return None, str(network)
    except ValueError:
        pass
    return None, None


def value_at(row, columns, field):
    index = columns.get(field)
    return clean(row[index]) if index is not None and index < len(row) else ""


def add_row(row, columns, source_file, source_link="", default_region=""):
    unit = value_at(row, columns, "unit")
    notes = value_at(row, columns, "notes")
    source = value_at(row, columns, "source") or source_file
    source_url = value_at(row, columns, "source_url")
    region = value_at(row, columns, "region") or default_region
    units = []
    assets = []
    networks = []

    if unit:
        variants = []
        for field, label in (
            ("short_name", "简称"),
            ("former_name", "旧名"),
            ("english_name", "英文名"),
            ("pinyin", "拼音"),
        ):
            variant = value_at(row, columns, field)
            if variant and variant.casefold() != unit.casefold():
                variants.append({"type": label, "value": variant})
        units.append({
            "unit": unit,
            "name_variants": variants,
            "subregion": region,
            "source": source,
            "source_url": source_url or source_link,
            "notes": notes,
            "source_file": source_file,
        })

    host_cell = value_at(row, columns, "host")
    ip_cell = value_at(row, columns, "ip")
    port_cell = value_at(row, columns, "port")
    proto_cell = value_at(row, columns, "protocol")
    endpoints = extract_endpoints(host_cell)
    if not endpoints:
        endpoints = extract_endpoints(ip_cell)

    explicit_ip, network = parse_ip_or_network(ip_cell)
    if network:
        networks.append({
            "unit": unit,
            "network": network,
            "source": source,
            "source_url": source_url or source_link,
            "notes": notes,
            "source_file": source_file,
        })
    for endpoint in endpoints:
        ip = endpoint["ip"] or explicit_ip or ""
        port = endpoint["port"] or port_cell
        assets.append({
            "unit": unit,
            "host": endpoint["host"] if not endpoint["is_ip"] else "",
            "ip": ip,
            "port": port,
            "protocol": proto_cell,
            "source": source,
            "source_url": source_url or source_link,
            "source_file": source_file,
            "notes": notes,
            "subregion": region,
        })
    if not endpoints and explicit_ip:
        assets.append({
            "unit": unit,
            "host": "",
            "ip": explicit_ip,
            "port": port_cell,
            "protocol": proto_cell,
            "source": source,
            "source_file": source_file,
            "notes": notes,
            "subregion": region,
            "source_url": source_url or source_link,
        })
    known_endpoints = {(item["host"], item["port"]) for item in endpoints}
    known_networks = {item["network"] for item in networks}
    mapped_indexes = set(columns.values())
    for index, cell in enumerate(row):
        if index in mapped_indexes:
            continue
        for endpoint in extract_endpoints(cell):
            key = (endpoint["host"], endpoint["port"])
            if key in known_endpoints:
                continue
            known_endpoints.add(key)
            assets.append({
                "unit": unit, "host": endpoint["host"] if not endpoint["is_ip"] else "",
                "ip": endpoint["ip"], "port": endpoint["port"], "protocol": proto_cell,
                "source": source, "source_url": source_url or source_link,
                "source_file": source_file, "notes": notes, "subregion": region,
            })
        for candidate in NETWORK_RE.findall(clean(cell)):
            _, network = parse_ip_or_network(candidate)
            if network and network not in known_networks:
                known_networks.add(network)
                networks.append({
                    "unit": unit, "network": network, "source": source,
                    "notes": notes, "source_file": source_file,
                })
    return units, assets, networks


def sheet_rows_xlsx(path):
    if load_workbook is None:
        raise RuntimeError("读取 XLSX 需要 openpyxl；请安装 scripts/requirements.txt")
    workbook = load_workbook(path, read_only=True, data_only=True)
    for sheet in workbook.worksheets:
        rows = sheet.iter_rows(values_only=True)
        buffered = []
        columns = {}
        for row in rows:
            row = list(row)
            candidate = detect_columns(row)
            if candidate and ("unit" in candidate or "host" in candidate or "ip" in candidate):
                columns = candidate
                break
            buffered.append(row)
        if columns:
            for row in rows:
                yield list(row), columns, sheet.title
        else:
            for row in buffered:
                for value in row:
                    for endpoint in extract_endpoints(value):
                        yield [endpoint["host"] + ((":" + endpoint["port"]) if endpoint["port"] else "")], {"host": 0}, sheet.title


def sheet_rows_xls(path):
    try:
        import xlrd
    except ImportError as exc:
        raise RuntimeError("读取 XLS 需要 xlrd；请安装 scripts/requirements.txt") from exc
    book = xlrd.open_workbook(str(path), on_demand=True)
    for sheet in book.sheets():
        header_row = None
        columns = {}
        for row_index in range(min(sheet.nrows, 30)):
            row = sheet.row_values(row_index)
            candidate = detect_columns(row)
            if candidate and ("unit" in candidate or "host" in candidate or "ip" in candidate):
                header_row = row_index
                columns = candidate
                break
        if header_row is not None:
            for row_index in range(header_row + 1, sheet.nrows):
                yield sheet.row_values(row_index), columns, sheet.name
        else:
            for row_index in range(sheet.nrows):
                for value in sheet.row_values(row_index):
                    for endpoint in extract_endpoints(value):
                        yield [endpoint["host"] + ((":" + endpoint["port"]) if endpoint["port"] else "")], {"host": 0}, sheet.name
        book.unload_sheet(sheet.name)


def read_text(path):
    data = path.read_bytes()
    for encoding in ("utf-8-sig", "gb18030", "utf-8"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def process_directory(input_dir, region):
    units, assets, networks, errors = [], [], [], []
    files = sorted(
        p for p in input_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in {".xls", ".xlsx", ".txt", ".csv"}
        and not p.name.startswith("~$")
    )
    for path in files:
        try:
            if path.suffix.lower() in {".xlsx", ".xls"}:
                row_iter = sheet_rows_xlsx(path) if path.suffix.lower() == ".xlsx" else sheet_rows_xls(path)
                for row, columns, sheet in row_iter:
                    new_units, new_assets, new_networks = add_row(row, columns, path.name, default_region=region)
                    units.extend(new_units)
                    assets.extend(new_assets)
                    networks.extend(new_networks)
            else:
                content = read_text(path)
                if path.suffix.lower() == ".csv":
                    sample = content[:8192]
                    try:
                        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
                    except csv.Error:
                        dialect = csv.excel
                    rows = list(csv.reader(content.splitlines(), dialect))
                    header_index = next((i for i, row in enumerate(rows[:30]) if detect_columns(row)), None)
                    if header_index is None:
                        for line in content.splitlines():
                            endpoints = extract_endpoints(line)
                            for endpoint in endpoints:
                                assets.append({
                                    "unit": "", "host": endpoint["host"] if not endpoint["is_ip"] else "",
                                    "ip": endpoint["ip"], "port": endpoint["port"], "protocol": "",
                                    "source": path.name, "source_file": path.name, "notes": line.strip(),
                                    "subregion": region,
                                })
                    else:
                        columns = detect_columns(rows[header_index])
                        for row in rows[header_index + 1:]:
                            new_units, new_assets, new_networks = add_row(row, columns, path.name, default_region=region)
                            units.extend(new_units)
                            assets.extend(new_assets)
                            networks.extend(new_networks)
                else:
                    for line in content.splitlines():
                        for candidate in NETWORK_RE.findall(line):
                            _, network = parse_ip_or_network(candidate)
                            if network:
                                networks.append({
                                    "unit": "", "network": network, "source": path.name,
                                    "notes": line.strip(), "source_file": path.name,
                                })
                        endpoints = extract_endpoints(line)
                        for endpoint in endpoints:
                            assets.append({
                                "unit": "", "host": endpoint["host"] if not endpoint["is_ip"] else "",
                                "ip": endpoint["ip"], "port": endpoint["port"], "protocol": "",
                                "source": path.name, "source_file": path.name, "notes": line.strip(),
                                "subregion": region,
                            })
        except (OSError, ValueError, RuntimeError, csv.Error) as exc:
            errors.append({"file": path.name, "error": str(exc)})
    return {
        "region": region,
        "files_seen": len(files),
        "units": units,
        "assets": assets,
        "appendices": {"network_candidates": networks},
        "errors": errors,
    }


def main():
    parser = argparse.ArgumentParser(description="Normalize optional XLS/XLSX/TXT/CSV asset lists.")
    parser.add_argument("--region", required=True)
    parser.add_argument("--input-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if not args.input_dir.is_dir():
        parser.error("输入目录不存在或不是目录")
    result = process_directory(args.input_dir, args.region)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "files_seen": result["files_seen"],
        "units": len(result["units"]),
        "assets": len(result["assets"]),
        "network_candidates": len(result["appendices"]["network_candidates"]),
        "errors": len(result["errors"]),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
