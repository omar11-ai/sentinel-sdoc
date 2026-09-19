"""Dataset loader — SENTINEL extends the OFFICIAL participant loader.

The organizers ship a stdlib-only `loader.py` (see official_loader.py, unmodified)
with a documented API:  Inbox(source).emails() / .get(id) / .read_bytes(path) /
.read_text(path) / .submit(sub) / .sample_submission() / iteration.
SENTINEL subclasses it and adds tolerant accessors + SI/BL guessing + lanes.
Same class name, drop-in compatible.
"""
from __future__ import annotations

import re
from pathlib import Path

import config
from official_loader import Inbox as _OfficialInbox


class Inbox(_OfficialInbox):
    def __init__(self, source: str | Path | None = None, mode: str | None = None):
        src = source if source is not None else (
            config.SERVER_URL if (mode or config.MODE) == "server" else config.DATA_DIR)
        super().__init__(str(src))
        self.mode = "server" if self.is_http else "folder"
        if self.mode == "folder":
            p = Path(self.source)
            self.root = p
            self.inbox_dir = p / "inbox" if (p / "inbox").exists() else p
            self.attach_dir = (p / "attachments" if (p / "attachments").exists()
                               else p.parent / "attachments")
        else:
            self.root = self.inbox_dir = self.attach_dir = None
        self._emails_cache: list[dict] | None = None

    # ---------- compatibility with pipeline ----------
    def emails(self) -> list[dict]:
        if self._emails_cache is None:
            self._emails_cache = super().emails()
        return self._emails_cache

    def all_ids(self) -> list[str]:
        return [self.get_id(e) for e in self.emails()]

    def read_bytes(self, att_path: str) -> bytes | None:
        if not att_path:
            return None
        if self.is_http:
            data = super().read_bytes(att_path)
            return data
        p = self._resolve(att_path)
        return p.read_bytes() if p else None

    def read_text(self, att_path: str, encoding: str = "utf-8") -> str:
        data = self.read_bytes(att_path)
        return data.decode(encoding, errors="replace") if data is not None else ""

    def sample_submission(self) -> dict | None:
        try:
            return super().sample_submission()
        except Exception:
            return None

    def _resolve(self, path: str) -> Path | None:
        p = Path(path)
        if p.is_absolute() and p.exists():
            return p
        for cand in [self.root / path, self.attach_dir / p.name,
                     self.attach_dir / path, self.inbox_dir / p.name]:
            try:
                if cand and cand.exists():
                    return cand
            except OSError:
                continue
        return None


    # ---------- tolerant getters ----------
    @staticmethod
    def get_id(e: dict) -> str:
        for k in ("email_id", "id", "name", "uid"):
            if e.get(k):
                return str(e[k])
        return "unknown_id"

    @staticmethod
    def get_subject(e: dict) -> str:
        for k in ("subject", "title"):
            if e.get(k):
                return str(e[k])
        return ""

    @staticmethod
    def get_body(e: dict) -> str:
        for k in ("body", "text", "content", "message"):
            if e.get(k):
                return str(e[k])
        return ""

    @staticmethod
    def get_attachments(e: dict) -> list[str]:
        for k in ("attachments", "files", "attachment_paths"):
            v = e.get(k)
            if isinstance(v, list):
                return [str(x) for x in v]
            if isinstance(v, dict):
                return [str(x) for x in v.values()]
        return []

    @staticmethod
    def guess_si_bl(e: dict) -> tuple[str, str]:
        atts = Inbox.get_attachments(e)
        si = bl = ""
        for a in atts:
            stem = Path(a).stem.upper()
            tokens = set(re.split(r"[^A-Z]+", stem))
            if not si and "SI" in tokens:
                si = a
            elif not bl and "BL" in tokens:
                bl = a
        if not si and not bl and len(atts) >= 2:
            si, bl = atts[0], atts[1]
        if not bl and len(atts) == 1:
            bl = ""  # explicitly missing
        return si, bl
