import os

import pytest
from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


@pytest.fixture()
def temp_file(request):
    filename = request.param["filename"]
    size_bytes = request.param["size_bytes"]

    def cleanup():
        if os.path.exists(filename):
            os.remove(filename)

    try:
        if size_bytes:
            with open(filename, "wb") as f:
                f.write(os.urandom(size_bytes))
            actual_size = os.path.getsize(filename)
            assert (
                actual_size == size_bytes
            ), f"Expected size {size_bytes}, got {actual_size}"
        yield filename
    finally:
        cleanup()


def test_validate_upload_file_no_file():
    """GIVEN a splats api consumer
    WHEN the POST /splats request is invoked
    AND no file is passed
    THEN a 422 status code is returned with a helpful error message."""
    response = client.post("/splats")
    assert response.status_code == 422
    assert response.json() == {
        "detail": [
            {
                "type": "missing",
                "loc": ["body", "file"],
                "msg": "Field required",
                "input": None,
            }
        ]
    }


@pytest.mark.parametrize(
    "temp_file",
    [{"filename": "test_video.jpg", "size_bytes": 51 * 1024 * 1024}],  # 51 MB
    indirect=True,
)
def test_validate_upload_file_given_violations(
    temp_file: str,
):
    """GIVEN a splats api consumer
    WHEN the POST /splats request is invoked
    AND a file is passed with an invalid content type
    AND an invalid file extension
    AND the file's actual content type does not match
    AND the file is too big
    THEN a 400 status code is returned with a helpful error message for each of these violations.
    """
    with open(temp_file, "rb") as f:
        response = client.post(
            "/splats",
            data={"file": temp_file},
            files={"file": (temp_file, f, "application/octet-stream")},
        )
    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid video file"}
    assert (
        response.headers.get("x-error-detail")
        == "{'content_type': 'Expected video file, got application/octet-stream', "
        "'content_type_mismatch': 'Header content type mismatch, expected application/octet-stream, got image/jpeg', "
        "'extension': 'Unsupported video format: .jpg', "
        "'size': 'File too large. Maximum size is 52428800 bytes. Got 53477376 bytes'}"
    )
