"""Where rendered files and job rows go. Dry-run uses the local stand-ins."""

from __future__ import annotations

import json
import os
from pathlib import Path

HEADERS = [
    "job_id",
    "content_hash",
    "book",
    "chapter",
    "status",
    "attempts",
    "error",
    "output_links",
    "updated_at",
]

MIME = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "html": "text/html",
    "epub": "application/epub+zip",
    "flipbook": "text/html",
}

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/documents.readonly",
]


class LocalLibrary:
    """Writes ``Book Xn/outputs/<format>/`` under a directory and returns dry-run links."""

    def __init__(self, root: Path):
        self.root = root

    def upload(self, book_code: str, format_name: str, filename: str, data: bytes) -> str:
        folder = self.root / book_code / "outputs" / format_name
        folder.mkdir(parents=True, exist_ok=True)
        (folder / filename).write_bytes(data)
        return f"dry-run://{book_code}/outputs/{format_name}/{filename}"


class LocalSheet:
    def __init__(self, path: Path):
        self.path = path
        self.rows: list[dict] = []
        if path.is_file():
            self.rows = json.loads(path.read_text(encoding="utf-8"))

    def find(self, content_hash: str) -> dict | None:
        for row in self.rows:
            if row.get("content_hash") == content_hash:
                return dict(row)
        return None

    def save(self, row: dict) -> None:
        stored = dict(row)
        for index, existing in enumerate(self.rows):
            if existing.get("content_hash") == stored["content_hash"]:
                self.rows[index] = stored
                break
        else:
            self.rows.append(stored)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.rows, indent=2), encoding="utf-8")


def load_service_account():
    """Build credentials from ``GOOGLE_SERVICE_ACCOUNT_JSON`` or ``GOOGLE_APPLICATION_CREDENTIALS``."""
    from google.oauth2 import service_account

    raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    if raw:
        info = json.loads(raw)
        return service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    if not path:
        raise RuntimeError("Set GOOGLE_SERVICE_ACCOUNT_JSON or GOOGLE_APPLICATION_CREDENTIALS")
    return service_account.Credentials.from_service_account_file(path, scopes=SCOPES)


def _quote(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


class DriveLibrary:
    def __init__(self, credentials, root_folder_id: str = "", root_name: str = ""):
        from googleapiclient.discovery import build

        self.drive = build("drive", "v3", credentials=credentials, cache_discovery=False)
        self.root_id = root_folder_id or self._ensure(None, root_name or "Physics Textbook Series")
        self._cache: dict[tuple[str, str], str] = {}

    def upload(self, book_code: str, format_name: str, filename: str, data: bytes) -> str:
        from googleapiclient.http import MediaInMemoryUpload

        book_id = self._ensure(self.root_id, book_code)
        outputs_id = self._ensure(book_id, "outputs")
        format_id = self._ensure(outputs_id, format_name)
        media = MediaInMemoryUpload(data, mimetype=MIME.get(format_name, "application/octet-stream"), resumable=False)
        created = (
            self.drive.files()
            .create(
                body={"name": filename, "parents": [format_id]},
                media_body=media,
                fields="id, webViewLink",
                supportsAllDrives=True,
            )
            .execute()
        )
        return created.get("webViewLink") or f"https://drive.google.com/file/d/{created['id']}/view"

    def _ensure(self, parent: str | None, name: str) -> str:
        key = (parent or "", name)
        if key in self._cache:
            return self._cache[key]
        clauses = [
            f"name = '{_quote(name)}'",
            "mimeType = 'application/vnd.google-apps.folder'",
            "trashed = false",
        ]
        if parent:
            clauses.append(f"'{parent}' in parents")
        found = (
            self.drive.files()
            .list(
                q=" and ".join(clauses),
                fields="files(id, name)",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
            )
            .execute()
        )
        files = found.get("files") or []
        if files:
            folder_id = files[0]["id"]
        else:
            body = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
            if parent:
                body["parents"] = [parent]
            created = (
                self.drive.files()
                .create(body=body, fields="id", supportsAllDrives=True)
                .execute()
            )
            folder_id = created["id"]
        self._cache[key] = folder_id
        return folder_id


class SheetTracker:
    def __init__(self, credentials, spreadsheet_id: str):
        from googleapiclient.discovery import build

        self.sheets = build("sheets", "v4", credentials=credentials, cache_discovery=False)
        self.spreadsheet_id = spreadsheet_id
        meta = self.sheets.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        self.title = meta["sheets"][0]["properties"]["title"]
        self._ensure_header()

    def _range(self, cells: str) -> str:
        escaped = self.title.replace("'", "''")
        return f"'{escaped}'!{cells}"

    def _ensure_header(self) -> None:
        current = (
            self.sheets.spreadsheets()
            .values()
            .get(spreadsheetId=self.spreadsheet_id, range=self._range("A1:I1"))
            .execute()
        )
        if current.get("values"):
            return
        self.sheets.spreadsheets().values().update(
            spreadsheetId=self.spreadsheet_id,
            range=self._range("A1:I1"),
            valueInputOption="RAW",
            body={"values": [HEADERS]},
        ).execute()

    def _rows(self) -> list[list[str]]:
        result = (
            self.sheets.spreadsheets()
            .values()
            .get(spreadsheetId=self.spreadsheet_id, range=self._range("A2:I"))
            .execute()
        )
        return result.get("values") or []

    @staticmethod
    def _as_dict(values: list) -> dict:
        padded = list(values) + [""] * (len(HEADERS) - len(values))
        raw_links = padded[7]
        try:
            links = json.loads(raw_links) if raw_links else {}
        except json.JSONDecodeError:
            links = {}
        try:
            attempts = int(padded[5] or 0)
        except ValueError:
            attempts = 0
        return {
            "job_id": padded[0],
            "content_hash": padded[1],
            "book": padded[2],
            "chapter": padded[3],
            "status": padded[4],
            "attempts": attempts,
            "error": padded[6],
            "output_links": links,
            "updated_at": padded[8],
        }

    def find(self, content_hash: str) -> dict | None:
        for values in self._rows():
            row = self._as_dict(values)
            if row["content_hash"] == content_hash:
                return row
        return None

    def save(self, row: dict) -> None:
        encoded = [
            row["job_id"],
            row["content_hash"],
            row["book"],
            str(row["chapter"]),
            row["status"],
            str(row["attempts"]),
            row.get("error") or "",
            json.dumps(row.get("output_links") or {}, ensure_ascii=False),
            row.get("updated_at") or "",
        ]
        rows = self._rows()
        for index, values in enumerate(rows, start=2):
            if len(values) > 1 and values[1] == row["content_hash"]:
                self.sheets.spreadsheets().values().update(
                    spreadsheetId=self.spreadsheet_id,
                    range=self._range(f"A{index}:I{index}"),
                    valueInputOption="RAW",
                    body={"values": [encoded]},
                ).execute()
                return
        self.sheets.spreadsheets().values().append(
            spreadsheetId=self.spreadsheet_id,
            range=self._range("A1:I1"),
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body={"values": [encoded]},
        ).execute()


def fetch_google_doc(credentials, document_id: str) -> str:
    from googleapiclient.discovery import build

    from physics_studio.generator.docs_text import document_plain_text

    docs = build("docs", "v1", credentials=credentials, cache_discovery=False)
    document = docs.documents().get(documentId=document_id).execute()
    return document_plain_text(document)
