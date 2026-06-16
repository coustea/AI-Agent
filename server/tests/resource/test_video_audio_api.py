import pytest
from fastapi.testclient import TestClient
from app.app import create_app
from app.config import WORKPLACE_DIR

client = TestClient(create_app())

def test_serve_audio_file():
    audio_dir = WORKPLACE_DIR / "video_audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    test_file = audio_dir / "test_endpoint.mp3"
    
    with open(test_file, "wb") as f:
        f.write(b"fake audio data")
        
    try:
        response = client.get("/api/v1/ai/video/audio/test_endpoint.mp3")
        assert response.status_code == 200
        assert response.headers["content-type"] == "audio/mpeg"
        assert response.content == b"fake audio data"
        
        # Test directory traversal protection
        response_traversal = client.get("/api/v1/ai/video/audio/%2E%2E/config.yaml")
        assert response_traversal.status_code == 400
        
        # Test not found
        response_not_found = client.get("/api/v1/ai/video/audio/non_existent.mp3")
        assert response_not_found.status_code == 404
    finally:
        if test_file.exists():
            test_file.unlink()
