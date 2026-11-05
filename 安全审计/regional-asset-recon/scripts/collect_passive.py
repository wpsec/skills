#!/usr/bin/env python3
"""Query only FOFA and Shodan's existing indexes; never scan or probe target hosts."""

import argparse
import base64
import hashlib
import ipaddress
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

FOFA_FIELDS = (
    "host,ip,port,protocol,title,domain,icp,cert.sn,cert.subject.org,"
    "cert.subject.cn,cert.domain,server,lastupdatetime,city,region,product,"
    "product.version,cname"
)
FOFA_MAX_REQUESTS = 10000
FOFA_MAX_RECORDS = 100000
SHODAN_MAX_REQUESTS = 2500
MAX_PAGES_PER_QUERY = 20
PAGE_SIZE = 500
TIMEOUT_SECONDS = 20
RETRIES = 2
RETRYABLE_HTTP = {500, 502, 503, 504}


class ApiFailure(Exception):
    def __init__(self, provider, status, kind):
        super().__init__(kind)
        self.provider = provider
        self.status = status
        self.kind = kind


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def read_nonempty_lines(path):
    try:
        return [line.strip() for line in Path(path).read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    except OSError as exc:
        raise ValueError("凭据文件不可读") from exc


def fofa_credentials(path):
    values = read_nonempty_lines(path)
    if len(values) < 2:
        raise ValueError("FOFA 凭据格式不符")
    return values[0], values[1]


def shodan_credentials(path):
    values = read_nonempty_lines(path)
    if not values:
        raise ValueError("Shodan 凭据文件为空")
    return values[-1]


def scrub(value):
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if re.search(r"(api.?key|token|secret|password)", str(key), re.I)
            else scrub(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [scrub(item) for item in value]
    return value


def http_json(provider, url, counters, state):
    for attempt in range(RETRIES + 1):
        limit = FOFA_MAX_REQUESTS if provider == "fofa" else SHODAN_MAX_REQUESTS
        totals = state.setdefault("api_totals", {}).setdefault(provider, {"requests": 0, "records": 0})
        if totals["requests"] >= limit:
            raise ApiFailure(provider, 0, "request_limit")
        counters[provider]["requests"] += 1
        totals["requests"] += 1
        save_state(state["_path"], state)
        request = Request(url, headers={"User-Agent": "regional-asset-recon/1.0"})
        try:
            with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
                payload = json.loads(response.read().decode("utf-8", errors="replace"))
                return response.status, payload
        except HTTPError as exc:
            status = exc.code
            try:
                payload = json.loads(exc.read().decode("utf-8", errors="replace"))
            except (ValueError, OSError):
                payload = {}
            if status == 429:
                return status, payload
            if status in RETRYABLE_HTTP and attempt < RETRIES:
                time.sleep(2 ** attempt)
                continue
            return status, payload
        except (URLError, TimeoutError, OSError, ValueError):
            if attempt < RETRIES:
                time.sleep(2 ** attempt)
                continue
            return 0, {}
    return 0, {}


def save_state(path, state):
    path = Path(path)
    temp_path = path.with_name(path.name + ".tmp")
    temp_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    temp_path.replace(path)


def append_record(handle, provider, query, unit, record):
    item = {
        "provider": provider,
        "query": query,
        "unit": unit,
        "retrieved_at": utc_now(),
        "record": scrub(record),
    }
    handle.write(json.dumps(item, ensure_ascii=False) + "\n")
    handle.flush()


def rows_to_dicts(results, fields):
    for item in results or []:
        if isinstance(item, dict):
            yield item
        elif isinstance(item, (list, tuple)):
            yield dict(zip(fields, item))


def query_identity(item):
    return digest(json.dumps(item, ensure_ascii=False, sort_keys=True))


def fofa_url(email, key, query, cursor):
    params = {
        "email": email,
        "key": key,
        "qbase64": base64.b64encode(query.encode("utf-8")).decode("ascii"),
        "fields": FOFA_FIELDS,
        "size": PAGE_SIZE,
        "r_type": "json",
    }
    if cursor:
        params["next"] = cursor
    return "https://fofa.info/api/v1/search/next?" + urlencode(params)


def fofa_error(payload):
    if not isinstance(payload, dict):
        return "invalid_response"
    if payload.get("error") is True:
        code = text(payload.get("code") or payload.get("errmsg") or payload.get("message"))
        if "820041" in code or "limit" in code.casefold() or "quota" in code.casefold():
            return "quota"
        return "api_error"
    return ""


def text(value):
    return "" if value is None else str(value)


def authorized_scope(plan):
    scope = plan.get("scope")
    if not isinstance(scope, dict) or not text(scope.get("authorization_reference")).strip():
        return set(), set(), False
    raw_units = scope.get("authorized_units", [])
    raw_vendors = scope.get("authorized_vendors", [])
    if not isinstance(raw_units, list):
        raw_units = []
    if not isinstance(raw_vendors, list):
        raw_vendors = []
    units = {
        text(value).strip().casefold()
        for value in raw_units + raw_vendors
        if text(value).strip()
    }
    raw_ips = scope.get("authorized_ips", [])
    if not isinstance(raw_ips, list):
        raw_ips = []
    ips = {
        text(value).strip()
        for value in raw_ips
        if text(value).strip()
    }
    return units, ips, True


def collect_fofa(plan, workdir, output, state, coverage):
    fofa_plan = plan.get("fofa_queries", [])
    if not fofa_plan:
        coverage["fofa"]["status"] = "no_queries"
        return
    authorized_units, _, scope_confirmed = authorized_scope(plan)
    if not scope_confirmed:
        coverage["fofa"]["status"] = "scope_unconfirmed"
        coverage["fofa"]["skipped_scope_unconfirmed"] = len(fofa_plan)
        return
    try:
        email, key = fofa_credentials(workdir / "fofa.txt")
    except ValueError as exc:
        coverage["fofa"]["status"] = "credential_unavailable"
        coverage["fofa"]["error"] = str(exc)
        return

    progress = state.setdefault("fofa", {})
    with output.open("a", encoding="utf-8") as handle:
        for item in fofa_plan:
            query = text(item.get("query")).strip()
            unit = text(item.get("unit")).strip()
            label = text(item.get("label")).strip()
            if not query:
                coverage["fofa"]["skipped"] += 1
                continue
            if not unit or unit.casefold() not in authorized_units:
                coverage["fofa"]["skipped_scope_unconfirmed"] += 1
                continue
            if item.get("fpoint_free_confirmed") is not True:
                coverage["fofa"]["skipped_fpoint_unverified"] += 1
                continue
            identity = query_identity(item)
            checkpoint = progress.get(identity, {"page": 0, "next": "", "done": False})
            if checkpoint.get("done"):
                coverage["fofa"]["resumed_done"] += 1
                continue
            while checkpoint["page"] < MAX_PAGES_PER_QUERY:
                if coverage["fofa"]["requests"] >= FOFA_MAX_REQUESTS:
                    coverage["fofa"]["status"] = "request_limit"
                    return
                if coverage["fofa"]["records"] >= FOFA_MAX_RECORDS:
                    coverage["fofa"]["status"] = "record_limit"
                    return
                if state.get("api_totals", {}).get("fofa", {}).get("records", 0) >= FOFA_MAX_RECORDS:
                    coverage["fofa"]["status"] = "record_limit"
                    return
                status, payload = http_json("fofa", fofa_url(email, key, query, checkpoint.get("next", "")), coverage, state)
                if status == 429:
                    coverage["fofa"]["status"] = "http_429"
                    return
                if status != 200:
                    coverage["fofa"]["errors"] += 1
                    coverage["fofa"]["last_error"] = "http_" + str(status)
                    if status in (401, 403):
                        coverage["fofa"]["status"] = "authentication_or_permission"
                        return
                    break
                error = fofa_error(payload)
                if error == "quota":
                    coverage["fofa"]["status"] = "quota_limited"
                    return
                if error:
                    coverage["fofa"]["errors"] += 1
                    coverage["fofa"]["last_error"] = error
                    break
                consumed = int(payload.get("consumed_fpoint") or 0)
                required = int(payload.get("required_fpoints") or 0)
                coverage["fofa"]["consumed_fpoints"] += consumed
                if consumed > 0 or required > 0:
                    coverage["fofa"]["status"] = "fpoint_signal_stopped"
                    return
                results = list(rows_to_dicts(payload.get("results"), FOFA_FIELDS.split(",")))
                remaining = FOFA_MAX_RECORDS - coverage["fofa"]["records"]
                for record in results[:remaining]:
                    record["_query_label"] = label
                    append_record(handle, "FOFA", query, unit, record)
                    coverage["fofa"]["records"] += 1
                    state.setdefault("api_totals", {}).setdefault("fofa", {"requests": 0, "records": 0})["records"] += 1
                coverage["fofa"]["completed_queries"].add(identity)
                checkpoint["page"] += 1
                checkpoint["next"] = text(payload.get("next"))
                checkpoint["done"] = not checkpoint["next"]
                progress[identity] = checkpoint
                save_state(state["_path"], state)
                if checkpoint["done"] or len(results) < PAGE_SIZE:
                    checkpoint["done"] = True
                    progress[identity] = checkpoint
                    coverage["fofa"]["completed_queries"].add(identity)
                    save_state(state["_path"], state)
                    break
            if not checkpoint.get("done"):
                coverage["fofa"]["page_cap_queries"] += 1
    if coverage["fofa"]["status"] == "pending":
        coverage["fofa"]["status"] = "complete"


def shodan_info(key, coverage, state):
    url = "https://api.shodan.io/api-info?" + urlencode({"key": key})
    status, payload = http_json("shodan", url, coverage, state)
    if status != 200 or not isinstance(payload, dict):
        return None
    return payload


def shodan_record(ip, host_data, service):
    location = host_data.get("location") or {}
    http = service.get("http") or {}
    ssl = service.get("ssl") or {}
    cert = ssl.get("cert") or {}
    subject = cert.get("subject") or {}
    return {
        "ip": ip,
        "ip_geo": "/".join(filter(None, [
            text(location.get("country_name")),
            text(location.get("region_code") or location.get("region_name")),
            text(location.get("city")),
        ])),
        "hostnames": host_data.get("hostnames") or [],
        "domains": host_data.get("domains") or [],
        "port": service.get("port"),
        "protocol": service.get("transport") or service.get("protocol"),
        "product": " ".join(filter(None, [text(service.get("product")), text(service.get("version"))])),
        "title": http.get("title") or "",
        "server": http.get("server") or service.get("http_server") or "",
        "cert_cn": subject.get("CN") or "",
        "cert_org": subject.get("O") or "",
        "cert_serial": cert.get("serial") or "",
        "cert_fingerprint": cert.get("fingerprint") or {},
        "cert_domains": cert.get("extensions", {}).get("subject_alt_name", []) if isinstance(cert.get("extensions"), dict) else [],
        "last_seen": service.get("timestamp") or host_data.get("last_update") or "",
        "module": (service.get("_shodan") or {}).get("module") or "",
    }


def unpack_shodan_match(match):
    ip_value = match.get("ip_str") or match.get("ip") or ""
    service = {
        "port": match.get("port"),
        "transport": match.get("transport"),
        "product": match.get("product"),
        "version": match.get("version"),
        "http": match.get("http"),
        "ssl": match.get("ssl"),
        "_shodan": match.get("_shodan"),
        "timestamp": match.get("timestamp"),
    }
    host_data = {
        "location": match.get("location"),
        "hostnames": match.get("hostnames"),
        "domains": match.get("domains"),
    }
    return ip_value, shodan_record(ip_value, host_data, service)


def shodan_search_requires_credit(query, page):
    return page > 1 or bool(re.search(r"(?:^|\s)[a-z][a-z0-9_.-]*:", query, re.I))


def collect_shodan(plan, workdir, output, state, coverage):
    authorized_units, authorized_ips, scope_confirmed = authorized_scope(plan)
    if not scope_confirmed:
        coverage["shodan"]["status"] = "scope_unconfirmed"
        coverage["shodan"]["skipped_scope_unconfirmed"] = (
            len(plan.get("shodan_ips", [])) + len(plan.get("shodan_queries", []))
        )
        return
    allowed_ips = set()
    for value in authorized_ips:
        try:
            allowed_ips.add(str(ipaddress.ip_address(value)))
        except ValueError:
            continue
    authorized_ips = allowed_ips
    scoped_ips = []
    for value in plan.get("shodan_ips", []):
        try:
            normalized_ip = str(ipaddress.ip_address(text(value).strip()))
        except ValueError:
            scoped_ips.append(value)
            continue
        if normalized_ip in authorized_ips:
            scoped_ips.append(normalized_ip)
        else:
            coverage["shodan"]["skipped_scope_unconfirmed"] += 1
    scoped_queries = []
    for item in plan.get("shodan_queries", []):
        if text(item.get("unit")).strip().casefold() in authorized_units:
            scoped_queries.append(item)
        else:
            coverage["shodan"]["skipped_scope_unconfirmed"] += 1
    if not scoped_ips and not scoped_queries:
        coverage["shodan"]["status"] = "no_in_scope_queries"
        return
    try:
        key = shodan_credentials(workdir / "shodan.txt")
    except ValueError as exc:
        coverage["shodan"]["status"] = "credential_unavailable"
        coverage["shodan"]["error"] = str(exc)
        return
    info = shodan_info(key, coverage, state)
    if info is None:
        coverage["shodan"]["status"] = "api_info_failed"
        return
    coverage["shodan"]["query_credits_before"] = info.get("query_credits")
    coverage["shodan"]["scan_credits_before"] = info.get("scan_credits")
    query_credits = info.get("query_credits")
    credits_unlimited = query_credits == -1 or (info.get("usage_limits") or {}).get("query_credits") == -1

    progress_ips = state.setdefault("shodan_ips", {})
    progress_queries = state.setdefault("shodan_queries", {})
    with output.open("a", encoding="utf-8") as handle:
        for raw_ip in scoped_ips:
            ip = text(raw_ip).strip()
            try:
                parsed_ip = ipaddress.ip_address(ip)
            except ValueError:
                coverage["shodan"]["skipped_ips"] += 1
                continue
            if not parsed_ip.is_global:
                coverage["shodan"]["skipped_non_global_ips"] += 1
                continue
            if progress_ips.get(ip) == "done":
                continue
            if coverage["shodan"]["requests"] >= SHODAN_MAX_REQUESTS:
                coverage["shodan"]["status"] = "request_limit"
                return
            endpoint = "https://api.shodan.io/shodan/host/" + ip + "?" + urlencode({"key": key, "minify": "false"})
            status, payload = http_json("shodan", endpoint, coverage, state)
            if status == 429:
                coverage["shodan"]["status"] = "http_429"
                return
            if status == 200 and isinstance(payload, dict):
                hostnames = payload.get("hostnames") or []
                unit = ""
                for service in payload.get("data") or []:
                    record = shodan_record(ip, payload, service)
                    record["hostnames"] = hostnames
                    append_record(handle, "Shodan host lookup", ip, unit, record)
                    coverage["shodan"]["records"] += 1
                    state.setdefault("api_totals", {}).setdefault("shodan", {"requests": 0, "records": 0})["records"] += 1
                progress_ips[ip] = "done"
                coverage["shodan"]["completed_ips"] += 1
                save_state(state["_path"], state)
            elif status in (401, 403):
                coverage["shodan"]["status"] = "authentication_or_permission"
                return
            else:
                coverage["shodan"]["errors"] += 1

        for item in scoped_queries:
            query = text(item.get("query")).strip()
            unit = text(item.get("unit")).strip()
            label = text(item.get("label")).strip()
            if not query:
                coverage["shodan"]["skipped_queries"] += 1
                continue
            identity = query_identity(item)
            checkpoint = progress_queries.get(identity, {"page": 1, "done": False})
            if checkpoint.get("done"):
                continue
            while checkpoint["page"] <= MAX_PAGES_PER_QUERY:
                page = checkpoint["page"]
                if shodan_search_requires_credit(query, page) and not credits_unlimited:
                    if not isinstance(query_credits, int) or query_credits <= 0:
                        coverage["shodan"]["skipped_credit_queries"] += 1
                        checkpoint["done"] = True
                        progress_queries[identity] = checkpoint
                        save_state(state["_path"], state)
                        break
                    query_credits -= 1
                if coverage["shodan"]["requests"] >= SHODAN_MAX_REQUESTS:
                    coverage["shodan"]["status"] = "request_limit"
                    return
                params = {"key": key, "query": query, "page": page, "minify": "false"}
                url = "https://api.shodan.io/shodan/host/search?" + urlencode(params)
                status, payload = http_json("shodan", url, coverage, state)
                if status == 429:
                    coverage["shodan"]["status"] = "http_429"
                    return
                if status == 200 and isinstance(payload, dict):
                    matches = payload.get("matches") or []
                    for match in matches:
                        ip, record = unpack_shodan_match(match)
                        record["_query_label"] = label
                        append_record(handle, "Shodan search", query, unit, record)
                        coverage["shodan"]["records"] += 1
                        state.setdefault("api_totals", {}).setdefault("shodan", {"requests": 0, "records": 0})["records"] += 1
                    checkpoint["page"] += 1
                    checkpoint["done"] = not matches or len(matches) < 100
                    progress_queries[identity] = checkpoint
                    coverage["shodan"]["completed_queries"].add(identity)
                    save_state(state["_path"], state)
                    if checkpoint["done"]:
                        break
                elif status in (401, 403):
                    coverage["shodan"]["status"] = "authentication_or_permission"
                    return
                else:
                    coverage["shodan"]["errors"] += 1
                    break
            if not checkpoint.get("done"):
                coverage["shodan"]["page_cap_queries"] += 1
    final_info = shodan_info(key, coverage, state)
    if final_info:
        coverage["shodan"]["query_credits_after"] = final_info.get("query_credits")
        coverage["shodan"]["scan_credits_after"] = final_info.get("scan_credits")
    if coverage["shodan"]["status"] == "pending":
        coverage["shodan"]["status"] = "complete"


def new_coverage():
    return {
        "fofa": {
            "status": "pending", "requests": 0, "records": 0, "errors": 0,
            "skipped": 0, "skipped_fpoint_unverified": 0, "consumed_fpoints": 0,
            "skipped_scope_unconfirmed": 0,
            "completed_queries": set(), "resumed_done": 0, "page_cap_queries": 0,
        },
        "shodan": {
            "status": "pending", "requests": 0, "records": 0, "errors": 0,
            "completed_ips": 0, "skipped_ips": 0, "skipped_non_global_ips": 0,
            "skipped_queries": 0, "skipped_credit_queries": 0,
            "skipped_scope_unconfirmed": 0,
            "completed_queries": set(), "page_cap_queries": 0,
        },
    }


def serializable_coverage(coverage):
    result = {}
    for provider, values in coverage.items():
        result[provider] = {
            key: sorted(value) if isinstance(value, set) else value
            for key, value in values.items()
        }
    return result


def reconcile_output_totals(output_path, state):
    totals = state.setdefault("api_totals", {})
    for provider in ("fofa", "shodan"):
        totals.setdefault(provider, {"requests": 0, "records": 0})
    if not Path(output_path).exists():
        return
    actual = {"fofa": 0, "shodan": 0}
    with Path(output_path).open(encoding="utf-8") as handle:
        for line in handle:
            try:
                provider = json.loads(line).get("provider", "")
            except (ValueError, AttributeError):
                continue
            if provider == "FOFA":
                actual["fofa"] += 1
            elif provider.startswith("Shodan"):
                actual["shodan"] += 1
    for provider, count in actual.items():
        totals[provider]["records"] = max(totals[provider].get("records", 0), count)


def main():
    parser = argparse.ArgumentParser(description="Collect existing FOFA/Shodan index records only.")
    parser.add_argument("--plan", required=True, type=Path, help="Query plan JSON created for this authorized region")
    parser.add_argument("--workdir", type=Path, default=Path.cwd(), help="Directory containing fofa.txt and shodan.txt")
    parser.add_argument("--output", required=True, type=Path, help="JSONL output path, preferably under a temporary directory")
    parser.add_argument("--state", type=Path, help="Checkpoint path; defaults beside output")
    parser.add_argument("--coverage", type=Path, help="Coverage JSON path; defaults beside output")
    args = parser.parse_args()

    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    if not text(plan.get("region")):
        parser.error("query plan must include a region")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    state_path = args.state or args.output.with_suffix(".state.json")
    coverage_path = args.coverage or args.output.with_suffix(".coverage.json")
    if state_path.exists() and not args.output.exists():
        parser.error("checkpoint exists without output; choose a new output path")
    if args.output.exists() and not state_path.exists():
        parser.error("output exists without checkpoint; choose a new output path to avoid repeated queries")
    state = {"_path": str(state_path)}
    if state_path.exists():
        state.update(json.loads(state_path.read_text(encoding="utf-8")))
        state["_path"] = str(state_path)
    elif args.output.exists():
        parser.error("output exists without checkpoint; choose a new output path to avoid repeated queries")
    reconcile_output_totals(args.output, state)
    coverage = new_coverage()
    try:
        collect_fofa(plan, args.workdir, args.output, state, coverage)
        collect_shodan(plan, args.workdir, args.output, state, coverage)
    except ApiFailure as exc:
        coverage[exc.provider]["status"] = exc.kind
    finally:
        report = serializable_coverage(coverage)
        for name, values in report.items():
            if values["status"] == "pending":
                values["status"] = "interrupted_or_partial"
            values["cumulative_requests"] = state.get("api_totals", {}).get(name, {}).get("requests", 0)
            values["cumulative_records"] = state.get("api_totals", {}).get(name, {}).get("records", 0)
        report["fofa"]["completed_query_count"] = sum(
            1 for item in state.get("fofa", {}).values() if isinstance(item, dict) and item.get("done")
        )
        report["shodan"]["completed_ip_count"] = sum(
            1 for value in state.get("shodan_ips", {}).values() if value == "done"
        )
        report["shodan"]["completed_search_count"] = sum(
            1 for item in state.get("shodan_queries", {}).values() if isinstance(item, dict) and item.get("done")
        )
        coverage_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        save_state(state_path, state)
        print(json.dumps({
            "region": text(plan.get("region")),
            "fofa": {key: value for key, value in report["fofa"].items() if key != "completed_queries"},
            "shodan": {key: value for key, value in report["shodan"].items() if key != "completed_queries"},
        }, ensure_ascii=False))


if __name__ == "__main__":
    main()
