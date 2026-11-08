"""
Adversarial Verification & Empirical Stress-Test Suite for Milestone 1:
Docker Packaging, Cloud 24/7 Compatibility, and Endpoints.

Executed by: Challenger 1
"""

import os
import sys
import subprocess
from pathlib import Path
from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from api import app

def test_posix_shell_parameter_substitution():
    """Empirically test POSIX sh parameter substitution behavior for ${PORT:-7860}."""
    git_sh = r"C:\Program Files\Git\bin\sh.exe"
    assert os.path.exists(git_sh), f"Git sh not found at {git_sh}"

    cases = [
        {"env": {}, "expected": "7860", "desc": "PORT unset"},
        {"env": {"PORT": ""}, "expected": "7860", "desc": "PORT empty string"},
        {"env": {"PORT": "8080"}, "expected": "8080", "desc": "PORT=8080 (Docker default/custom)"},
        {"env": {"PORT": "10000"}, "expected": "10000", "desc": "PORT=10000 (Render dynamic port)"},
        {"env": {"PORT": "7860"}, "expected": "7860", "desc": "PORT=7860 (Hugging Face Spaces)"},
    ]

    print("\n=== [1] POSIX Shell Parameter Substitution Stress Tests ===")
    for c in cases:
        env = os.environ.copy()
        if "PORT" in env:
            del env["PORT"]
        env.update(c["env"])
        
        # Test exact CMD expression: sh -c 'echo ${PORT:-7860}'
        res = subprocess.run(
            [git_sh, "-c", "echo ${PORT:-7860}"],
            capture_output=True,
            text=True,
            env=env,
        )
        actual = res.stdout.strip()
        print(f"[*] Case '{c['desc']}': input PORT={c['env'].get('PORT', '<UNSET>')} -> Result: '{actual}' | Expected: '{c['expected']}'")
        assert actual == c["expected"], f"Failed case {c['desc']}: expected {c['expected']}, got {actual}"
    print("[+] All POSIX shell parameter substitution test cases PASSED!")


def test_dockerfile_syntax_and_security():
    """Empirically verify Dockerfile commands, multi-stage isolation, and UID 1000 configuration."""
    print("\n=== [2] Dockerfile Syntax & Security Inspection ===")
    dockerfile_path = ROOT_DIR / "Dockerfile"
    assert dockerfile_path.exists(), "Dockerfile does not exist"
    content = dockerfile_path.read_text(encoding="utf-8")

    # 1. Multi-stage build isolation
    assert "FROM node:20-alpine AS web-builder" in content, "Stage 1 must use node:20-alpine AS web-builder"
    assert "FROM python:3.11-slim" in content, "Stage 2 must use python:3.11-slim"
    assert "COPY --chown=user:user --from=web-builder /app/web/dist ./web/dist" in content, "Stage 2 must copy only dist from web-builder"

    # Verify node/npm are not installed or leaked in runtime stage
    assert "apk add" not in content.split("FROM python:3.11-slim")[1], "apk commands must not leak into Python stage"

    # 2. Non-root UID 1000 user
    assert "useradd -m -u 1000 user" in content, "useradd with UID 1000 missing"
    assert "USER user" in content, "USER user directive missing"

    # 3. Directory creation and write permissions
    assert "mkdir -p /app/backend/cache/forecast_audit" in content, "cache directory creation missing"
    assert "/app/backend/data/ohlcv" in content, "data directory creation missing"
    assert "chown -R 1000:1000 /app /home/user" in content, "chown to UID 1000 missing"
    assert "chmod -R 775 /app/backend" in content, "write permission chmod 775 missing"
    assert "chmod -R 777 /tmp" in content, "write permission chmod 777 /tmp missing"

    # 4. Port exposure and CMD
    assert "EXPOSE 7860" in content, "EXPOSE 7860 missing"
    assert 'CMD ["sh", "-c", "uvicorn api:app --app-dir backend --host 0.0.0.0 --port ${PORT:-7860}"]' in content, "CMD incorrect"

    print("[+] Dockerfile syntax, UID 1000 user, and multi-stage isolation verified successfully!")


def test_dockerignore_rules():
    """Verify .dockerignore excludes unwanted files and protects sensitive data."""
    print("\n=== [3] .dockerignore Rules Inspection ===")
    dockerignore_path = ROOT_DIR / ".dockerignore"
    assert dockerignore_path.exists(), ".dockerignore missing"
    rules = dockerignore_path.read_text(encoding="utf-8").splitlines()
    clean_rules = [r.strip() for r in rules if r.strip() and not r.startswith("#")]

    mandatory_patterns = [
        ".git",
        ".agents",
        ".env",
        "api key.ini",
        "node_modules",
        "web/dist",
        "backend/cache",
    ]
    for pattern in mandatory_patterns:
        matched = any(pattern in r for r in clean_rules)
        print(f"[*] Checking pattern '{pattern}' in .dockerignore -> {'FOUND' if matched else 'MISSING'}")
        assert matched, f"Mandatory ignore pattern '{pattern}' missing from .dockerignore"
    print("[+] .dockerignore rules verified successfully!")


