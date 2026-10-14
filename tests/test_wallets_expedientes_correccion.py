"""Controles documentales de corrección: sin mutación de cargas."""
from decimal import Decimal
from unittest.mock import Mock, patch
import pytest
from app.motores.conciliacion_wallets.expedientes_correccion import preparar, decidir

BASE=dict(empresa_id=1,periodo_id=2,ejecucion_id=3,carga_id=4,
          movimiento_ref="M1",valor_anterior=Decimal("100.00"),
          valor_propuesto=Decimal("101.00"),evidencia_antes_ref="prueba://antes",
          evidencia_despues_ref="prueba://despues",justificacion="Corrección",
          usuario_id=5)

def test_periodo_cerrado_impide_preparar():
    session=Mock()
    session.scalar.return_value=Mock(cerrado=True)
    with pytest.raises(ValueError,match="cerrado"):
        preparar(session,**BASE)

def test_rechaza_carga_o_reapertura_ajena():
    session=Mock()
    session.scalar.side_effect=[Mock(cerrado=False),None,None]
    with pytest.raises(LookupError,match="Ejecución o carga"):
        preparar(session,**BASE)

def test_valores_iguales_no_son_correccion():
    session=Mock()
    session.scalar.side_effect=[Mock(cerrado=False),Mock(),Mock()]
    with pytest.raises(ValueError,match="Sin diferencia"):
        preparar(session,**{**BASE,"valor_propuesto":Decimal("100.00")})

def test_no_permite_decidir_expediente_propio():
    session=Mock()
    session.scalar.side_effect=[Mock(cerrado=False),Mock(decision=None,preparado_por=5)]
    with pytest.raises(ValueError,match="propia"):
        decidir(session,empresa_id=1,periodo_id=2,expediente_id=3,
               usuario_id=5,decision="AUTORIZAR_EJECUCION",motivo="revisado")
