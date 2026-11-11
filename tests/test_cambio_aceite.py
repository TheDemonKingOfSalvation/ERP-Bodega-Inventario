from unittest.mock import MagicMock, patch

from logic.logic_mongo import registrar_cambio_aceite


def test_registrar_cambio_aceite_crea_solicitud_pendiente():
    fake_db = MagicMock()
    fake_db.carros_aceite.find_one.return_value = None
    fake_db.carros.find_one.return_value = {"placa": "ABC123", "descripcion": "Vehículo prueba"}

    with patch("logic.logic_mongo.db", fake_db):
        ok, mensaje = registrar_cambio_aceite("carro-1", 12000, observacion="Prueba")

    assert ok is True
    assert "pendiente" in mensaje.lower()
    registro_insertado = fake_db.carros_aceite.insert_one.call_args.args[0]
    assert registro_insertado["estado"] == "pendiente"
    assert registro_insertado["km"] == 12000
    fake_db.carros.update_one.assert_not_called()
