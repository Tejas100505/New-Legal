"""
Live Verification of CMU Enron Dataset Source
Empirically queries the live URL and inspects response headers, magic bytes, and tar members.
"""

import io
import time
import tarfile
import requests

def main():
    url = "https://www.cs.cmu.edu/~enron/enron_mail_20150507.tar.gz"
    print("=" * 80)
    print("LIVE RE-VERIFICATION OF CMU ENRON DATASET SOURCE")
    print("=" * 80)
    print(f"Target URL: {url}")
    print("Sending live HTTP GET request (streaming)...")

    t0 = time.time()
    resp = requests.get(url, stream=True, timeout=25)
    connect_time = time.time() - t0

    print(f"\n[1] CONNECTION CONFIRMATION:")
    print(f"  HTTP Status Code: {resp.status_code} ({resp.reason})")
    print(f"  Connection Time: {connect_time:.2f} seconds")

    print(f"\n[2] RESPONSE HEADERS:")
    interesting_headers = ["content-length", "content-type", "last-modified", "server", "etag", "date", "accept-ranges"]
    for h in interesting_headers:
        if h in resp.headers:
            print(f"  {h}: {resp.headers[h]}")

    print(f"\n[3] FIRST BYTES INSPECTION:")
    first_chunk = resp.raw.read(1024)
    print(f"  Bytes read: {len(first_chunk)}")
    print(f"  Hex representation (first 32 bytes): {first_chunk[:32].hex()}")
    is_gzip = (first_chunk[:2] == b"\x1f\x8b")
    print(f"  GZIP Magic Bytes (0x1F8B): {is_gzip}")

    print(f"\n[4] LIVE TAR ARCHIVE STREAM DECOMPRESSION:")
    # Read a modest buffer (1.5 MB) to decompress initial tar headers
    more_bytes = resp.raw.read(1536 * 1024)
    combined = io.BytesIO(first_chunk + more_bytes)
    
    tar = tarfile.open(fileobj=combined, mode="r:gz")
    members_found = []
    for member in tar:
        if member.isfile():
            members_found.append(member)
            if len(members_found) >= 5:
                break

    print(f"  Successfully decompressed initial members from stream:")
    for i, m in enumerate(members_found, 1):
        f = tar.extractfile(m)
        content_snippet = f.read(150).decode("latin1", errors="replace").replace("\n", " ").strip()
        print(f"  {i}. Name: {m.name}")
        print(f"     Size: {m.size} bytes")
        print(f"     Preview: {content_snippet[:100]}...")

    resp.close()
    print("\n" + "=" * 80)
    print("LIVE RE-VERIFICATION SUCCESSFUL: SOURCE IS ACTIVE, LEGITIMATE, AND REACHABLE")
    print("=" * 80)

if __name__ == "__main__":
    main()
