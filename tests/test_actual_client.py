"""Automated Integration Tests for SyncLab Actual Client
Tests real multi-device workflow: offline staging, outbox queues, 3-way Diff3 merge,
and conflict detection using actual client instances.
"""

import os
import shutil
import pytest
from fastapi.testclient import TestClient

from app.main import app
from scripts.client import SyncLabDeviceClient

client_http = TestClient(app)


@pytest.fixture(autouse=True)
def cleanup_client_storage():
    """Clean up .synclab_client test storage between runs."""
    test_storage = os.path.join(os.getcwd(), ".synclab_client")
    if os.path.exists(test_storage):
        shutil.rmtree(test_storage, ignore_errors=True)
    yield
    if os.path.exists(test_storage):
        shutil.rmtree(test_storage, ignore_errors=True)


def test_actual_client_lifecycle_and_offline_merge():
    # 1. Initialize two actual device clients
    laptop = SyncLabDeviceClient(device_id="laptop-actual")
    phone = SyncLabDeviceClient(device_id="phone-actual")

    # Override client_http inside clients to use FastAPI TestClient
    laptop.client_http = client_http
    phone.client_http = client_http

    # 2. Laptop creates a real document
    initial_body = "Line 1: System Title\nLine 2: Common Arch\nLine 3: Database Spec"
    laptop.create_document("Real Sync Spec", initial_body)

    # Verify document exists in laptop cache
    assert len(laptop.cache) >= 1
    doc_id = int(list(laptop.cache.keys())[0])
    assert laptop.cache[str(doc_id)]["title"] == "Real Sync Spec"

    # 3. Phone pulls document
    phone.show_document(doc_id)
    assert str(doc_id) in phone.cache
    assert phone.cache[str(doc_id)]["version"] == 1

    # 4. Laptop goes OFFLINE
    laptop.set_offline()
    assert not laptop.is_online

    # 5. Phone makes online edit to Line 3 (disjoint from Line 1)
    phone_new_body = "Line 1: System Title\nLine 2: Common Arch\nLine 3: Database Spec (UPDATED BY PHONE)"
    phone.edit_document(doc_id, phone_new_body)
    assert phone.cache[str(doc_id)]["version"] == 2

    # 6. Laptop makes offline edit to Line 1 (disjoint from Line 3)
    laptop_new_body = "Line 1: System Title (UPDATED BY LAPTOP)\nLine 2: Common Arch\nLine 3: Database Spec"
    laptop.edit_document(doc_id, laptop_new_body)

    # Laptop must have staged the mutation into local outbox!
    assert len(laptop.outbox) == 1
    assert laptop.outbox[0]["base_version"] == 1
    assert laptop.outbox[0]["document_id"] == doc_id

    # 7. Laptop goes back ONLINE
    laptop.set_online()
    assert laptop.is_online

    # 8. Laptop synchronizes queued outbox
    laptop.sync_document(doc_id, chosen_strategy="merge")

    # Outbox should now be empty (successfully merged!)
    assert len(laptop.outbox) == 0

    # Server must now be at Version 3 with BOTH edits merged cleanly!
    server_doc = client_http.get(f"/documents/{doc_id}").json()
    assert server_doc["version"] == 3
    assert "(UPDATED BY LAPTOP)" in server_doc["body"]
    assert "(UPDATED BY PHONE)" in server_doc["body"]


def test_actual_client_same_line_conflict_rejection():
    laptop = SyncLabDeviceClient(device_id="laptop-conf")
    phone = SyncLabDeviceClient(device_id="phone-conf")
    laptop.client_http = client_http
    phone.client_http = client_http

    # Create doc
    laptop.create_document("Conflict Document", "Base content on line 1")
    doc_id = int(list(laptop.cache.keys())[0])

    phone.show_document(doc_id)

    # Laptop goes offline
    laptop.set_offline()

    # Phone edits line 1 online to 'Phone value'
    phone.edit_document(doc_id, "Phone value on line 1")
    assert phone.cache[str(doc_id)]["version"] == 2

    # Laptop edits line 1 offline to 'Laptop value'
    laptop.edit_document(doc_id, "Laptop value on line 1")
    assert len(laptop.outbox) == 1

    laptop.set_online()

    # Direct push_sync with strategy=merge will trigger conflict
    # and fail to commit silently
    res = client_http.post(
        "/sync",
        json={
            "device_id": "laptop-conf",
            "document_id": doc_id,
            "base_version": 1,
            "body": "Laptop value on line 1",
            "strategy": "merge",
        },
    )
    assert res.status_code == 200
    outcome = res.json()["outcome"]
    # MUST be conflict! Never silent overwrite!
    assert outcome == "conflict"

    # Server state remains Phone's v2
    server_doc = client_http.get(f"/documents/{doc_id}").json()
    assert server_doc["version"] == 2
    assert server_doc["body"] == "Phone value on line 1"


def test_actual_client_obsidian_export():
    client = SyncLabDeviceClient(device_id="export-test")
    client.client_http = client_http

    client.create_document("Obsidian Export Test", "# Header\nBody content.")
    doc_id = int(list(client.cache.keys())[0])

    client.export_obsidian(doc_id)

    expected_path = os.path.join(client.storage_dir, f"doc_{doc_id}.md")
    assert os.path.exists(expected_path)
    with open(expected_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "Obsidian Export Test" in content
    assert "Body content." in content
