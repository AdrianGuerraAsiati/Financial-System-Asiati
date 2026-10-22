"""Promoción única y auditada de la cuenta técnica designada en desarrollo.

Solo puede ejecutarse en APP_ENV=development durante el despliegue autorizado.
No concede privilegios al rol TI ni modifica otras cuentas.
"""
from __future__ import annotations

import os
from sqlalchemy import select

from app.core.auditoria import registrar_auditoria
from app.core.session import crear_session
from app.core.usuarios.model import Usuario
from app.core.usuarios.roles import ROL_SUPER_ADMINISTRADOR, ROL_TI


CUENTA_AUTORIZADA = "sistemas@asiati.com.co"


def main() -> int:
    if os.getenv("APP_ENV", "").strip().lower() != "development":
        raise RuntimeError("Esta promoción solo puede ejecutarse en desarrollo.")

    with crear_session() as session:
        usuario = session.scalar(
            select(Usuario)
            .where(Usuario.email == CUENTA_AUTORIZADA)
            .with_for_update()
        )
        if usuario is None or not usuario.activo:
            raise RuntimeError("La cuenta técnica designada no existe o está inactiva.")
        if usuario.rol == ROL_SUPER_ADMINISTRADOR:
            print("La cuenta técnica ya es superadministradora; sin cambios.")
            return 0
        if usuario.rol != ROL_TI:
            raise RuntimeError(
                "Rol inesperado para la cuenta técnica; se requiere revisión manual."
            )

        anterior = usuario.rol
        usuario.rol = ROL_SUPER_ADMINISTRADOR
        registrar_auditoria(
            session,
            usuario_id=None,  # Cambio automatizado desde despliegue, no una sesión humana.
            accion="usuario.promover_superadmin_dev",
            entidad="usuario",
            entidad_id=usuario.id,
            antes={"email": CUENTA_AUTORIZADA, "rol": anterior},
            despues={"email": CUENTA_AUTORIZADA, "rol": ROL_SUPER_ADMINISTRADOR},
        )
        session.commit()
        print("Promoción de la cuenta técnica completada y auditada.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
