import argparse
import csv
import json
import os
import shutil
import subprocess
import tempfile
from typing import List

import requests


CSV_FIELDNAMES = [
    "url",
    "status_code",
    "title",
    "webserver",
    "host_ip",
    "cdn",
    "cdn_name",
    "technologies",
]


def normalize_url(url: str) -> str:
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        return f"https://{url}"
    return url


def find_httpx_binary(httpx_path: str = "httpx") -> str | None:
    if os.path.isfile(httpx_path):
        return httpx_path

    found = shutil.which(httpx_path)
    if found:
        return found

    for path in [
        "/root/go/bin/httpx",
        os.path.expanduser("~/go/bin/httpx"),
        os.path.expanduser("~/go/bin/httpx.exe"),
    ]:
        if os.path.isfile(path):
            return path

    return None


def load_sites_from_csv(file_path: str, column: str = "url") -> List[str]:
    sites = []

    with open(file_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        if not reader.fieldnames or column not in reader.fieldnames:
            raise ValueError(f"Column '{column}' not found in CSV")

        for row in reader:
            raw_site = row.get(column, "").strip()
            if raw_site:
                sites.append(normalize_url(raw_site))

    return sites


def try_request(url: str, timeout: int):
    try:
        return requests.get(url, timeout=timeout, allow_redirects=True)

    except requests.exceptions.ConnectionError:
        if url.startswith("https://"):
            fallback = url.replace("https://", "http://", 1)
            try:
                return requests.get(fallback, timeout=timeout, allow_redirects=True)
            except requests.exceptions.RequestException:
                return None

    except requests.exceptions.RequestException:
        return None

    return None


def check_websites(websites: List[str], timeout: int = 5):
    successful_sites = []

    for site in websites:
        response = try_request(site, timeout)

        if response and 200 <= response.status_code < 400:
            print(f"[SUCCESS] {response.url} (Status: {response.status_code})")
            successful_sites.append({
                "url": response.url,
                "status_code": response.status_code,
            })
        elif response:
            print(f"[WARNING] {site} responded with status {response.status_code}")
        else:
            print(f"[FAILED] {site} could not be reached")

    return successful_sites


def enrich_with_httpx(successful_sites, httpx_path="httpx"):
    httpx_binary = find_httpx_binary(httpx_path)

    if not httpx_binary:
        print("[WARNING] ProjectDiscovery httpx was not found. Returning basic reachability results.")
        return successful_sites

    urls = [site["url"] for site in successful_sites]

    with tempfile.NamedTemporaryFile(
        mode="w",
        delete=False,
        encoding="utf-8",
        suffix=".txt",
    ) as temp_file:
        for url in urls:
            temp_file.write(url + "\n")
        temp_file_path = temp_file.name

    command = [
        httpx_binary,
        "-l", temp_file_path,
        "-json",
        "-tech-detect",
        "-status-code",
        "-title",
        "-web-server",
        "-cdn",
        "-ip",
        "-follow-redirects",
        "-silent",
    ]

    enriched_results = []

    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)

        if result.stderr:
            print(f"[HTTPX WARNING] {result.stderr.strip()}")

        for line in result.stdout.splitlines():
            if not line.strip():
                continue

            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue

            enriched_results.append({
                "url": item.get("url", ""),
                "status_code": item.get("status_code", ""),
                "title": item.get("title", ""),
                "webserver": item.get("webserver", ""),
                "host_ip": item.get("host_ip", ""),
                "cdn": item.get("cdn", ""),
                "cdn_name": item.get("cdn_name", ""),
                "technologies": ", ".join(item.get("tech", [])),
            })

    finally:
        try:
            os.remove(temp_file_path)
        except OSError:
            pass

    return enriched_results or successful_sites


def save_to_csv(data, output_file="reachable_sites.csv"):
    if not data:
        print("[ERROR] No data to save.")
        return

    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(data)

    print(f"[INFO] Results saved to {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Check website reachability from CSV and enrich reachable sites with httpx."
    )

    parser.add_argument("--input", required=True, help="Path to input CSV file")
    parser.add_argument("--column", default="url", help="CSV column name. Default: url")
    parser.add_argument("--timeout", type=int, default=5, help="Request timeout in seconds")
    parser.add_argument("--httpx-path", default="httpx", help="Path to ProjectDiscovery httpx binary")
    parser.add_argument("--output", default="sitecheck_results.csv", help="Output CSV path")
    parser.add_argument("--no-httpx", action="store_true", help="Skip httpx enrichment")

    args = parser.parse_args()

    try:
        sites = load_sites_from_csv(args.input, args.column)
    except Exception as e:
        print(f"[ERROR] {e}")
        raise SystemExit(1)

    if not sites:
        print("[ERROR] No valid sites found in CSV")
        raise SystemExit(1)

    successful_sites = check_websites(sites, args.timeout)
    print(f"\n[SUMMARY] {len(successful_sites)} sites reachable")

    if not successful_sites:
        raise SystemExit(0)

    if args.no_httpx:
        results = successful_sites
    else:
        print("[INFO] Running httpx enrichment...")
        results = enrich_with_httpx(successful_sites, args.httpx_path)

    save_to_csv(results, args.output)


if __name__ == "__main__":
    main()