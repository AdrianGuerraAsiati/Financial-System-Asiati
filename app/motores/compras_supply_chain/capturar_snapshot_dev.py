from __future__ import annotations

import json
import os

from app.core.auditoria.service import registrar_auditoria
from app.core.session import crear_session

from .google_sheets import construir_fuente_compras_desde_entorno
from .persistencia import guardar_snapshot, snapshot_como_dict


def main() -> None:
    app_env = os.getenv("APP_ENV", "development").strip().lower()
    if app_env == "production":
        raise SystemExit(
            "capturar_snapshot_dev no puede ejecutarse con APP_ENV=production."
        )

    fuente = construir_fuente_compras_desde_entorno()
    if fuente.configuracion.modo_fuente != "EXCEL_LOCAL":
        raise SystemExit(
            "capturar_snapshot_dev requiere COMPRAS_EXCEL_LOCAL_FILE."
        )

    empresa_id = fuente.configuracion.empresa_id
    snapshot = fuente.obtener_snapshot(
        empresa_id=empresa_id,
        forzar_lectura=True,
    )

    if not snapshot.esquema_valido:
        diagnosticos = [
            diagnostico.como_dict()
            for diagnostico in snapshot.diagnosticos
        ]
        raise SystemExit(
            "El Excel local no cumple el contrato de Compras: "
            + json.dumps(diagnosticos, ensure_ascii=False)
        )

    with crear_session() as session:
        persistido, creado = guardar_snapshot(
            session,
            empresa_id=empresa_id,
            spreadsheet_id=fuente.configuracion.spreadsheet_id,
            modo_fuente=fuente.configuracion.modo_fuente,
            rangos_por_pais=fuente.configuracion.rangos_por_pais,
            snapshot=snapshot,
        )
        if creado:
            registrar_auditoria(
                session,
                usuario_id=None,
                empresa_id=empresa_id,
                accion="compras.snapshot_guardado_desarrollo",
                entidad="compras_snapshot",
                entidad_id=persistido.id,
                despues={
                    "contenido_hash": persistido.contenido_hash,
                    "lineas": persistido.lineas,
                    "esquema_valido": persistido.esquema_valido,
                    "modo_fuente": persistido.modo_fuente,
                },
            )
        session.commit()
        session.refresh(persistido)

        print(
            json.dumps(
                {
                    "creado": creado,
                    "snapshot": snapshot_como_dict(persistido),
                },
                ensure_ascii=False,
                default=str,
            )
        )


if __name__ == "__main__":
    main()
