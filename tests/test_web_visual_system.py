from fastapi.testclient import TestClient

from app.main import app


def test_shell_exposes_refined_brand_and_navigation_structure() -> None:
    response = TestClient(app).get("/")

    assert response.status_code == 200
    assert 'class="brand-mark"' in response.text
    assert 'class="brand-lockup"' in response.text
    assert 'class="sidebar-section-label"' in response.text
    assert 'class="nav-icon"' in response.text
    assert 'class="nav-badge"' in response.text
    assert "Plataforma Financiera" in response.text


def test_stylesheet_contains_visual_tokens_accessibility_and_responsive_rules() -> None:
    response = TestClient(app).get("/static/styles.css")

    assert response.status_code == 200
    css = response.text
    assert "Visual system v1" in css
    assert "--accent: #2f6fed;" in css
    assert "--nav: #0c1322;" in css
    assert "button:focus-visible" in css
    assert "@media (prefers-reduced-motion: reduce)" in css
    assert "@media (max-width: 850px)" in css
    assert ".auth-shell::before" in css
    assert ".home-module-card:hover" in css
