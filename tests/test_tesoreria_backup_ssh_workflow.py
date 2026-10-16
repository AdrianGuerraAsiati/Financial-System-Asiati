"""Contratos sintéticos del workflow de respaldo documental de Tesorería.

Estas pruebas nunca contactan AWS ni manipulan facturas reales.
"""
from pathlib import Path


WORKFLOW = Path(".github/workflows/backup-tesoreria-docs.yml")


def _paso(nombre: str) -> str:
    texto = WORKFLOW.read_text(encoding="utf-8")
    encabezado = f"      - name: {nombre}\n"
    assert texto.count(encabezado) == 1
    bloque = texto.split(encabezado, 1)[1]
    return bloque.split("\n      - name: ", 1)[0]


def test_respaldo_obtiene_y_configura_certificado_temporal_de_lightsail():
    acceso = _paso("Obtain temporary Lightsail SSH key")
    assert "get-instance-access-details" in acceso
    assert ".accessDetails.privateKey" in acceso
    assert ".accessDetails.certKey // empty" in acceso
    assert "if [[ -n \"$CERT_KEY\" ]]" in acceso
    assert 'printf \'%s\\n\' "$CERT_KEY" > "$RUNNER_TEMP/tesoreria-ssh.pem-cert.pub"' in acceso
    assert 'chmod 600 "$RUNNER_TEMP/tesoreria-ssh.pem"' in acceso
    assert 'chmod 644 "$RUNNER_TEMP/tesoreria-ssh.pem-cert.pub"' in acceso
    assert 'ssh-keygen -L -f "$RUNNER_TEMP/tesoreria-ssh.pem-cert.pub"' in acceso


def test_certificado_se_descubre_junto_a_identidad_y_se_elimina():
    copia = _paso("Create, verify and upload encrypted document backup")
    assert '-i "$RUNNER_TEMP/tesoreria-ssh.pem"' in copia
    # OpenSSH usa automáticamente un certificado con el sufijo '-cert.pub'.
    assert 'rm -f "$ARCHIVO" "$MANIFIESTO"' in copia
    assert '"$RUNNER_TEMP/tesoreria-ssh.pem-cert.pub"\' EXIT' in copia
    assert 'test -s "$ARCHIVO"' in copia
    assert 'aws s3api head-object' in copia


def test_respaldo_no_se_ejecuta_con_un_push_o_pr():
    workflow = WORKFLOW.read_text(encoding="utf-8")
    disparadores = workflow.split("permissions:", 1)[0]
    assert "schedule:" in disparadores
    assert "workflow_dispatch:" in disparadores
    assert "pull_request:" not in disparadores
    assert "push:" not in disparadores
