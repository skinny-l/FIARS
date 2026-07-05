"""
server.py — FIARS web server (Python standard library).
Run: python server.py
"""
from __future__ import annotations
import json, os, sys, traceback, threading, webbrowser, re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from fiars import db
from fiars.extract import extract_text
from fiars.config import load_config
from fiars.parser import parse_ticket, parse_multi_ticket, search_text
from fiars.parser_table import parse_dispatch_table, merge_dispatch
from fiars.recommend import diagnose
from fiars.report import build_report, default_draft
from fiars.smart_search import smart_search
from fiars.diagnostics import get_diagnostics
from fiars.bulk_parse import parse_bulk

CFG = load_config()
HERE = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(HERE, "templates", "index.html")
UPLOADS = os.path.join(HERE, "uploads")
os.makedirs(UPLOADS, exist_ok=True)


def startup():
    print("=" * 50)
    print("FIARS — Fault Resolution Intelligence Platform")
    print("=" * 50)
    print(f"  Python {sys.version.split()[0]}")
    print(f"  DB: {os.path.abspath(CFG['db_path'])}")

    status = db.init_db(CFG["db_path"])
    print(f"  Database: {status}")

    # Auto-load KB + confirmed solutions
    for script in ("load_kb_power_fault.py", "load_confirmed_solutions.py", "load_server_fault_kb.py", "load_sa5212d6_faults.py", "load_gpu_faults.py", "load_reference_data.py"):
        path = os.path.join(HERE, "scripts", script)
        if os.path.exists(path):
            try:
                import importlib.util
                spec = importlib.util.spec_from_file_location(script, path)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                mod.main()
            except Exception as e:
                print(f"  Warning loading {script}: {e}")

    s = db.stats(CFG["db_path"])
    print(f"  Knowledge: {s['knowledge']}  |  Cases: {s['cases']}  |  KB patterns: {s['kb_patterns']}")

    # Self-test
    print("  Self-test...", end=" ")
    try:
        job = parse_ticket("fault_type:Disk\nFault Description:test", "SELFTEST")
        build_report(default_draft(job))
        db.search_knowledge(CFG["db_path"], "test")
        print("PASS")
    except Exception as e:
        print(f"FAIL: {e}")
    print()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        sys.stderr.write(f"  {fmt % args}\n")

    def _json(self, code, body):
        data = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _html(self, code, data):
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _body(self):
        n = int(self.headers.get("Content-Length", 0))
        if not n: return {}
        try: return json.loads(self.rfile.read(n) or b"{}")
        except: return {}

    def _qs(self):
        return {k: v[0] for k, v in parse_qs(urlparse(self.path).query).items()}

    def do_GET(self):
        try:
            path = urlparse(self.path).path
            qs = self._qs()

            if path in ("/", "/index.html"):
                with open(INDEX, "rb") as f: return self._html(200, f.read())

            if path == "/api/stats":
                return self._json(200, db.stats(CFG["db_path"]))

            if path == "/api/knowledge":
                q = qs.get("q", "")
                mode = qs.get("mode", "smart")
                if q and mode == "smart":
                    results = smart_search(db, CFG["db_path"], q)
                else:
                    results = db.search_knowledge(CFG["db_path"], q)
                return self._json(200, {"results": results})

            if path.startswith("/api/knowledge/"):
                try:
                    kid = int(path.split("/")[-1])
                except (ValueError, IndexError):
                    return self._json(400, {"error": "Invalid ID"})
                con = db.connect(CFG["db_path"])
                row = con.execute("SELECT * FROM knowledge WHERE id=?", (kid,)).fetchone()
                con.close()
                return self._json(200 if row else 404, dict(row) if row else {"error": "not found"})

            if path == "/api/cases":
                page = int(qs.get("page", 1))
                per_page = int(qs.get("per_page", 25))
                search = qs.get("q", "")
                sort_col = qs.get("sort", "id")
                sort_dir = qs.get("dir", "DESC")
                rows, total = db.list_cases(CFG["db_path"], page, per_page, search, sort_col, sort_dir)
                return self._json(200, {"cases": rows, "total": total,
                    "page": page, "per_page": per_page, "pages": max(1, -(-total // per_page))})

            if path == "/api/raw_dumps":
                return self._json(200, {"dumps": db.list_raw_dumps(CFG["db_path"])})

            if path.startswith("/api/raw_dump/"):
                did = int(path.split("/")[-1])
                dump = db.get_raw_dump(CFG["db_path"], did)
                return self._json(200 if dump else 404, dump or {"error": "not found"})

            if path == "/api/config":
                return self._json(200, {"engineer_name": CFG.get("engineer_name", "")})

            if path == "/api/export":
                fn = db.export_all(CFG["db_path"], CFG.get("backup_dir", "backups"))
                return self._json(200, {"ok": True, "file": fn})

            return self._json(404, {"error": "not found"})
        except Exception as e:
            traceback.print_exc()
            return self._json(500, {"error": str(e)})

    def do_POST(self):
        try:
            path = urlparse(self.path).path

            if path == "/api/knowledge":
                b = self._body()
                if not b.get("fault_description") or not b.get("solution"):
                    return self._json(400, {"error": "fault_description and solution are required."})
                kid = db.add_knowledge(CFG["db_path"], b)
                return self._json(200, {"ok": True, "id": kid})

            if path == "/api/cases":
                b = self._body()
                if not b.get("error_fault") or not b.get("solution"):
                    return self._json(400, {"error": "error_fault and solution are required."})
                cid = db.add_case(CFG["db_path"], b)
                return self._json(200, {"ok": True, "id": cid})

            if path == "/api/parse":
                b = self._body()
                raw = b.get("raw", "")
                if not raw.strip():
                    return self._json(400, {"error": "Paste the fault block first."})
                jobs = parse_multi_ticket(raw, b.get("ticket_number", ""))
                dispatch_raw = b.get("dispatch_table", "")
                if dispatch_raw.strip():
                    rows = parse_dispatch_table(dispatch_raw)
                    merge_dispatch(jobs, rows)
                results = []
                for job in jobs:
                    draft = default_draft(job)
                    query = search_text(job)
                    kb_matches = db.kb_pattern_lookup(CFG["db_path"], job.get("raw", raw))
                    kb_results = smart_search(db, CFG["db_path"], query,
                                              parsed_category=job.get("category", ""))
                    diag = get_diagnostics(job.get("category", ""))
                    rec = diagnose(CFG["db_path"], query, raw_text=job.get("raw", raw))
                    parts_to_bring = []
                    if kb_results:
                        p = kb_results[0].get("affected_parts", "")
                        if p:
                            parts_to_bring = [x.strip() for x in p.split(",") if x.strip()]
                    results.append({"job": job, "draft": draft,
                        "report": build_report(draft),
                        "kb_matches": kb_matches, "kb_results": kb_results[:10],
                        "diagnostics": diag, "parts_to_bring": parts_to_bring,
                        "recommend": rec})
                # Single block: return flat (backwards compatible)
                if len(results) == 1:
                    return self._json(200, results[0])
                # Multi-block: return array
                return self._json(200, {"multi": True, "blocks": results,
                    "count": len(results)})

            if path == "/api/report":
                b = self._body()
                return self._json(200, {"report": build_report(b.get("draft", {}))})

            if path == "/api/knowledge/export":
                results = db.search_knowledge(CFG["db_path"], "", limit=9999)
                return self._json(200, {"knowledge": results, "count": len(results)})

            if path == "/api/knowledge/bulk_preview":
                b = self._body()
                entries = parse_bulk(b.get("text", ""), b.get("category", ""),
                                     b.get("format", "auto"))
                return self._json(200, {"entries": entries, "count": len(entries)})

            if path == "/api/knowledge/bulk_import":
                b = self._body()
                entries = parse_bulk(b.get("text", ""), b.get("category", ""),
                                     b.get("format", "auto"))
                added, skipped = 0, 0
                for e in entries:
                    if not e.get("fault_description") or not e.get("solution"):
                        skipped += 1
                        continue
                    if e.get("error_code"):
                        con = db.connect(CFG["db_path"])
                        exists = con.execute("SELECT 1 FROM knowledge WHERE error_code=?",
                            (e["error_code"],)).fetchone()
                        con.close()
                        if exists:
                            skipped += 1
                            continue
                    db.add_knowledge(CFG["db_path"], e)
                    added += 1
                return self._json(200, {"ok": True, "added": added,
                    "skipped": skipped, "total": len(entries)})

            if path == "/api/knowledge/import":
                b = self._body()
                entries = b.get("knowledge", [])
                if not entries:
                    return self._json(400, {"error": "No entries to import."})
                added = 0
                skipped = 0
                for e in entries:
                    if not e.get("fault_description") or not e.get("solution"):
                        skipped += 1
                        continue
                    # Skip if exact error_code already exists
                    if e.get("error_code"):
                        con = db.connect(CFG["db_path"])
                        exists = con.execute("SELECT 1 FROM knowledge WHERE error_code=?",
                            (e["error_code"],)).fetchone()
                        con.close()
                        if exists:
                            skipped += 1
                            continue
                    db.add_knowledge(CFG["db_path"], e)
                    added += 1
                return self._json(200, {"ok": True, "added": added, "skipped": skipped})

            if path == "/api/upload":
                return self._handle_upload()

            return self._json(404, {"error": "not found"})
        except Exception as e:
            traceback.print_exc()
            return self._json(500, {"error": str(e)})

    def _handle_upload(self):
        ctype = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in ctype:
            return self._json(400, {"error": "Use multipart/form-data"})

        # Extract boundary
        boundary = None
        for part in ctype.split(";"):
            part = part.strip()
            if part.startswith("boundary="):
                boundary = part[9:].strip('"')
        if not boundary:
            return self._json(400, {"error": "No boundary in Content-Type"})

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        sep = f"--{boundary}".encode()
        parts = body.split(sep)

        filename = ""
        file_data = b""
        engineer = ""

        for part in parts:
            if b"Content-Disposition" not in part:
                continue
            header_end = part.find(b"\r\n\r\n")
            if header_end < 0:
                continue
            headers_raw = part[:header_end].decode("utf-8", errors="replace")
            payload = part[header_end + 4:]
            if payload.endswith(b"\r\n"):
                payload = payload[:-2]

            # Extract field name and filename
            name_match = re.search(r'name="([^"]*)"', headers_raw)
            fname_match = re.search(r'filename="([^"]*)"', headers_raw)

            if fname_match and name_match and name_match.group(1) == "file":
                filename = fname_match.group(1)
                file_data = payload
            elif name_match and name_match.group(1) == "engineer":
                engineer = payload.decode("utf-8", errors="replace").strip()

        if not filename:
            return self._json(400, {"error": "No file uploaded"})

        ext = os.path.splitext(filename)[1].lower()
        safe_ts = db._now().replace(":", "").replace("-", "")
        dest = os.path.join(UPLOADS, f"{safe_ts}_{filename}")
        with open(dest, "wb") as f:
            f.write(file_data)

        text, status = extract_text(dest)
        did = db.add_raw_dump(CFG["db_path"], filename, ext, dest, text, engineer)
        return self._json(200, {"ok": True, "id": did, "filename": filename,
            "extraction_status": status, "text_length": len(text)})

    def do_PUT(self):
        try:
            path = urlparse(self.path).path
            if path.startswith("/api/knowledge/"):
                id_str = path.rstrip("/").split("/")[-1]
                if not id_str.isdigit():
                    return self._json(400, {"error": "Valid knowledge ID required."})
                kid = int(id_str)
                b = self._body()
                if not b.get("fault_description") or not b.get("solution"):
                    return self._json(400, {"error": "fault_description and solution required."})
                db.update_knowledge(CFG["db_path"], kid, b)
                return self._json(200, {"ok": True, "id": kid})
            return self._json(404, {"error": "not found"})
        except Exception as e:
            traceback.print_exc()
            return self._json(500, {"error": str(e)})

    def do_DELETE(self):
        try:
            path = urlparse(self.path).path
            if path.startswith("/api/knowledge/"):
                id_str = path.rstrip("/").split("/")[-1]
                if not id_str.isdigit():
                    return self._json(400, {"error": "Valid knowledge ID required."})
                kid = int(id_str)
                db.delete_knowledge(CFG["db_path"], kid)
                return self._json(200, {"ok": True})
            return self._json(404, {"error": "not found"})
        except Exception as e:
            traceback.print_exc()
            return self._json(500, {"error": str(e)})


def main():
    startup()
    host, port = CFG.get("host", "127.0.0.1"), int(CFG.get("port", 5000))
    srv = ThreadingHTTPServer((host, port), Handler)
    url = f"http://{host}:{port}"
    print(f"  Listening: {url}\n")
    threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try: srv.serve_forever()
    except KeyboardInterrupt: print("\nstopped.")

if __name__ == "__main__":
    main()
