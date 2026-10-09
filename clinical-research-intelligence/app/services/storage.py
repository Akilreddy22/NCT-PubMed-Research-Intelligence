"""
storage.py - saves figure image files.

Version 1 saves to the local folder  data/figures/<pmid>/<file>.
The database only keeps the PATH, never the image bytes.
To move to S3 / Cloudflare R2 later, only THIS file changes: replace the body of save()
with boto3  s3.put_object(Bucket=..., Key=..., Body=content)  and return the object key/URL.
"""
import re

from app.config import settings


def save_figure(pmid: str, filename: str, content: bytes) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", filename)
    folder = settings.data_dir / "figures" / str(pmid)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / safe
    path.write_bytes(content)
    return str(path)
