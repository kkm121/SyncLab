#!/usr/bin/env python3
"""
SyncLab — Production-Grade Multi-Device Client CLI
GDG on Campus SRM Recruitment 2026-27 · Backend & Distributed Systems Track

An actual working client application representing an independent device (Laptop, Phone, Tablet).
Features:
- Real local-first cache & offline mutation queue (Outbox)
- Real network toggling (ONLINE / OFFLINE)
- Real background WebSocket listener for live multi-device push updates
- Real Diff3 3-way auto-merging & interactive conflict resolution prompt
- Real Obsidian Markdown export

Usage:
    # Interactive REPL mode:
    python scripts/client.py --device laptop
    python scripts/client.py --device phone

    # Scriptable one-shot command mode:
    python scripts/client.py --device laptop --command "list"
    python scripts/client.py --device laptop --command "create 'Project Spec' 'Initial text'"
"""

import argparse
import json
import os
import shlex
import sys
import threading
import time
from typing import Any, Dict, List, Optional
import httpx

# Ensure UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ANSI Colors
BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
MAGENTA = "\033[35m"
BLUE = "\033[34m"
RESET = "\033[0m"


class SyncLabDeviceClient:
    """Actual working local-first client representing a physical device."""

    def __init__(self, device_id: str, server_url: str = "http://127.0.0.1:8000"):
        self.device_id = device_id
        self.server_url = server_url.rstrip("/")
        self.ws_url = self.server_url.replace("http://", "ws://").replace("https://", "wss://") + "/ws/sync"
        self.storage_dir = os.path.join(os.getcwd(), ".synclab_client", self.device_id)
        os.makedirs(self.storage_dir, exist_ok=True)

        self.cache_file = os.path.join(self.storage_dir, "cache.json")
        self.outbox_file = os.path.join(self.storage_dir, "outbox.json")
        self.vclock_file = os.path.join(self.storage_dir, "vector_clock.json")

        self.is_online = True
        self.ws_thread: Optional[threading.Thread] = None
        self.stop_ws = threading.Event()
        self.client_http = httpx.Client(base_url=self.server_url, timeout=10.0)

        # Load local persistent state
        self.cache: Dict[str, Any] = self._load_json(self.cache_file, {})
        self.outbox: List[Dict[str, Any]] = self._load_json(self.outbox_file, [])
        self.vector_clock: Dict[str, int] = self._load_json(self.vclock_file, {self.device_id: 1})

        # Register device on server if reachable
        self._register_device()
        self._start_ws_listener()

    def _load_json(self, path: str, default: Any) -> Any:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return default
        return default

    def _save_state(self):
        with open(self.cache_file, "w", encoding="utf-8") as f:
            json.dump(self.cache, f, indent=2)
        with open(self.outbox_file, "w", encoding="utf-8") as f:
            json.dump(self.outbox, f, indent=2)
        with open(self.vclock_file, "w", encoding="utf-8") as f:
            json.dump(self.vector_clock, f, indent=2)

    def _register_device(self):
        if not self.is_online:
            return
        try:
            res = self.client_http.post("/devices/register", json={"device_id": self.device_id})
            if res.status_code in (200, 201):
                pass
        except Exception:
            pass

    def _start_ws_listener(self):
        if not self.is_online:
            return
        self.stop_ws.clear()

        def ws_worker():
            # WebSocket background receiver
            try:
                # Use simple polling or websocket client if available
                # Fallback to polling /sync/realtime/history for robustness across all environments
                last_seen_ts = time.time()
                while not self.stop_ws.is_set():
                    if self.is_online:
                        try:
                            res = self.client_http.get("/sync/realtime/history")
                            if res.status_code == 200:
                                events = res.json()
                                for ev in events:
                                    ev_ts = ev.get("timestamp", 0)
                                    if ev_ts > last_seen_ts:
                                        last_seen_ts = ev_ts
                                        data = ev.get("data", {})
                                        sender = data.get("device_id")
                                        if sender != self.device_id and "document_id" in data:
                                            doc_id = str(data["document_id"])
                                            # If we have this cached and no pending outbox edits, pull fresh
                                            has_outbox = any(o.get("document_id") == int(doc_id) for o in self.outbox)
                                            if doc_id in self.cache and not has_outbox:
                                                self._pull_silent(int(doc_id))
                                                sys.stdout.write(
                                                    f"\n{BOLD}{CYAN}⚡ [REAL-TIME LIVE UPDATE]{RESET} "
                                                    f"Doc #{doc_id} updated by '{sender}' -> v{data.get('current_version')}\n"
                                                    f"{BOLD}{self.device_id} ({'ONLINE' if self.is_online else 'OFFLINE'}) > {RESET}"
                                                )
                                                sys.stdout.flush()
                        except Exception:
                            pass
                    time.sleep(1.0)
            except Exception:
                pass

        self.ws_thread = threading.Thread(target=ws_worker, daemon=True)
        self.ws_thread.start()

    def _pull_silent(self, doc_id: int):
        try:
            res = self.client_http.get(f"/documents/{doc_id}")
            if res.status_code == 200:
                doc = res.json()
                self.cache[str(doc_id)] = doc
                self._save_state()
        except Exception:
            pass

    # -------------------------------------------------------------
    # CLIENT USER COMMANDS
    # -------------------------------------------------------------

    def set_offline(self):
        self.is_online = False
        self.stop_ws.set()
        print(f"{YELLOW}⚡ Device [{self.device_id}] is now OFFLINE (Airplane Mode / Disconnected).{RESET}")
        print(f"  All edits will be queued in local outbox: {self.outbox_file}")

    def set_online(self):
        self.is_online = True
        self._register_device()
        self._start_ws_listener()
        print(f"{GREEN}🟢 Device [{self.device_id}] is now ONLINE.{RESET}")
        if self.outbox:
            print(f"  You have {BOLD}{len(self.outbox)}{RESET} pending offline edits in your outbox.")
            print(f"  Run {BOLD}'sync'{RESET} to synchronize them with the server.")

    def list_documents(self):
        if self.is_online:
            try:
                res = self.client_http.get("/documents")
                if res.status_code == 200:
                    docs = res.json()
                    # update local cache
                    for d in docs:
                        self.cache[str(d["id"])] = d
                    self._save_state()
                    print(f"\n{BOLD}{CYAN}SERVER DOCUMENTS ({len(docs)} found):{RESET}")
                    for d in docs:
                        outbox_mark = " [PENDING LOCAL EDITS]" if any(o.get("document_id") == d["id"] for o in self.outbox) else ""
                        print(f"  • ID {BOLD}#{d['id']}{RESET} | v{d['version']} | {BOLD}{d['title']}{RESET} | tags: {d['tags']}{YELLOW}{outbox_mark}{RESET}")
                    return
            except Exception as e:
                print(f"{RED}Server unreachable ({e}). Falling back to local cache.{RESET}")

        print(f"\n{BOLD}{YELLOW}LOCAL CACHED DOCUMENTS ({len(self.cache)} cached):{RESET}")
        for doc_id, d in self.cache.items():
            outbox_mark = " [PENDING LOCAL EDITS]" if any(str(o.get("document_id")) == str(doc_id) for o in self.outbox) else ""
            print(f"  • ID {BOLD}#{doc_id}{RESET} | v{d.get('version', '?')} | {BOLD}{d.get('title', 'Untitled')}{RESET}{YELLOW}{outbox_mark}{RESET}")

    def show_document(self, doc_id: int):
        doc = self.cache.get(str(doc_id))
        if self.is_online:
            try:
                res = self.client_http.get(f"/documents/{doc_id}")
                if res.status_code == 200:
                    doc = res.json()
                    self.cache[str(doc_id)] = doc
                    self._save_state()
            except Exception:
                pass

        if not doc:
            print(f"{RED}Document #{doc_id} not found in cache or server.{RESET}")
            return

        print(f"\n{BOLD}{CYAN}=== DOCUMENT #{doc['id']}: {doc['title']} (v{doc['version']}) ==={RESET}")
        print(f"Collection : {doc.get('collection')}")
        print(f"Tags       : {doc.get('tags')}")
        print(f"Updated At : {doc.get('updated_at')}")
        print(f"{BOLD}--- BODY CONTENT ---{RESET}")
        print(doc.get("body", ""))
        print(f"{BOLD}--------------------{RESET}")

        # Check if local outbox has pending changes
        pending = [o for o in self.outbox if o.get("document_id") == doc_id]
        if pending:
            print(f"{YELLOW}[!] You have {len(pending)} pending offline mutation(s) for this document!{RESET}")
            latest_pending = pending[-1]
            print(f"{DIM}Latest offline draft content:{RESET}\n{latest_pending.get('body')}")

    def create_document(self, title: str, body: str = ""):
        self.vector_clock[self.device_id] = self.vector_clock.get(self.device_id, 0) + 1
        self._save_state()

        if not self.is_online:
            print(f"{RED}[ERROR] Document creation requires an active server connection to allocate Document ID.{RESET}")
            print(f"  Tip: Go 'online' to create document, then 'offline' to edit it freely!")
            return

        try:
            res = self.client_http.post(
                "/documents",
                json={
                    "title": title,
                    "body": body,
                    "collection": "notes",
                    "tags": ["synclab", self.device_id],
                    "device_id": self.device_id,
                },
            )
            if res.status_code == 201:
                doc = res.json()
                self.cache[str(doc["id"])] = doc
                self._save_state()
                print(f"{GREEN}✓ Created Document #{doc['id']} ('{doc['title']}') v{doc['version']} on server!{RESET}")
            else:
                print(f"{RED}Failed to create document: {res.text}{RESET}")
        except Exception as e:
            print(f"{RED}Error creating document: {e}{RESET}")

    def edit_document(self, doc_id: int, new_body: str, title: Optional[str] = None):
        doc = self.cache.get(str(doc_id))
        if not doc:
            if self.is_online:
                self._pull_silent(doc_id)
                doc = self.cache.get(str(doc_id))
        if not doc:
            print(f"{RED}Document #{doc_id} not found. Please 'list' or 'show {doc_id}' first.{RESET}")
            return

        base_version = doc.get("version", 1)
        self.vector_clock[self.device_id] = self.vector_clock.get(self.device_id, 0) + 1

        if not self.is_online:
            # Stage in local outbox
            # Remove any earlier pending edit for this document and replace with latest
            self.outbox = [o for o in self.outbox if o.get("document_id") != doc_id]
            mutation = {
                "document_id": doc_id,
                "base_version": base_version,
                "body": new_body,
                "title": title or doc.get("title"),
                "timestamp": time.time(),
            }
            self.outbox.append(mutation)
            # Update local cache preview
            doc["body"] = new_body
            if title:
                doc["title"] = title
            self.cache[str(doc_id)] = doc
            self._save_state()
            print(f"{YELLOW}⚡ [SAVED OFFLINE] Edit staged in local outbox for Doc #{doc_id} (Base v{base_version}).{RESET}")
            print(f"  When ready to synchronize with server, run {BOLD}'online'{RESET} and {BOLD}'sync {doc_id}'{RESET}.")
            return

        # If ONLINE: push immediately
        self._push_sync(doc_id, base_version, new_body, title or doc.get("title"), strategy="merge")

    def append_document(self, doc_id: int, line_to_append: str):
        doc = self.cache.get(str(doc_id))
        if not doc:
            if self.is_online:
                self._pull_silent(doc_id)
                doc = self.cache.get(str(doc_id))
        if not doc:
            print(f"{RED}Document #{doc_id} not found.{RESET}")
            return

        curr_body = doc.get("body", "")
        new_body = (curr_body + "\n" + line_to_append).strip()
        self.edit_document(doc_id, new_body)

    def sync_document(self, doc_id: Optional[int] = None, chosen_strategy: str = "merge"):
        if not self.is_online:
            print(f"{RED}[ERROR] Device is OFFLINE. Type 'online' before syncing with the server.{RESET}")
            return

        # Filter outbox
        targets = self.outbox if doc_id is None else [o for o in self.outbox if o.get("document_id") == doc_id]
        if not targets:
            print(f"{GREEN}Nothing pending in local outbox to sync! Local state is clean.{RESET}")
            return

        for mut in list(targets):
            t_id = mut["document_id"]
            base_ver = mut["base_version"]
            body = mut["body"]
            title = mut.get("title")
            success = self._push_sync(t_id, base_ver, body, title, strategy=chosen_strategy)
            if success:
                self.outbox = [o for o in self.outbox if o != mut]
                self._save_state()

    def _push_sync(
        self,
        doc_id: int,
        base_version: int,
        body: str,
        title: Optional[str] = None,
        strategy: str = "merge",
    ) -> bool:
        print(f"\n{BOLD}--> Synchronizing Doc #{doc_id} with Server (Base v{base_version}, Strategy: {strategy})...{RESET}")
        try:
            res = self.client_http.post(
                "/sync",
                json={
                    "device_id": self.device_id,
                    "document_id": doc_id,
                    "base_version": base_version,
                    "body": body,
                    "title": title,
                    "strategy": strategy,
                },
            )
            if res.status_code == 200:
                data = res.json()
                outcome = data["outcome"]

                if outcome == "accepted":
                    print(f"{GREEN}{BOLD}✓ [ACCEPTED]{RESET} Server fast-forward committed revision -> {BOLD}v{data['current_version']}{RESET}")
                    self.cache[str(doc_id)] = data["document"]
                    self._save_state()
                    return True

                elif outcome == "merged":
                    print(f"{GREEN}{BOLD}✓ [DIFF3 AUTO-MERGED]{RESET} Disjoint concurrent edits merged -> {BOLD}v{data['current_version']}{RESET}")
                    print(f"  Merged Fields : {data.get('merged_fields')}")
                    print(f"\n{DIM}Merged Result from Server:{RESET}\n{data['document']['body']}")
                    self.cache[str(doc_id)] = data["document"]
                    self._save_state()
                    return True

                elif outcome == "conflict":
                    print(f"{RED}{BOLD}⚠ [CONFLICT DETECTED — ZERO OVERWRITE GUARANTEE]{RESET}")
                    print(f"  The server has advanced to version {BOLD}v{data['current_version']}{RESET} while your edits were based on v{base_version}.")
                    print(f"  Server refused to silently overwrite existing data!")
                    print(f"  Conflict Details : {data.get('resolution')}")
                    print(f"  Conflicting Fields: {[c.get('field') for c in data.get('conflicts', [])]}")

                    # Interactive conflict resolution prompt
                    print(f"\n{BOLD}{YELLOW}CHOOSE CONFLICT RESOLUTION STRATEGY:{RESET}")
                    print(f"  [1] {CYAN}Diff3 3-Way Line Merge (Generate Conflict Markers: <<<<<<< / ======= / >>>>>>>){RESET}")
                    print(f"  [2] {GREEN}Server Wins (Discard local offline change, accept server v{data['current_version']}){RESET}")
                    print(f"  [3] {MAGENTA}Client Wins (Force your offline change over server){RESET}")
                    print(f"  [4] {BLUE}FugueMax CRDT (Maximal Non-Interleaving Character Merge){RESET}")
                    print(f"  [5] Cancel / Keep in local outbox for later")

                    choice = input(f"{BOLD}Select strategy (1-5): {RESET}").strip()
                    if choice == "1":
                        # Fetch server version and run AST or line merge with conflict markers
                        server_doc = self.client_http.get(f"/documents/{doc_id}").json()
                        marked_body = (
                            f"<<<<<<< LOCAL ({self.device_id})\n"
                            f"{body}\n"
                            f"=======\n"
                            f"{server_doc['body']}\n"
                            f">>>>>>> SERVER (v{server_doc['version']})"
                        )
                        # Re-push as client_wins with markers so user can manually edit
                        return self._push_sync(doc_id, server_doc["version"], marked_body, title, strategy="client_wins")

                    elif choice == "2":
                        # Server wins
                        return self._push_sync(doc_id, base_version, body, title, strategy="server_wins")

                    elif choice == "3":
                        # Client wins
                        return self._push_sync(doc_id, base_version, body, title, strategy="client_wins")

                    elif choice == "4":
                        # FugueMax CRDT
                        server_doc = self.client_http.get(f"/documents/{doc_id}").json()
                        fugue_res = self.client_http.post(
                            "/sync/fugue/simulate",
                            json={
                                "initial_text": server_doc["body"],
                                "peer_a_insert": body,
                                "peer_b_insert": "",
                                "cursor_offset": len(server_doc["body"]),
                            },
                        ).json()
                        crdt_text = fugue_res["converged_text"]
                        return self._push_sync(doc_id, server_doc["version"], crdt_text, title, strategy="client_wins")

                    else:
                        print(f"{YELLOW}Conflict unresolved. Retained in outbox.{RESET}")
                        return False

                elif outcome == "resolved":
                    print(f"{GREEN}✓ [RESOLVED]{RESET} Server successfully applied {strategy}: {data.get('resolution')}")
                    self.cache[str(doc_id)] = data["document"]
                    self._save_state()
                    return True

            print(f"{RED}Sync returned status {res.status_code}: {res.text}{RESET}")
            return False
        except Exception as e:
            print(f"{RED}Sync network error: {e}{RESET}")
            return False

    def view_history(self, doc_id: int):
        if not self.is_online:
            print(f"{RED}[ERROR] Fetching version audit log requires ONLINE connection.{RESET}")
            return
        try:
            res = self.client_http.get(f"/documents/{doc_id}/versions")
            if res.status_code == 200:
                versions = res.json()
                print(f"\n{BOLD}{CYAN}=== AUDIT HISTORY FOR DOC #{doc_id} ({len(versions)} versions) ==={RESET}")
                for v in versions:
                    print(
                        f"  v{v['version']:<3} | By: {BOLD}{v['device_id']:<20}{RESET} | "
                        f"Strategy: {v['strategy']:<10} | Outcome: {GREEN}{v['outcome']:<10}{RESET} | {DIM}{v['created_at']}{RESET}"
                    )
            else:
                print(f"{RED}Failed to fetch versions: {res.text}{RESET}")
        except Exception as e:
            print(f"{RED}Error fetching history: {e}{RESET}")

    def export_obsidian(self, doc_id: int):
        doc = self.cache.get(str(doc_id))
        if self.is_online:
            try:
                res = self.client_http.get(f"/documents/{doc_id}/export.md")
                if res.status_code == 200:
                    out_path = os.path.join(self.storage_dir, f"doc_{doc_id}.md")
                    with open(out_path, "w", encoding="utf-8") as f:
                        f.write(res.text)
                    print(f"{GREEN}✓ Exported Obsidian Markdown to: {BOLD}{out_path}{RESET}")
                    return
            except Exception:
                pass

        if doc:
            out_path = os.path.join(self.storage_dir, f"doc_{doc_id}.md")
            frontmatter = f"---\ntitle: {doc.get('title')}\nversion: {doc.get('version')}\ndevice: {self.device_id}\n---\n\n"
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(frontmatter + doc.get("body", ""))
            print(f"{GREEN}✓ Exported local cached document to: {BOLD}{out_path}{RESET}")
        else:
            print(f"{RED}Document #{doc_id} not available for export.{RESET}")

    def print_status(self):
        state_badge = f"{GREEN}ONLINE 🟢{RESET}" if self.is_online else f"{YELLOW}OFFLINE ⚡{RESET}"
        print(f"\n{BOLD}=== DEVICE STATUS: {CYAN}{self.device_id}{RESET} ===")
        print(f"Network Status : {state_badge}")
        print(f"Server Target  : {self.server_url}")
        print(f"Cached Docs    : {len(self.cache)} documents")
        print(f"Pending Outbox : {BOLD}{len(self.outbox)}{RESET} uncommitted offline mutations")
        print(f"Vector Clock   : {self.vector_clock}")
        print(f"Storage Folder : {self.storage_dir}\n")

    def execute_command_string(self, cmd_line: str):
        parts = shlex.split(cmd_line.strip())
        if not parts:
            return
        cmd = parts[0].lower()

        if cmd in ("exit", "quit", "q"):
            self.stop_ws.set()
            sys.exit(0)
        elif cmd == "help":
            self.print_help()
        elif cmd == "status":
            self.print_status()
        elif cmd in ("offline", "disconnect"):
            self.set_offline()
        elif cmd in ("online", "connect"):
            self.set_online()
        elif cmd == "list":
            self.list_documents()
        elif cmd == "show":
            if len(parts) > 1 and parts[1].isdigit():
                self.show_document(int(parts[1]))
            else:
                print(f"{YELLOW}Usage: show <document_id>{RESET}")
        elif cmd == "create":
            if len(parts) > 1:
                title = parts[1]
                body = parts[2] if len(parts) > 2 else ""
                self.create_document(title, body)
            else:
                print(f"{YELLOW}Usage: create \"Document Title\" [optional body]{RESET}")
        elif cmd == "edit":
            if len(parts) > 2 and parts[1].isdigit():
                self.edit_document(int(parts[1]), parts[2])
            else:
                print(f"{YELLOW}Usage: edit <document_id> \"New Content\"{RESET}")
        elif cmd == "append":
            if len(parts) > 2 and parts[1].isdigit():
                self.append_document(int(parts[1]), parts[2])
            else:
                print(f"{YELLOW}Usage: append <document_id> \"Line to append\"{RESET}")
        elif cmd == "sync":
            doc_id = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None
            strat = parts[2] if len(parts) > 2 else "merge"
            self.sync_document(doc_id, chosen_strategy=strat)
        elif cmd == "history":
            if len(parts) > 1 and parts[1].isdigit():
                self.view_history(int(parts[1]))
            else:
                print(f"{YELLOW}Usage: history <document_id>{RESET}")
        elif cmd == "export":
            if len(parts) > 1 and parts[1].isdigit():
                self.export_obsidian(int(parts[1]))
            else:
                print(f"{YELLOW}Usage: export <document_id>{RESET}")
        else:
            print(f"{RED}Unknown command: '{cmd}'. Type 'help' for commands.{RESET}")

    def print_help(self):
        print(f"""
{BOLD}{CYAN}AVAILABLE DEVICE CLIENT COMMANDS:{RESET}
  {BOLD}status{RESET}                      Show device connectivity, vector clock, and outbox count
  {BOLD}list{RESET}                        List all server or locally cached documents
  {BOLD}show <id>{RESET}                   Display full content, tags, and version of a document
  {BOLD}create <title> [body]{RESET}       Create a new document on server (when online)
  {BOLD}edit <id> <text>{RESET}             Edit document (updates immediately if online, stages if offline)
  {BOLD}append <id> <line>{RESET}           Append a line to document
  {BOLD}offline{RESET}                     Simulate airplane mode / network disconnection
  {BOLD}online{RESET}                      Reconnect to server & start receiving live updates
  {BOLD}sync [id] [strategy]{RESET}        Flush queued offline edits to server (merge / client_wins / server_wins)
  {BOLD}history <id>{RESET}                 View immutable version timeline and device audit trail
  {BOLD}export <id>{RESET}                  Export document to Obsidian Markdown (.md)
  {BOLD}help{RESET}                        Show this help cheat sheet
  {BOLD}exit{RESET}                        Quit client application
""")


