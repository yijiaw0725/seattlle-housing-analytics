"""
King County Assessor Data Downloader
- Accepts the disclaimer automatically (checks the checkbox)
- Downloads a specified list of zip files from the assessor data portal
"""

import requests
from bs4 import BeautifulSoup
import os

BASE_URL = "https://info.kingcounty.gov/assessor/datadownload/default.aspx"
DOWNLOAD_DIR = "./kc_assessor_data"

# Files to download — matched against link text (case-insensitive)
TARGET_FILES = [
    "real property sales",
    "residential building",
    "parcel",
    "lookup",
]


def get_download_links(session):
    """Submit the disclaimer form and return all zip download links as {name: url}."""
    # Step 1: GET the page and extract hidden ASP.NET form fields
    resp = session.get(BASE_URL)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    form_data = {}
    for inp in soup.find_all("input"):
        name = inp.get("name", "")
        val = inp.get("value", "")
        if name:
            form_data[name] = val

    # Step 2: Check the disclaimer checkbox
    form_data["kingcounty_gov$cphContent$CheckBox1"] = "on"

    # Step 3: POST to accept the disclaimer
    resp2 = session.post(BASE_URL, data=form_data)
    resp2.raise_for_status()
    soup2 = BeautifulSoup(resp2.text, "html.parser")

    # Step 4: Collect all zip links
    links = {}
    for a in soup2.find_all("a", href=True):
        if ".zip" in a["href"].lower():
            links[a.get_text(strip=True).lower()] = a["href"]

    return links


def download_file(session, url, filepath):
    """Stream-download a file and print progress."""
    with session.get(url, stream=True) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        downloaded = 0
        with open(filepath, "wb") as f:
            for chunk in r.iter_content(chunk_size=65536):
                f.write(chunk)
                downloaded += len(chunk)
                if total:
                    pct = downloaded / total * 100
                    print(
                        f"\r  {downloaded/1024/1024:.2f} MB / {total/1024/1024:.2f} MB ({pct:.1f}%)",
                        end="",
                        flush=True,
                    )
    print()


def main():
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Referer": BASE_URL,
    })

    print("Fetching download links...")
    links = get_download_links(session)
    print(f"Found {len(links)} files on the portal.\n")

    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    for target in TARGET_FILES:
        # Find the matching link (partial match against link text)
        url = next((v for k, v in links.items() if target in k), None)

        if not url:
            print(f"[SKIP] '{target}' — not found on the portal.")
            continue

        filename = url.split("/")[-1]
        filepath = os.path.join(DOWNLOAD_DIR, filename)

        if os.path.exists(filepath):
            print(f"[SKIP] '{filename}' already exists, skipping.")
            continue

        print(f"[DOWN] {filename}")
        print(f"       {url}")
        download_file(session, url, filepath)
        print(f"       Saved: {filepath}\n")

    print("Done.")


if __name__ == "__main__":
    main()
