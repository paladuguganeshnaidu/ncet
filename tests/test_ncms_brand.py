from pathlib import Path
from PIL import Image
from app.main import app

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "static"

def test_ncms_branding_is_consistent():
    files = [STATIC / name for name in ("app.js", "index.html", "about.html")]
    for path in files:
        text = path.read_text(encoding="utf-8")
        assert "NCET VerifyFlow" in text
        assert "NCMS VerifyFlow" not in text
        assert "Nagarjuna College of Management Studies" not in text
        assert "ncms.co.in" not in text

def test_brand_assets_are_authentic_rasters():
    for name in ("ncet-official.webp", "ngi-logo.webp"):
        with Image.open(STATIC / name) as im:
            assert im.width >= 100
            assert im.height >= 100
            assert im.format == "WEBP"

def test_existing_document_workflows_stay_intact():
    paths = {route.path for route in app.routes if hasattr(route, "path")}
    for required in ("/app", "/api/documents", "/api/users", "/api/rules", "/healthz"):
        assert required in paths
    assert app.title == "NCET VerifyFlow"
    assert "public_id='NCET-'" in (ROOT / "app/main.py").read_text(encoding="utf-8")

def test_legacy_bootstrap_secret_preserved():
    assert "NCET_BOOTSTRAP" in (ROOT / "app/bootstrap.py").read_text(encoding="utf-8")
