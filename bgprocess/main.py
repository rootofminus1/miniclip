import os
import time
import requests



API_BASE = "https://h2nr8b2xq5.execute-api.eu-west-1.amazonaws.com/dev"
DIR_TO_WATCH = "/home/the/Videos/Replays"
POLL_SECONDS = 5
USER_ID = "u2"
seen = set()


def upload(api_base: str, user_id: str, filepath: str):
    filename = os.path.basename(filepath)
    print(f"[watcher] uploading {filename}...")

    res = requests.post(
        f"{api_base}/uploads/presign",
        json={"filename": filename},
        headers={"x-user-id": user_id, "content-type": "application/json"},
    )
    res.raise_for_status()
    data = res.json()

    presigned_url = data["presigned_url"]

    with open(filepath, "rb") as f:
        put_res = requests.put(
            presigned_url,
            data=f,
            headers={"content-type": "video/mp4"},
        )

    if put_res.status_code not in (200, 201, 204):
        print(f"[watcher] upload failed: {put_res.status_code} {put_res.text[:200]}")
        return

    print(f"[watcher] uploaded {filename} → {data['s3_key']}")



def scan(watch_dir: str, api_base: str, user_id: str, seen: set):
    print("[watcher] scanning")
    for fname in os.listdir(watch_dir):
        if not fname.lower().endswith(".mp4"):
            continue

        fpath = os.path.join(watch_dir, fname)

        if fpath in seen:
            continue

        seen.add(fpath)

        print(f"[watcher] new vid: {fpath}")

        try:
            upload(api_base, user_id, fpath)
        except Exception as e:
            print(f"[watcher] error uploading {fname}: {e}")


def main():
    print(f"[watcher] watching {DIR_TO_WATCH} as {USER_ID}, polling every {POLL_SECONDS}s")

    seen = set()
    for fname in os.listdir(DIR_TO_WATCH):
        if fname.lower().endswith(".mp4"):
            seen.add(os.path.join(DIR_TO_WATCH, fname))
    print(f"[watcher] skipping {len(seen)} existing files, watching {DIR_TO_WATCH} as {USER_ID}")

    while True:
        scan(DIR_TO_WATCH, API_BASE, USER_ID, seen)
        time.sleep(POLL_SECONDS)

if __name__ == "__main__":
    main()