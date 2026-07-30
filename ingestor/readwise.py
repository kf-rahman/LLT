"""Readwise Reader connector.

Implements the Connector protocol over Readwise's Reader API
(GET /api/v3/list/?withHtmlContent=true), yielding one IngestEvent per saved
document with its html_content as the bytes. The rest of the pipeline (classify
-> html recipe -> chunk/embed -> idempotent memory -> trace) is unchanged.

Auth: a token from https://readwise.io/access_token, read from the READWISE_TOKEN
env var (put it in a gitignored .env — never commit it). Uses stdlib urllib so
there's no new dependency. Respects the 20 req/min list limit by backing off on
429 using the Retry-After header.

Docs: https://readwise.io/reader_api
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Iterator

from .change import content_hash
from .models import IngestEvent

READER_LIST_URL = "https://readwise.io/api/v3/list/"


class ReadwiseConnector:
    def __init__(
        self,
        token: str | None = None,
        updated_after: str | None = None,
        source: str = "readwise",
        location: str | None = None,
    ):
        self.token = token or os.getenv("READWISE_TOKEN")
        if not self.token:
            raise RuntimeError(
                "READWISE_TOKEN is not set. Put it in a gitignored .env "
                "(READWISE_TOKEN=...) — get one at https://readwise.io/access_token"
            )
        self.updated_after = updated_after
        self.source = source
        self.location = location

    def _get(self, cursor: str | None) -> dict:
        params = {"withHtmlContent": "true"}
        if self.updated_after:
            params["updatedAfter"] = self.updated_after
        if self.location:
            params["location"] = self.location
        if cursor:
            params["pageCursor"] = cursor
        url = f"{READER_LIST_URL}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={"Authorization": f"Token {self.token}"})
        while True:
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    return json.load(resp)
            except urllib.error.HTTPError as e:
                if e.code == 429:  # rate limited — respect Retry-After and retry
                    wait = int(e.headers.get("Retry-After", "5"))
                    time.sleep(wait)
                    continue
                raise

    def list_events(self) -> Iterator[IngestEvent]:
        cursor: str | None = None
        while True:
            page = self._get(cursor)
            for doc in page.get("results", []):
                html = doc.get("html_content") or ""
                if not html.strip():
                    continue  # nothing to ingest (metadata-only doc)
                data = html.encode("utf-8")
                yield IngestEvent(
                    path=f"{self.source}://{doc['id']}",
                    content_hash=content_hash(data),
                    mime="text/html",
                    size=len(data),
                    read=(lambda d=data: d),
                )
            cursor = page.get("nextPageCursor")
            if not cursor:
                break
