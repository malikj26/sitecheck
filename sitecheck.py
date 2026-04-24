import csv
import requests
import argparse
import subprocess
import json
import tempfile
from typing import List


def normalize_url(url: str) -> str:
    """
    Ensure the URL has a scheme. Default to https:// if missing.
    """
    url = url.strip()

    if not url.startswith(("http://", "https://")):
        return f"https://{url}"

    return url

import shutil
import subprocess
import json
import tempfile


def find_httpx_binary(httpx_path: str = "httpx") -> str | None:
    """
    Finds ProjectDiscovery httpx on Windows/Linux/macOS.
    Allows a custom path or uses PATH lookup.
    """
    found = shutil.which(httpx_path)

    if found:
        return found

    return None


def enrich_with_httpx(successful_sites, httpx_path="httpx"):
    httpx_binary = find_httpx_binary(httpx_path)

    if not httpx_binary:
        print("[WARNING] ProjectDiscovery httpx was not found.")
        print("Install it with:")
        print("  go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest")
        print("Then make sure your Go bin folder is in PATH.")
        return successful_sites

    urls = [site["url"] for site in successful_sites]

    with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8") as temp_file:
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

    result = subprocess.run(command, capture_output=True, text=True, check=False)

    for line in result.stdout.splitlines():
        if not line.strip():
            continue

        item = json.loads(line)

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

    return enriched_results

def load_sites_from_csv(file_path: str, column: str = "url") -> List[str]:
    sites = []

    try:
        with open(file_path, newline="") as f:
            reader = csv.DictReader(f)

            if column not in reader.fieldnames:
                raise ValueError(f"Column '{column}' not found in CSV")

            for row in reader:
                raw_site = row[column].strip()
                if raw_site:
                    normalized = normalize_url(raw_site)
                    sites.append(normalized)

    except FileNotFoundError:
        print(f"[ERROR] File not found: {file_path}")
    except Exception as e:
        print(f"[ERROR] Failed to read CSV: {e}")

    return sites


def check_websites(websites, timeout=5):
    successful_sites = []

    for site in websites:
        try:
            response = try_request(site, timeout)

            if response and 200 <= response.status_code < 400:
                print(f"[SUCCESS] {site} (Status: {response.status_code})")
                successful_sites.append({
                    "url": site,
                    "status_code": response.status_code
                })
            elif response:
                print(f"[WARNING] {site} (Status: {response.status_code})")
            else:
                print(f"[FAILED] {site} could not be reached")

        except Exception as e:
            print(f"[ERROR] {site}: {e}")

    return successful_sites

def try_request(url, timeout):
    try:
        return requests.get(url, timeout=timeout)
    except requests.exceptions.ConnectionError:
        if url.startswith("https://"):
            fallback = url.replace("https://", "http://", 1)
            try:
                return requests.get(fallback, timeout=timeout)
            except:
                return None
        return None

def save_to_csv(data, output_file="reachable_sites.csv"):
    if not data:
        print("[ERROR] No data to save.")
        return

    fieldnames = [
        "url",
        "status_code",
        "title",
        "webserver",
        "host_ip",
        "cdn",
        "cdn_name",
        "technologies",
    ]

    try:
        with open(output_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)

        print(f"[INFO] Results saved to {output_file}")

    except Exception as e:
        print(f"[ERROR] Failed to save CSV: {e}")

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Check website connectivity from CSV")

    # Existing args
    parser.add_argument("--input", required=True, help="Path to CSV file")
    parser.add_argument("--column", default="url", help="CSV column name")
    parser.add_argument("--timeout", type=int, default=5)
    parser.add_argument("--httpx-path", default="httpx", help="Path to httpx binary (default assumes it's in PATH)")

    args = parser.parse_args()

    sites = load_sites_from_csv(args.input, args.column)

    if not sites:
        print("[ERROR] No valid sites found in CSV")
        return

    successful_sites = check_websites(sites, args.timeout)

    print(f"\n[SUMMARY] {len(successful_sites)} sites reachable")

    if successful_sites:
        print("[INFO] Running httpx enrichment...")

        # 👇 PASS IT HERE
        enriched_results = enrich_with_httpx(
            successful_sites,
            args.httpx_path
        )

        choice = input("Would you like to save enriched results to CSV? (y/n): ").lower()

        if choice == "y":
            filename = input("Enter output filename (default: reachable_sites.csv): ").strip()
            if not filename:
                filename = "reachable_sites.csv"

            save_to_csv(enriched_results, filename)


if __name__ == "__main__":
    main()