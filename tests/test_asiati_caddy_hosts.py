"""Invariantes de publicación HTTPS de ASIATI en Lightsail."""
from pathlib import Path


RAIZ = Path(__file__).resolve().parents[1]


def test_caddy_atiende_dominio_tecnico_y_corporativo():
    configuracion = (RAIZ / "ops" / "Caddyfile").read_text(encoding="utf-8")
    assert "{$ASIATI_DOMAIN}, financial.asiaticorp.com {" in configuracion
    assert "reverse_proxy api:8000" in configuracion


def test_despliegue_recarga_caddyfile_despues_de_intercambiar_release():
    script = (RAIZ / "ops" / "deploy_production.sh").read_text(encoding="utf-8")
    assert '"${DC[@]}" run --rm --no-deps --entrypoint caddy caddy validate' in script
    assert '"${DC[@]}" up -d --no-deps --force-recreate caddy' in script


def test_despliegue_valida_https_en_ambos_dominios():
    workflow = (RAIZ / ".github" / "workflows" / "deploy-development.yml").read_text(encoding="utf-8")
    assert "CORPORATE_DOMAIN: financial.asiaticorp.com" in workflow
    assert 'for domain in "$DEVELOPMENT_DOMAIN" "$CORPORATE_DOMAIN"; do' in workflow
