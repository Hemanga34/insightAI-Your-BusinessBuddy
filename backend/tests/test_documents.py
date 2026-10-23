from io import BytesIO

from conftest import register
from openpyxl import Workbook


def test_private_upload_and_cross_business_isolation(client):
    first = register(client)
    response = client.post(
        "/api/documents",
        headers=first,
        files={
            "file": ("statement.csv", b"date,amount\n2026-10-01,1200.25\n", "text/csv"),
        },
    )
    assert response.status_code == 201, response.text
    document = response.json()
    assert document["status"] == "extracted"
    detail = client.get(f"/api/documents/{document['id']}", headers=first).json()
    assert detail["extraction"]["verified"] is False
    assert detail["extraction"]["blocks"][1]["location"] == {"row": 2}
    second = register(client, "another@example.in")
    assert client.get("/api/documents", headers=second).json() == []
    assert client.get(f"/api/documents/{document['id']}", headers=second).status_code == 404
    assert client.post(f"/api/documents/{document['id']}/retry", headers=second).status_code == 404
    assert client.get("/api/documents").status_code == 401


def test_duplicate_file_rejected_without_cross_business_leak(client):
    first = register(client)
    payload = {"file": ("invoice.csv", b"amount\n50\n", "text/csv")}
    assert client.post("/api/documents", headers=first, files=payload).status_code == 201
    assert client.post("/api/documents", headers=first, files=payload).status_code == 409
    second = register(client, "second@example.in")
    assert client.post("/api/documents", headers=second, files=payload).status_code == 201


def test_renamed_binary_and_empty_file_rejected(client):
    headers = register(client)
    assert (
        client.post(
            "/api/documents", headers=headers, files={"file": ("fake.pdf", b"not a PDF")}
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/documents", headers=headers, files={"file": ("empty.csv", b"")}
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/documents", headers=headers, files={"file": ("program.exe", b"binary")}
        ).status_code
        == 415
    )


def test_spreadsheet_preserves_source_and_does_not_execute_formulas(client):
    headers = register(client)
    workbook = Workbook()
    workbook.active.title = "Sales"
    workbook.active.append(["Amount", "Formula"])
    workbook.active.append([100, "=1+1"])
    buffer = BytesIO()
    workbook.save(buffer)
    response = client.post(
        "/api/documents", headers=headers, files={"file": ("sales.xlsx", buffer.getvalue())}
    )
    assert response.status_code == 201
    detail = client.get(f"/api/documents/{response.json()['id']}", headers=headers).json()
    assert detail["extraction"]["blocks"][1]["location"] == {"sheet": "Sales", "row": 2}
    assert "=1+1" in detail["extraction"]["blocks"][1]["text"]


def test_images_report_ocr_requirement(client):
    headers = register(client)
    from PIL import Image

    image = BytesIO()
    Image.new("RGB", (1, 1)).save(image, format="PNG")
    response = client.post(
        "/api/documents", headers=headers, files={"file": ("scan.png", image.getvalue())}
    )
    assert response.status_code == 201
    assert response.json()["status"] == "needs_attention"
    assert "OCR" in response.json()["error"]


def test_queue_failure_can_be_retried(client, monkeypatch):
    headers = register(client)
    from app import main

    original_dispatch = main.dispatch_document

    def unavailable(_):
        raise ConnectionError("Redis is offline")

    monkeypatch.setattr(main, "dispatch_document", unavailable)
    response = client.post(
        "/api/documents", headers=headers, files={"file": ("data.csv", b"amount\n30")}
    )
    assert response.json()["status"] == "failed"
    monkeypatch.setattr(main, "dispatch_document", original_dispatch)
    retry = client.post(f"/api/documents/{response.json()['id']}/retry", headers=headers)
    assert retry.status_code == 200
    assert retry.json()["status"] == "extracted"