def test_readme_hf_frontmatter():
    """Verify Hugging Face Space YAML frontmatter in README.md."""
    print("\n=== [4] Hugging Face Spaces Frontmatter Inspection ===")
    readme_path = ROOT_DIR / "README.md"
    assert readme_path.exists(), "README.md does not exist"
    lines = readme_path.read_text(encoding="utf-8").splitlines()

    assert lines[0] == "---", "README.md must start with YAML frontmatter delimiter '---'"
    end_idx = -1
    for i in range(1, len(lines)):
        if lines[i] == "---":
            end_idx = i
            break
    assert end_idx > 0, "Closing '---' delimiter for YAML frontmatter missing"

    frontmatter = "\n".join(lines[1:end_idx])
    print(f"[*] Extracted frontmatter:\n{frontmatter}")
    assert "sdk: docker" in frontmatter, "Frontmatter must contain 'sdk: docker'"
    assert "app_port: 7860" in frontmatter, "Frontmatter must contain 'app_port: 7860'"
    print("[+] Hugging Face Spaces metadata verified successfully!")


def test_fastapi_endpoints_and_routing():
    """Empirically test healthcheck (GET and HEAD), static asset routing, and SPA fallback."""
    print("\n=== [5] FastAPI Endpoints & Routing Empirical Tests ===")
    client = TestClient(app)

    # 1. Healthcheck GET
    resp_get = client.get("/api/health")
    print(f"[*] GET /api/health -> Status: {resp_get.status_code}, Body: {resp_get.text}")
    assert resp_get.status_code == 200, f"Expected 200, got {resp_get.status_code}"
    data_get = resp_get.json()
    assert data_get.get("status") == "ok", f"Expected status 'ok', got {data_get}"
    assert "timestamp" in data_get, "Timestamp missing from health response"

    # 2. Healthcheck HEAD
    resp_head = client.head("/api/health")
    print(f"[*] HEAD /api/health -> Status: {resp_head.status_code}, Headers: {dict(resp_head.headers)}, Body len: {len(resp_head.content)}")
    assert resp_head.status_code == 200, f"HEAD /api/health failed with status {resp_head.status_code}"
    assert len(resp_head.content) == 0, f"HEAD response body must be empty, got {len(resp_head.content)} bytes"
    assert "application/json" in resp_head.headers.get("content-type", ""), "Content-type must be application/json"

    # 3. Static assets routing
    dist_dir = ROOT_DIR / "web" / "dist"
    assets_dir = dist_dir / "assets"
    assert assets_dir.exists(), "web/dist/assets does not exist"
    asset_files = list(assets_dir.glob("*.*"))
    assert len(asset_files) > 0, "No assets found in web/dist/assets"

    for asset_file in asset_files:
        asset_url = f"/assets/{asset_file.name}"
        resp_asset = client.get(asset_url)
        print(f"[*] GET {asset_url} -> Status: {resp_asset.status_code}, Content-Type: {resp_asset.headers.get('content-type')}")
        assert resp_asset.status_code == 200, f"Asset {asset_url} returned status {resp_asset.status_code}"
        assert len(resp_asset.content) > 0, f"Asset {asset_url} returned empty content"

    # 4. SPA Fallback routing
    spa_routes = ["/", "/overview", "/stock/HPG", "/watchlist", "/deep-analysis"]
    for route in spa_routes:
        resp_spa = client.get(route)
        print(f"[*] GET {route} -> Status: {resp_spa.status_code}, Content-Type: {resp_spa.headers.get('content-type')}")
        assert resp_spa.status_code == 200, f"SPA route {route} failed with status {resp_spa.status_code}"
        assert "text/html" in resp_spa.headers.get("content-type", ""), f"Route {route} did not return HTML"
        assert "<div id=\"root\"></div>" in resp_spa.text, f"Route {route} did not serve index.html"

    # 5. Demo HTML page
    resp_demo = client.get("/fiintrade_demo.html")
    print(f"[*] GET /fiintrade_demo.html -> Status: {resp_demo.status_code}")
    assert resp_demo.status_code == 200, f"fiintrade_demo.html returned status {resp_demo.status_code}"

    # 6. API 404 behavior: /api/non_existent must return 404 JSON, NOT index.html!
    resp_api_404 = client.get("/api/non_existent_subpath_test")
    print(f"[*] GET /api/non_existent_subpath_test -> Status: {resp_api_404.status_code}, Body: {resp_api_404.text}")
    assert resp_api_404.status_code == 404, f"API unknown endpoint must return 404, got {resp_api_404.status_code}"
    assert "API endpoint không tồn tại." in resp_api_404.text, "API 404 did not return expected error message"

    # 7. Path Traversal Adversarial Attack
    traversal_paths = [
        "/assets/../../Dockerfile",
        "/assets/../index.html",
        "/../../etc/passwd",
        "/assets/..%2f..%2fDockerfile",
    ]
    for p in traversal_paths:
        resp_attack = client.get(p)
        print(f"[*] Path traversal probe '{p}' -> Status: {resp_attack.status_code}")
        # Traversal under /assets must either return 404 or be blocked
        assert "FROM python:3.11-slim" not in resp_attack.text, f"Path traversal leaked Dockerfile content on {p}!"

    print("[+] All FastAPI endpoint, static routing, SPA fallback, and security tests PASSED!")


if __name__ == "__main__":
    test_posix_shell_parameter_substitution()
    test_dockerfile_syntax_and_security()
    test_dockerignore_rules()
    test_readme_hf_frontmatter()
    test_fastapi_endpoints_and_routing()
    print("\n=======================================================")
    print("   [+] ALL MILESTONE 1 EMPIRICAL TESTS PASSED!        ")
    print("=======================================================\n")