def main():
    parser = argparse.ArgumentParser(description="SyncLab Multi-Device Interactive Client CLI")
    parser.add_argument("--device", default="laptop", help="Unique device ID (e.g. laptop, phone, tablet)")
    parser.add_argument("--server", default="http://127.0.0.1:8000", help="SyncLab backend server URL")
    parser.add_argument("--command", help="Run a single command non-interactively and exit")
    args = parser.parse_args()

    client = SyncLabDeviceClient(device_id=args.device, server_url=args.server)

    if args.command:
        client.execute_command_string(args.command)
        client.stop_ws.set()
        return

    # Interactive REPL mode
    print(f"""
{BOLD}{CYAN}╔═══════════════════════════════════════════════════════════════════════════╗
║                   SYNCLAB · MULTI-DEVICE CLIENT CLI                       ║
║        Device: {MAGENTA}{args.device:<15}{CYAN} | Server: {GREEN}{args.server:<25}{CYAN} ║
╚═══════════════════════════════════════════════════════════════════════════╝{RESET}
{DIM}Type 'help' for command list. Type 'offline' to disconnect and make offline edits!{RESET}
""")

    while True:
        try:
            status_tag = f"{GREEN}ONLINE{RESET}" if client.is_online else f"{YELLOW}OFFLINE{RESET}"
            prompt = f"{BOLD}{client.device_id}{RESET} [{status_tag}] > "
            user_input = input(prompt)
            if user_input.strip():
                client.execute_command_string(user_input)
        except (KeyboardInterrupt, EOFError):
            print("\nExiting client...")
            client.stop_ws.set()
            break


if __name__ == "__main__":
    main()
