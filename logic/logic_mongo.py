from datetime import datetime
from pymongo.errors import DuplicateKeyError
from bson import ObjectId
from config.db_mongo import db
from ui.utils import coleccion_por_tipo

SI = "SI"
NO = "NO"

ESTATUS_TRABAJO_ABIERTO = ["activo", "pendiente de devolucion"]


# =========================================================
# UTILIDADES GENERALES
# =========================================================

def existe_id(coleccion, id_val):
    return db[coleccion].find_one({"_id": id_val}, projection={"_id": 1}) is not None


def fecha_hoy():
    return datetime.now().strftime("%Y-%m-%d")


def registrar_movimiento(tipo, item_id, nombre, cantidad, accion, origen="", referencia="", observacion=""):
    db.historial_movimientos.insert_one({
        "fecha": datetime.now(),
        "fecha_texto": fecha_hoy(),
        "tipo": tipo,
        "item_id": item_id,
        "nombre": nombre,
        "cantidad": int(cantidad),
        "accion": accion,
        "origen": origen,
        "referencia": referencia,
        "observacion": observacion
    })


def _coleccion_por_tipo(tipo):
    return coleccion_por_tipo(tipo)


def obtener_stock(tipo, id_val):
    if tipo == "herramienta":
        return obtener_disponibles_herramienta(id_val)

    col = coleccion_por_tipo(tipo)
    doc = db[col].find_one({"_id": id_val}, projection={"cantidad": 1})

    if not doc:
        return 0

    return int(doc.get("cantidad", 0))


def obtener_usados_herramienta(herramienta_id):
    pipeline = [
        {"$match": {
            "estatus": {"$in": ESTATUS_TRABAJO_ABIERTO},
            "detalle": {
                "$elemMatch": {"tipo": "herramienta", "id": herramienta_id}
            },
        }},
        {"$unwind": "$detalle"},
        {"$match": {"detalle.tipo": "herramienta", "detalle.id": herramienta_id}},
        {"$group": {
            "_id": None,
            "usados": {
                "$sum": {
                    "$max": [
                        {"$subtract": ["$detalle.cantidad", "$detalle.vuelto"]},
                        0,
                    ]
                }
            },
        }},
    ]

    resultado = list(db.trabajos.aggregate(pipeline))
    if not resultado:
        return 0
    return int(resultado[0].get("usados", 0))


def obtener_usados_herramientas_batch():
    """Devuelve {herramienta_id: unidades_en_uso} en una sola agregacion."""
    pipeline = [
        {"$match": {"estatus": {"$in": ESTATUS_TRABAJO_ABIERTO}}},
        {"$unwind": "$detalle"},
        {"$match": {"detalle.tipo": "herramienta"}},
        {"$project": {
            "id": "$detalle.id",
            "retenido": {
                "$max": [
                    {"$subtract": ["$detalle.cantidad", {"$ifNull": ["$detalle.vuelto", 0]}]},
                    0,
                ]
            },
        }},
        {"$match": {"retenido": {"$gt": 0}}},
        {"$group": {"_id": "$id", "usados": {"$sum": "$retenido"}}},
    ]

    return {str(item["_id"]): int(item["usados"]) for item in db.trabajos.aggregate(pipeline)}


def obtener_disponibles_herramienta(herramienta_id):
    herramienta = db.herramientas.find_one(
        {"_id": herramienta_id},
        projection={"cantidad": 1},
    )
    if not herramienta:
        return 0
    cantidad_total = int(herramienta.get("cantidad", 0))
    usados = obtener_usados_herramienta(herramienta_id)
    return max(cantidad_total - usados, 0)


def descontar_stock(tipo, id_val, cantidad, origen="trabajo", referencia="", observacion=""):
    cantidad = int(cantidad)
    col = coleccion_por_tipo(tipo)
    doc = db[col].find_one({"_id": id_val}, projection={"cantidad": 1, "nombre": 1})
    if not doc:
        return False, f"No existe {tipo}: {id_val}"

    if int(doc.get("cantidad", 0)) < cantidad:
        return False, f"Stock insuficiente en {tipo}: {id_val}"

    db[col].update_one({"_id": id_val}, {"$inc": {"cantidad": -cantidad}})
    registrar_movimiento(tipo, id_val, doc.get("nombre", ""), cantidad, "SALIDA", origen, referencia, observacion)
    return True, "OK"


def devolver_stock(tipo, id_val, cantidad, origen="trabajo", referencia="", observacion=""):
    cantidad = int(cantidad)
    if cantidad <= 0:
        return True, "OK"

    col = coleccion_por_tipo(tipo)
    doc = db[col].find_one({"_id": id_val}, projection={"nombre": 1})
    nombre = doc.get("nombre", "") if doc else ""

    resultado = db[col].update_one(
        {"_id": id_val},
        {"$inc": {"cantidad": cantidad}},
        upsert=False,
    )

    if resultado.matched_count == 0:
        return False, f"No existe {tipo}: {id_val}"

    registrar_movimiento(tipo, id_val, nombre, cantidad, "ENTRADA", origen, referencia, observacion)
    return True, "OK"


def obtener_item(coleccion, id_val):
    return db[coleccion].find_one({"_id": id_val})


def buscar_por_texto(coleccion, texto=""):
    texto = str(texto or "").strip()
    if not texto:
        return list(db[coleccion].find())

    patron = {"$regex": texto, "$options": "i"}
    return list(db[coleccion].find({
        "$or": [
            {"nombre": patron},
            {"placa": patron},
            {"descripcion": patron},
        ]
    }))


# =========================================================
# INVENTARIOS
# =========================================================

def agregar_herramienta(id_val, nombre, cantidad):
    try:
        db.herramientas.insert_one({
            "_id": id_val,
            "nombre": nombre,
            "cantidad": int(cantidad)
        })
        registrar_movimiento("herramienta", id_val, nombre, cantidad, "ALTA", "inventario", id_val)
        return True, "OK"
    except DuplicateKeyError:
        return False, "ID duplicado"


def editar_herramienta(id_val, nombre, cantidad):
    db.herramientas.update_one({"_id": id_val}, {"$set": {
        "nombre": nombre,
        "cantidad": int(cantidad)
    }})
    return True, "OK"


def eliminar_herramienta(id_val):
    db.herramientas.delete_one({"_id": id_val})


def agregar_consumible(id_val, nombre, cantidad, stock_minimo=3):
    try:
        db.consumibles.insert_one({
            "_id": id_val,
            "nombre": nombre,
            "cantidad": int(cantidad),
            "stock_minimo": int(stock_minimo)
        })
        registrar_movimiento("consumible", id_val, nombre, cantidad, "ALTA", "inventario", id_val)
        return True, "OK"
    except DuplicateKeyError:
        return False, "ID duplicado"


def editar_consumible(id_val, nombre, cantidad, stock_minimo=3):
    db.consumibles.update_one({"_id": id_val}, {"$set": {
        "nombre": nombre,
        "cantidad": int(cantidad),
        "stock_minimo": int(stock_minimo)
    }})
    return True, "OK"


def eliminar_consumible(id_val):
    db.consumibles.delete_one({"_id": id_val})


def agregar_epp(id_val, nombre, cantidad, stock_minimo=3):
    try:
        db.epp.insert_one({
            "_id": id_val,
            "nombre": nombre,
            "cantidad": int(cantidad),
            "stock_minimo": int(stock_minimo)
        })
        registrar_movimiento("epp", id_val, nombre, cantidad, "ALTA", "inventario", id_val)
        return True, "OK"
    except DuplicateKeyError:
        return False, "ID duplicado"


def editar_epp(id_val, nombre, cantidad, stock_minimo=3):
    db.epp.update_one({"_id": id_val}, {"$set": {
        "nombre": nombre,
        "cantidad": int(cantidad),
        "stock_minimo": int(stock_minimo)
    }})
    return True, "OK"


def eliminar_epp(id_val):
    db.epp.delete_one({"_id": id_val})


def agregar_pvc(id_val, nombre, cantidad, tipo, stock_minimo=3):
    try:
        db.pvc.insert_one({
            "_id": id_val,
            "nombre": nombre,
            "cantidad": int(cantidad),
            "tipo": tipo,
            "stock_minimo": int(stock_minimo)
        })
        registrar_movimiento("pvc", id_val, nombre, cantidad, "ALTA", "inventario", id_val)
        return True, "OK"
    except DuplicateKeyError:
        return False, "ID duplicado"


def editar_pvc(id_val, nombre, cantidad, tipo, stock_minimo=3):
    db.pvc.update_one({"_id": id_val}, {"$set": {
        "nombre": nombre,
        "cantidad": int(cantidad),
        "tipo": tipo,
        "stock_minimo": int(stock_minimo)
    }})
    return True, "OK"


def eliminar_pvc(id_val):
    db.pvc.delete_one({"_id": id_val})


def agregar_proveedor(id_val, nombre, telefono):
    try:
        db.proveedores.insert_one({
            "_id": id_val,
            "nombre": nombre,
            "telefono": telefono
        })
        return True, "OK"
    except DuplicateKeyError:
        return False, "ID duplicado"


def editar_proveedor(id_val, nombre, telefono):
    db.proveedores.update_one({"_id": id_val}, {"$set": {
        "nombre": nombre,
        "telefono": telefono
    }})
    return True, "OK"


def eliminar_proveedor(id_val):
    db.proveedores.delete_one({"_id": id_val})


def obtener_proveedores():
    return list(db.proveedores.find().sort("nombre", 1))


# =========================================================
# MÃƒÆ’Ã‚ÂQUINAS
# =========================================================

def agregar_maquina(id_val, nombre):
    try:
        db.maquinas.insert_one({
            "_id": id_val,
            "nombre": nombre,
            "disponibilidad": SI,
            "estatus": "disponible"
        })
        return True, "OK"
    except DuplicateKeyError:
        return False, "ID duplicado"


def editar_maquina(id_val, nombre):
    db.maquinas.update_one({"_id": id_val}, {"$set": {"nombre": nombre}})
    return True, "OK"


def eliminar_maquina(id_val):
    db.maquinas.delete_one({"_id": id_val})


def guardar_requerimiento_maquina(codigo, nombre, fecha, razon, pdf_path):
    from ui.utils import normalizar_ruta_relativa
    ruta_relativa = normalizar_ruta_relativa(pdf_path)
    db.requerimientos_maquinas.insert_one({
        "codigo": codigo,
        "nombre": nombre,
        "fecha": fecha,
        "razon": razon,
        "pdf_path": ruta_relativa,
        "estado": "en mantenimiento",
        "fecha_terminado": ""
    })
    db.maquinas.update_one(
        {"_id": codigo},
        {"$set": {"disponibilidad": NO, "estatus": "mantenimiento"}}
    )
    return True, "OK"


def obtener_requerimientos_maquinas():
    return list(db.requerimientos_maquinas.find().sort("fecha", -1))


def terminar_mantenimiento_maquina(requerimiento_id):
    try:
        oid = ObjectId(requerimiento_id)
    except Exception:
        return False, "Identificador de mantenimiento invalido."

    req = db.requerimientos_maquinas.find_one({"_id": oid})
    if not req:
        return False, "No se encontro el mantenimiento."

    if req.get("estado") == "terminado":
        return False, "Este mantenimiento ya fue terminado."

    db.requerimientos_maquinas.update_one(
        {"_id": oid},
        {"$set": {"estado": "terminado", "fecha_terminado": fecha_hoy()}}
    )

    db.maquinas.update_one(
        {"_id": req.get("codigo")},
        {"$set": {"disponibilidad": SI, "estatus": "disponible"}}
    )

    return True, "Mantenimiento terminado correctamente."


# =========================================================
# CARROS
# =========================================================

def agregar_carro(id_val, placa, descripcion, kmCambio):
    try:
        db.carros.insert_one({
            "_id": id_val,
            "placa": placa,
            "descripcion": descripcion,
            "km_cambio_intervalo": int(kmCambio),
            "disponibilidad": SI
        })
        return True, "OK"
    except DuplicateKeyError:
        return False, "ID duplicado"


def editar_carro(id_val, placa, descripcion, kmCambio):
    db.carros.update_one({"_id": id_val}, {"$set": {
        "placa": placa,
        "descripcion": descripcion,
        "km_cambio_intervalo": int(kmCambio)
    }})
    return True, "OK"


def eliminar_carro(id_val):
    db.carros.delete_one({"_id": id_val})


# =========================================================
# TRABAJADORES
# =========================================================

def agregar_trabajador(id_val, nombre, tipo):
    try:
        db.trabajadores.insert_one({
            "_id": id_val,
            "nombre": nombre,
            "tipo": tipo,
            "detalle_epp": []
        })
        return True, "OK"
    except DuplicateKeyError:
        return False, "ID duplicado"


def editar_trabajador(id_val, nombre, tipo):
    db.trabajadores.update_one({"_id": id_val}, {"$set": {
        "nombre": nombre,
        "tipo": tipo
    }})
    return True, "OK"


def eliminar_trabajador(id_val):
    db.trabajadores.delete_one({"_id": id_val})


def entregar_epp_trabajador(trabajador_id, epps):
    trabajador = db.trabajadores.find_one(
        {"_id": trabajador_id},
        projection={"_id": 1, "detalle_epp": 1},
    )
    if not trabajador:
        return False, "Trabajador no existe"

    entregas = []
    errores = []

    for item in epps:
        codigo = str(item.get("codigo", "")).strip()
        reposicion = str(item.get("reposicion", "No"))
        if not codigo:
            errores.append("Hay un EPP sin codigo.")
            continue

        epp = db.epp.find_one({"_id": codigo}, projection={"cantidad": 1, "nombre": 1})
        if not epp:
            errores.append(f"EPP no existe: {codigo}")
            continue

        if int(epp.get("cantidad", 0)) <= 0:
            errores.append(f"Sin stock: {codigo}")
            continue

        db.epp.update_one({"_id": codigo}, {"$inc": {"cantidad": -1}})
        registrar_movimiento("epp", codigo, epp.get("nombre", ""), 1, "SALIDA", "trabajador", trabajador_id)

        entregas.append({
            "codigo": codigo,
            "nombre": epp.get("nombre", ""),
            "fecha_entrega": fecha_hoy(),
            "reposicion": reposicion,
        })

    if not entregas:
        return False, "\n".join(errores) or "No se entrego ningun EPP"

    db.trabajadores.update_one({"_id": trabajador_id}, {"$push": {"detalle_epp": {"$each": entregas}}})
    return True, "OK"


def asignar_epp(trabajador_id, epp_id, cantidad):
    return entregar_epp_trabajador(trabajador_id, [{"codigo": epp_id, "reposicion": "No"} for _ in range(int(cantidad))])


def obtener_detalle_epp_trabajador(trabajador_id):
    trabajador = db.trabajadores.find_one({"_id": trabajador_id}, projection={"detalle_epp": 1})
    if not trabajador:
        return []
    return trabajador.get("detalle_epp", [])


# =========================================================
# TRABAJOS
# =========================================================

def generar_id_trabajo():
    hoy = datetime.now()
    prefijo = f"{hoy.month}.{hoy.day}.{str(hoy.year)[-2:]}"
    cantidad_hoy = db.trabajos.count_documents({"_id": {"$regex": f"^{prefijo}\\."}})
    return f"{prefijo}.{cantidad_hoy + 1}"


def crear_trabajo(planta):
    nuevo_id = generar_id_trabajo()
    db.trabajos.insert_one({
        "_id": nuevo_id,
        "nombre": planta,
        "fecha_inicio": datetime.now(),
        "fecha_fin": None,
        "estatus": "activo",
        "detalle": []
    })
    return nuevo_id


def eliminar_trabajo(trabajo_id):
    db.trabajos.delete_one({"_id": trabajo_id})


def revertir_trabajo(trabajo_id):
    db.trabajos.update_one({"_id": trabajo_id}, {"$set": {"estatus": "activo", "fecha_fin": None}})


def obtener_trabajo(trabajo_id):
    return db.trabajos.find_one({"_id": trabajo_id})


def obtener_detalle_trabajo(trabajo_id):
    trabajo = obtener_trabajo(trabajo_id)
    if not trabajo:
        return []
    return trabajo.get("detalle", [])


def actualizar_datos_salida_trabajo(trabajo_id, **kwargs):
    db.trabajos.update_one({"_id": trabajo_id}, {"$set": kwargs})


def guardar_detalle_trabajo(trabajo_id, detalles_nuevos):
    trabajo = db.trabajos.find_one({"_id": trabajo_id})
    if not trabajo:
        return False, "Trabajo no existe"

    detalles_anteriores = trabajo.get("detalle", [])
    mapa_anterior = {(d["tipo"], d["id"]): d for d in detalles_anteriores}
    mapa_nuevo = {(d["tipo"], d["id"]): d for d in detalles_nuevos}
    tipos_stock = {"consumible", "pvc"}

    # =========================================================
    # VALIDACIÃƒÆ’Ã¢â‚¬Å“N DE DEVOLUCIONES YA REGISTRADAS
    # =========================================================
    for clave, nuevo in mapa_nuevo.items():
        tipo, id_val = clave
        if tipo not in tipos_stock:
            continue
        viejo = mapa_anterior.get(clave, {})
        vuelto_anterior_registrado = int(viejo.get("vuelto_registrado", 0))
        vuelto_nuevo = int(nuevo.get("vuelto", 0))
        if vuelto_nuevo < vuelto_anterior_registrado:
            return (
                False,
                f"No puedes disminuir la cantidad devuelta de {tipo}: {id_val}. "
                f"Ya se registraron {vuelto_anterior_registrado} unidad(es) devuelta(s)."
            )

    # =========================================================
    # AJUSTE DE STOCK POR CAMBIOS DE CANTIDAD O ELIMINACIÃƒÆ’Ã¢â‚¬Å“N
    # =========================================================
    for clave, viejo in mapa_anterior.items():
        tipo, id_val = clave
        if tipo not in tipos_stock:
            continue
        cantidad_vieja = int(viejo.get("cantidad", 0))
        usado_viejo = int(viejo.get("usado", 0))
        vuelto_registrado_viejo = int(viejo.get("vuelto_registrado", 0))
        nuevo = mapa_nuevo.get(clave)
        if nuevo is None:
            cantidad_a_devolver = max(
                cantidad_vieja - usado_viejo - vuelto_registrado_viejo,
                0,
            )
            if cantidad_a_devolver > 0:
                devolver_stock(
                    tipo, id_val, cantidad_a_devolver,
                    "trabajo", trabajo_id, "Se quitÃƒÆ’Ã‚Â³ del trabajo",
                )
        else:
            cantidad_nueva = int(nuevo.get("cantidad", 0))
            diferencia = cantidad_nueva - cantidad_vieja
            if diferencia > 0:
                ok, msg = descontar_stock(
                    tipo, id_val, diferencia,
                    "trabajo", trabajo_id, "Aumento de reserva",
                )
                if not ok:
                    return False, msg
            elif diferencia < 0:
                devolver_stock(
                    tipo, id_val, abs(diferencia),
                    "trabajo", trabajo_id, "ReducciÃƒÆ’Ã‚Â³n de reserva",
                )

    for clave, nuevo in mapa_nuevo.items():
        tipo, id_val = clave
        if tipo not in tipos_stock or clave in mapa_anterior:
            continue
        cantidad_nueva = int(nuevo.get("cantidad", 0))
        ok, msg = descontar_stock(
            tipo, id_val, cantidad_nueva,
            "trabajo", trabajo_id, "Reserva de trabajo",
        )
        if not ok:
            return False, msg

    # =========================================================
    # DEVOLUCIÃƒÆ’Ã¢â‚¬Å“N INMEDIATA POR COLUMNA "VOLVIÃƒÆ’Ã¢â‚¬Å“"
    # =========================================================
    for clave, nuevo in mapa_nuevo.items():
        tipo, id_val = clave
        if tipo not in tipos_stock:
            continue
        viejo = mapa_anterior.get(clave, {})
        vuelto_anterior_registrado = int(viejo.get("vuelto_registrado", 0))
        vuelto_nuevo = int(nuevo.get("vuelto", 0))
        diferencia_devuelta = vuelto_nuevo - vuelto_anterior_registrado
        if diferencia_devuelta > 0:
            devolver_stock(
                tipo, id_val, diferencia_devuelta,
                "trabajo", trabajo_id, f"{tipo} devuelto desde checklist",
            )
        nuevo["vuelto_registrado"] = vuelto_nuevo

    # =========================================================
    # CONTROL DE DISPONIBILIDAD DE MÃƒÆ’Ã‚ÂQUINAS
    # =========================================================
    maquinas_anteriores = {d["id"] for d in detalles_anteriores if d["tipo"] == "maquina"}
    maquinas_nuevas = {d["id"] for d in detalles_nuevos if d["tipo"] == "maquina"}

    for maquina_id in maquinas_anteriores - maquinas_nuevas:
        db.maquinas.update_one(
            {"_id": maquina_id},
            {"$set": {"disponibilidad": SI, "estatus": "disponible"}},
        )

    for maquina_id in maquinas_nuevas - maquinas_anteriores:
        maq = db.maquinas.find_one({"_id": maquina_id}, projection={"disponibilidad": 1})
        if not maq:
            return False, f"MÃƒÆ’Ã‚Â¡quina no existe: {maquina_id}"
        if maq.get("disponibilidad") == NO:
            return False, f"MÃƒÆ’Ã‚Â¡quina no disponible: {maquina_id}"
        db.maquinas.update_one(
            {"_id": maquina_id},
            {"$set": {"disponibilidad": NO, "estatus": "trabajando"}},
        )

    db.trabajos.update_one(
        {"_id": trabajo_id},
        {"$set": {"detalle": detalles_nuevos}},
    )
    return True, "OK"


def trabajo_tiene_pendientes(detalle):
    for item in detalle:
        tipo = item.get("tipo")
        if tipo == "trabajador":
            continue
        cantidad = int(item.get("cantidad", 0))
        devuelto = bool(item.get("devuelto", False))
        usado = int(item.get("usado", 0))
        vuelto = int(item.get("vuelto", 0))
        if tipo == "maquina" and not devuelto:
            return True
        if tipo == "herramienta" and cantidad - vuelto > 0:
            return True
        if tipo in ["pvc", "consumible"] and cantidad - usado - vuelto > 0:
            return True
    return False


def finalizar_trabajo(trabajo_id):
    trabajo = db.trabajos.find_one({"_id": trabajo_id})
    if not trabajo:
        return False, "Trabajo no existe"

    detalle = trabajo.get("detalle", [])
    hay_pendientes = False

    for item in detalle:
        tipo = item.get("tipo")
        id_val = item.get("id")
        cantidad = int(item.get("cantidad", 0))
        devuelto = bool(item.get("devuelto", False))
        usado = int(item.get("usado", 0))
        vuelto = int(item.get("vuelto", 0))

        if tipo == "herramienta":
            faltante = max(cantidad - vuelto, 0)
            if faltante > 0:
                hay_pendientes = True
                item["devuelto"] = False
            else:
                item["devuelto"] = True

        elif tipo == "maquina":
            if devuelto:
                db.maquinas.update_one(
                    {"_id": id_val},
                    {"$set": {"disponibilidad": SI, "estatus": "disponible"}},
                )
            else:
                hay_pendientes = True

        elif tipo in ["consumible", "pvc"]:
            vuelto_registrado = int(item.get("vuelto_registrado", 0))
            diferencia_devuelta = max(vuelto - vuelto_registrado, 0)
            if diferencia_devuelta > 0:
                devolver_stock(
                    tipo, id_val, diferencia_devuelta,
                    "trabajo", trabajo_id, f"{tipo} devuelto al finalizar trabajo",
                )
            item["vuelto_registrado"] = max(vuelto_registrado, vuelto)
            faltante = max(cantidad - usado - vuelto, 0)
            if faltante > 0:
                hay_pendientes = True
                item["devuelto"] = False
            else:
                item["devuelto"] = True

        elif tipo == "trabajador":
            continue

    estatus = "pendiente de devolucion" if hay_pendientes else "finalizado"

    db.trabajos.update_one(
        {"_id": trabajo_id},
        {"$set": {"detalle": detalle, "estatus": estatus, "fecha_fin": datetime.now()}},
    )
    return True, "OK"


# =========================================================
# REABASTECIMIENTO
# =========================================================

COLECCIONES_REABASTECIMIENTO = {
    "epp": "epp",
    "consumible": "consumibles",
    "pvc": "pvc",
    "herramienta": "herramientas",
}


def obtener_inventario_reabastecimiento(tipo):
    coleccion = COLECCIONES_REABASTECIMIENTO.get(tipo)
    if not coleccion:
        return []
    return list(db[coleccion].find())


def guardar_requerimiento_reabastecimiento(tipo, fecha, items, pdf_path, proveedor=None, precio=0, creado_por=""):
    from ui.utils import normalizar_ruta_relativa
    ruta_relativa = normalizar_ruta_relativa(pdf_path)
    resultado = db.requerimientos_reabastecimiento.insert_one({
        "tipo": tipo,
        "fecha": fecha,
        "items": items,
        "pdf_path": ruta_relativa,
        "proveedor": proveedor or {},
        "precio": precio,
        "estado": "pendiente",
        "creado_por": creado_por,
        "fecha_creacion": datetime.now(),
    })
    registrar_evento_requerimiento(resultado.inserted_id, "CREADO", creado_por, f"Requerimiento de {tipo}")
    return True, "OK"


def obtener_requerimientos_reabastecimiento(tipo=None):
    filtro = {"tipo": tipo} if tipo else {}
    return list(db.requerimientos_reabastecimiento.find(filtro).sort("fecha", -1))


def guardar_factura_reabastecimiento(requerimiento_id, numero_factura):
    numero_factura = str(numero_factura or "").strip()
    if not numero_factura:
        return False, "El numero de factura no puede estar vacio."

    requerimiento = db.requerimientos_reabastecimiento.find_one({"_id": ObjectId(requerimiento_id)})
    if not requerimiento:
        return False, "No se encontro el requerimiento."

    if requerimiento.get("factura_editada") or str(requerimiento.get("numero_factura", "")).strip():
        return False, "El numero de factura ya fue registrado y no puede editarse otra vez."

    db.requerimientos_reabastecimiento.update_one(
        {"_id": ObjectId(requerimiento_id)},
        {"$set": {
            "numero_factura": numero_factura,
            "factura_editada": True,
            "fecha_factura": fecha_hoy(),
        }},
    )
    registrar_evento_requerimiento(
        requerimiento_id, "FACTURA_REGISTRADA", "",
        f"N. de factura: {numero_factura}",
    )
    return True, "Numero de factura guardado correctamente."


def aceptar_requerimiento_reabastecimiento(requerimiento_id, items_ajustados, aceptado_por=""):
    requerimiento = db.requerimientos_reabastecimiento.find_one({"_id": ObjectId(requerimiento_id)})
    if not requerimiento:
        return False, "No se encontrÃƒÆ’Ã‚Â³ el requerimiento."
    if requerimiento.get("estado") == "aceptado":
        return False, "Este requerimiento ya fue aceptado."

    tipo = requerimiento.get("tipo")
    coleccion = COLECCIONES_REABASTECIMIENTO.get(tipo)
    if not coleccion:
        return False, f"Tipo de inventario invÃƒÆ’Ã‚Â¡lido: {tipo}"

    errores = []
    for item in items_ajustados:
        codigo = str(item.get("codigo", "")).strip()
        cantidad = int(item.get("cantidad_aceptada", 0))
        if not codigo:
            errores.append("Hay un item sin cÃƒÆ’Ã‚Â³digo.")
            continue
        if cantidad <= 0:
            continue
        doc = db[coleccion].find_one({"_id": codigo}, projection={"nombre": 1})
        resultado = db[coleccion].update_one({"_id": codigo}, {"$inc": {"cantidad": cantidad}})
        if resultado.matched_count == 0:
            errores.append(f"No se encontrÃƒÆ’Ã‚Â³ en {coleccion} el item con ID: {codigo}")
        else:
            registrar_movimiento(
                tipo, codigo, (doc or {}).get("nombre", item.get("nombre", "")),
                cantidad, "REABASTECIMIENTO", "requerimiento", requerimiento_id,
            )

    if errores:
        return False, "\n".join(errores)

    db.requerimientos_reabastecimiento.update_one(
        {"_id": ObjectId(requerimiento_id)},
        {"$set": {
            "estado": "aceptado",
            "fecha_aceptacion": fecha_hoy(),
            "aceptado_por": aceptado_por,
            "items_aceptados": items_ajustados,
        }},
    )
    total_aceptado = sum(int(item.get("cantidad_aceptada", 0)) for item in items_ajustados)
    registrar_evento_requerimiento(
        requerimiento_id, "ACEPTADO", aceptado_por,
        f"Total aceptado: {total_aceptado} unidad(es)",
    )
    return True, "Requerimiento aceptado correctamente."


def cancelar_requerimiento_reabastecimiento(requerimiento_id, cancelado_por="", motivo=""):
    requerimiento = db.requerimientos_reabastecimiento.find_one({"_id": ObjectId(requerimiento_id)})
    if not requerimiento:
        return False, "No se encontrÃƒÆ’Ã‚Â³ el requerimiento."

    estado = requerimiento.get("estado", "")
    if estado == "aceptado":
        return False, "No se puede cancelar un requerimiento que ya fue aceptado."
    if estado == "cancelado":
        return False, "Este requerimiento ya fue cancelado."

    db.requerimientos_reabastecimiento.update_one(
        {"_id": ObjectId(requerimiento_id)},
        {"$set": {
            "estado": "cancelado",
            "fecha_cancelacion": fecha_hoy(),
            "cancelado_por": cancelado_por,
            "motivo_cancelacion": motivo,
        }},
    )
    registrar_evento_requerimiento(
        requerimiento_id, "CANCELADO", cancelado_por,
        f"Motivo: {motivo}" if motivo else "Sin motivo",
    )
    return True, "Requerimiento cancelado correctamente."


# =========================================================
# HISTORIAL DE REQUERIMIENTOS (epp / consumible / pvc / herramienta)
# =========================================================

def registrar_evento_requerimiento(requerimiento_id, accion, usuario="", detalle=""):
    db.requerimientos_reabastecimiento_historial.insert_one({
        "requerimiento_id": ObjectId(requerimiento_id),
        "accion": accion,
        "usuario": usuario,
        "detalle": detalle,
        "fecha": datetime.now(),
        "fecha_texto": fecha_hoy(),
    })


def obtener_historial_requerimiento(requerimiento_id):
    return list(
        db.requerimientos_reabastecimiento_historial
            .find({"requerimiento_id": ObjectId(requerimiento_id)})
            .sort("fecha", 1)
    )


# =========================================================
# DASHBOARD
# =========================================================

def obtener_resumen_dashboard():
    """Una sola consulta para alimentar el dashboard."""
    pipeline_maquinas = [
        {"$group": {"_id": "$estatus", "total": {"$sum": 1}}},
    ]
    conteo_estatus_maquinas = {
        str(item["_id"]): int(item["total"])
        for item in db.maquinas.aggregate(pipeline_maquinas)
    }

    conteo_trabajos = {
        str(item["_id"]): int(item["total"])
        for item in db.trabajos.aggregate([
            {"$group": {"_id": "$estatus", "total": {"$sum": 1}}},
        ])
    }

    req_pendientes = db.requerimientos_reabastecimiento.count_documents({"estado": "pendiente"})

    bajo_stock = {}
    for coleccion, tipo in (("epp", "epp"), ("consumibles", "consumible"), ("pvc", "pvc")):
        bajo_stock[tipo] = db[coleccion].count_documents({
            "$expr": {"$lte": ["$cantidad", {"$ifNull": ["$stock_minimo", 3]}]},
        })

    return {
        "maquinas_mantenimiento": conteo_estatus_maquinas.get("mantenimiento", 0),
        "trabajos_activos": conteo_trabajos.get("activo", 0),
        "trabajos_pendientes_devolucion": conteo_trabajos.get("pendiente de devolucion", 0),
        "requerimientos_pendientes": req_pendientes,
        "bajo_stock_epp": bajo_stock["epp"],
        "bajo_stock_consumibles": bajo_stock["consumible"],
        "bajo_stock_pvc": bajo_stock["pvc"],
    }


# =========================================================
# ALERTAS (modo administrador)
# =========================================================

ESTATUS_TRABAJO_NO_DEVUELTO = ["pendiente de devolucion"]


def _trabajos_con_herramientas_pendientes():
    """Devuelve la lista de herramientas o máquinas no devueltas en trabajos finalizados."""
    pipeline = [
        {"$match": {"estatus": {"$in": ESTATUS_TRABAJO_NO_DEVUELTO}}},
        {"$unwind": "$detalle"},
        {"$match": {
            "$or": [
                {
                    "$and": [
                        {"detalle.tipo": "herramienta"},
                        {"$expr": {"$gt": [
                            {"$subtract": ["$detalle.cantidad", {"$ifNull": ["$detalle.vuelto", 0]}]},
                            0,
                        ]}},
                    ],
                },
                {
                    "$and": [
                        {"detalle.tipo": "maquina"},
                        {"$expr": {"$eq": [
                            {"$ifNull": ["$detalle.devuelto", False]},
                            False,
                        ]}},
                    ],
                },
            ],
        }},
        {"$project": {
            "trabajo_id": "$_id",
            "punto": "$nombre",
            "tipo": "$detalle.tipo",
            "item_id": "$detalle.id",
            "item_nombre": "$detalle.nombre",
            "pendientes": {
                "$cond": [
                    {"$eq": ["$detalle.tipo", "herramienta"]},
                    {"$subtract": ["$detalle.cantidad", {"$ifNull": ["$detalle.vuelto", 0]}]},
                    1,
                ],
            },
        }},
    ]
    return list(db.trabajos.aggregate(pipeline))


def _requerimientos_reabastecimiento_pendientes():
    return list(db.requerimientos_reabastecimiento.find(
        {"estado": "pendiente"},
        projection={"_id": 1, "tipo": 1, "fecha": 1, "proveedor": 1, "items": 1},
    ).sort("fecha", -1))


def _mantenimientos_maquinas_activos():
    return list(db.requerimientos_maquinas.find(
        {"estado": "en mantenimiento"},
        projection={"_id": 1, "codigo": 1, "nombre": 1, "fecha": 1, "razon": 1},
    ).sort("fecha", -1))


def _orden_aceite():
    return [("updated_at", -1), ("created_at", -1), ("fecha", -1), ("_id", -1)]


def obtener_ultimo_cambio_aceite(carro_id):
    carro_id = str(carro_id or "").strip()
    if not carro_id:
        return {"km": 0, "fecha": "", "pdf_path": "", "estado": ""}

    doc = db.carros_aceite.find_one(
        {"carro_id": carro_id, "estado": {"$ne": "pendiente"}},
        projection={"km": 1, "fecha": 1, "pdf_path": 1, "estado": 1},
        sort=_orden_aceite(),
    )
    if doc:
        return {
            "km": int(doc.get("km", 0) or 0),
            "fecha": doc.get("fecha", ""),
            "pdf_path": doc.get("pdf_path", ""),
            "estado": doc.get("estado", ""),
        }

    carro = db.carros.find_one({"_id": carro_id}, projection={"ultimo_cambio_aceite_km": 1}) or {}
    return {
        "km": int(carro.get("ultimo_cambio_aceite_km", 0) or 0),
        "fecha": "",
        "pdf_path": "",
        "estado": "",
    }


def _estado_aceite_carros():
    """Para cada carro calcula el km actual, el ultimo cambio conocido y cuantos km faltan.

    Si no hay un cambio de aceite previo registrado y no hay kilometraje cargado, el carro se considera
    recien salido de agencia y no aparece como vencido.
    """
    carros = list(db.carros.find({}, projection={
        "_id": 1, "nombre": 1, "placa": 1, "km_cambio_intervalo": 1, "ultimo_cambio_aceite_km": 1,
    }))

    resultados = []
    for carro in carros:
        carro_id = str(carro.get("_id", ""))
        if not carro_id:
            continue
        try:
            intervalo = int(carro.get("km_cambio_intervalo", 0) or 0)
        except (TypeError, ValueError):
            continue
        if intervalo <= 0:
            continue

        km_actual = _obtener_km_actual_carro(carro_id)

        solicitud_pendiente = db.carros_aceite.find_one(
            {"carro_id": carro_id, "estado": "pendiente"},
            projection={"km": 1, "fecha": 1, "observacion": 1, "pdf_path": 1},
            sort=_orden_aceite(),
        )
        ultimo = db.carros_aceite.find_one(
            {"carro_id": carro_id, "estado": {"$ne": "pendiente"}},
            projection={"km": 1, "fecha": 1, "pdf_path": 1},
            sort=_orden_aceite(),
        )
        km_en_cambio_doc = ultimo["km"] if ultimo else carro.get("ultimo_cambio_aceite_km")
        try:
            km_en_cambio = int(km_en_cambio_doc or 0)
        except (TypeError, ValueError):
            km_en_cambio = 0

        fecha_ultimo = ultimo.get("fecha", "") if ultimo else ""

        if km_actual is None:
            if km_en_cambio_doc is None:
                continue
            km_recorridos = 0
            km_actual = km_en_cambio
        else:
            km_recorridos = max(km_actual - km_en_cambio, 0)

        km_restantes = max(intervalo - km_recorridos, 0)
        vencido = km_recorridos >= intervalo and not solicitud_pendiente

        resultados.append({
            "carro_id": carro_id,
            "carro_nombre": carro.get("nombre") or carro.get("placa") or carro_id,
            "intervalo": intervalo,
            "km_actual": km_actual,
            "ultimo_cambio_km": km_en_cambio,
            "ultimo_cambio_fecha": fecha_ultimo,
            "km_recorridos": km_recorridos,
            "km_restantes": km_restantes,
            "vencido": vencido,
            "pendiente_aprobacion": bool(solicitud_pendiente),
            "solicitud_aceite_km": int(solicitud_pendiente.get("km", 0) or 0) if solicitud_pendiente else None,
            "solicitud_aceite_fecha": solicitud_pendiente.get("fecha", "") if solicitud_pendiente else "",
            "solicitud_pdf_path": solicitud_pendiente.get("pdf_path", "") if solicitud_pendiente else "",
            "ultimo_pdf_path": ultimo.get("pdf_path", "") if ultimo else "",
        })
    return resultados


def _obtener_km_actual_carro(carro_id):
    """Devuelve el mayor km registrado en carros_kilometraje para este carro.

    Recorre todos los meses guardados y se queda con el valor maximo (no-cero) de la coleccion.
    Esto evita depender de que el ultimo mes tenga datos o de que los meses esten en orden.
    """
    pipeline = [
        {"$match": {"carro_id": carro_id}},
        {"$project": {"values": {"$objectToArray": "$days"}}},
        {"$unwind": "$values"},
        {"$match": {
            "values.v": {"$type": "number"},
            "values.v": {"$gt": 0},
        }},
        {"$group": {"_id": None, "max_km": {"$max": "$values.v"}}},
    ]
    try:
        resultado = list(db.carros_kilometraje.aggregate(pipeline))
    except Exception:
        resultado = []
    if resultado and resultado[0].get("max_km") is not None:
        try:
            return int(resultado[0]["max_km"])
        except (TypeError, ValueError):
            return None
    return None


def obtener_alertas_admin():
    """Calcula todas las alertas para el modo administrador."""
    herramientas = _trabajos_con_herramientas_pendientes()
    requerimientos = _requerimientos_reabastecimiento_pendientes()
    mantenimientos = _mantenimientos_maquinas_activos()
    aceite = _estado_aceite_carros()

    aceite_pendientes = [c for c in aceite if c.get("pendiente_aprobacion")]
    aceite_vencidos = [c for c in aceite if c["vencido"]]

    conteo = {
        "herramientas_pendientes": len(herramientas),
        "requerimientos_pendientes": len(requerimientos),
        "mantenimientos_activos": len(mantenimientos),
        "aceite_pendientes": len(aceite_pendientes),
        "aceite_vencidos": len(aceite_vencidos),
        "aceite_por_vencer": sum(1 for c in aceite if not c["vencido"] and c["km_restantes"] <= c["intervalo"] * 0.1),
    }
    return {
        "conteo": conteo,
        "herramientas": herramientas,
        "requerimientos": requerimientos,
        "mantenimientos": mantenimientos,
        "aceite": aceite,
        "aceite_pendientes": aceite_pendientes,
    }


# =========================================================
# CAMBIO DE ACEITE
# =========================================================

def _generar_pdf_cambio_aceite(carro_id, km, fecha, observacion, ultimo_km):
    import os
    from reportlab.pdfgen import canvas
    from ui.utils import (
        ruta_recurso,
        obtener_base_pdf,
        obtener_pdf_unico,
        limpiar_nombre_archivo,
        normalizar_ruta_relativa,
    )
    from io import BytesIO
    from reportlab.lib.utils import simpleSplit
    from pypdf import PdfReader, PdfWriter

    carro = db.carros.find_one({"_id": carro_id}) or {}
    placa = carro.get("placa") or carro.get("nombre") or carro_id
    descripcion = carro.get("descripcion", "")

    fecha_text = str(fecha)
    plantilla_pdf = ruta_recurso("ui/requerimiento/Cambio_aceite.pdf")
    carpeta_salida = os.path.join(obtener_base_pdf(), "requerimientos", "cambio_aceite")
    os.makedirs(carpeta_salida, exist_ok=True)
    salida_pdf = obtener_pdf_unico(carpeta_salida, f"Cambio_aceite_{limpiar_nombre_archivo(carro_id)}_{fecha_text}_{km}")

    if os.path.exists(plantilla_pdf):
        plantilla = PdfReader(plantilla_pdf)
        if len(plantilla.pages) == 0:
            raise Exception("La plantilla de Cambio_aceite.pdf no tiene paginas.")
        pagina_base = plantilla.pages[0]
        ancho = float(pagina_base.mediabox.width)
        alto = float(pagina_base.mediabox.height)

        def y_from_top(top):
            return alto - top - 4

        packet = BytesIO()
        c = canvas.Canvas(packet, pagesize=(ancho, alto))
        c.setFont("Helvetica", 11)

        c.drawString(145, y_from_top(204.524), str(placa))
        c.drawString(205, y_from_top(229.484), str(km))
        c.drawString(335, y_from_top(254.474), str(ultimo_km))
        c.drawString(318, y_from_top(279.434), fecha_text)

        obs_text = str(observacion or "").strip()
        if obs_text:
            c.drawString(85, y_from_top(410), "Observación:")
            y_obs = y_from_top(430)
            lineas = simpleSplit(obs_text, "Helvetica", 10, ancho - 110)
            for linea in lineas:
                c.drawString(90, y_obs, linea)
                y_obs -= 14
                if y_obs < 60:
                    c.showPage()
                    y_obs = alto - 60

        c.save()
        packet.seek(0)

        overlay = PdfReader(packet)
        writer = PdfWriter()
        pagina = plantilla.pages[0]
        pagina.merge_page(overlay.pages[0])
        writer.add_page(pagina)

        with open(salida_pdf, "wb") as f:
            writer.write(f)

        return normalizar_ruta_relativa(salida_pdf), ""

    from reportlab.lib.pagesizes import A4
    nombre_base = f"Cambio_aceite_{limpiar_nombre_archivo(carro_id)}_{fecha_text}_{km}"
    salida_pdf = obtener_pdf_unico(carpeta_salida, nombre_base)

    c = canvas.Canvas(salida_pdf, pagesize=A4)
    ancho, alto = A4
    margen_x = 50
    y = alto - 80
    c.setFont("Helvetica-Bold", 14)
    c.drawString(margen_x, y, "Cambio de Aceite - Aprobacion")
    y -= 30
    c.setFont("Helvetica", 10)
    c.drawString(margen_x, y, f"Fecha: {fecha_text}")
    y -= 18
    c.drawString(margen_x, y, f"Carro ID: {carro_id}")
    y -= 18
    if placa:
        c.drawString(margen_x, y, f"Placa / Nombre: {placa}")
        y -= 18
    if descripcion:
        c.drawString(margen_x, y, f"Descripcion: {descripcion}")
        y -= 18
    c.drawString(margen_x, y, f"Kilometraje registrado: {km} km")
    y -= 18
    c.drawString(margen_x, y, "Observacion:")
    y -= 14
    obs_text = str(observacion or "").strip()
    max_width = ancho - margen_x * 2
    lineas = simpleSplit(obs_text, "Helvetica", 10, max_width)
    for linea in lineas:
        c.drawString(margen_x + 10, y, linea)
        y -= 14
        if y < 60:
            c.showPage()
            y = alto - 60
    y -= 10
    c.setFont("Helvetica-Oblique", 9)
    c.drawString(margen_x, y, "Firma responsable: _________________________")
    c.showPage()
    c.save()

    return normalizar_ruta_relativa(salida_pdf), ""


def registrar_cambio_aceite(carro_id, km, fecha=None, observacion=""):
    """Crea una solicitud de cambio de aceite pendiente de aprobación administrativa."""
    carro_id = str(carro_id or "").strip()
    if not carro_id:
        return False, "Carro invalido."
    try:
        km = int(km)
    except (TypeError, ValueError):
        return False, "El kilometraje debe ser un numero entero."
    if km < 0:
        return False, "El kilometraje no puede ser negativo."

    fecha = fecha or fecha_hoy()
    pendiente = db.carros_aceite.find_one(
        {"carro_id": carro_id, "estado": "pendiente"},
        projection={"_id": 1},
        sort=[("fecha", -1)],
    )
    if pendiente:
        return False, "Ya existe una solicitud de cambio de aceite pendiente para este carro."

    ultimo = db.carros_aceite.find_one(
        {"carro_id": carro_id, "estado": {"$ne": "pendiente"}},
        projection={"km": 1},
        sort=_orden_aceite(),
    )
    if ultimo and km < int(ultimo.get("km", 0)):
        return False, f"El nuevo kilometraje ({km}) es menor al ultimo registrado ({ultimo['km']})."

    ultimo_doc = db.carros_aceite.find_one(
        {"carro_id": carro_id, "estado": {"$ne": "pendiente"}},
        projection={"km": 1, "fecha": 1},
        sort=[("created_at", -1), ("fecha", -1), ("_id", -1)],
    )
    ultimo_km = int(ultimo_doc.get("km", 0) or 0) if ultimo_doc else int(
        db.carros.find_one({"_id": carro_id}, projection={"ultimo_cambio_aceite_km": 1}).get("ultimo_cambio_aceite_km", 0) or 0
    )

    try:
        ruta_relativa, pdf_err = _generar_pdf_cambio_aceite(carro_id, km, fecha, observacion, ultimo_km)
    except Exception as e:
        ruta_relativa = ""
        pdf_err = str(e)

    registro = {
        "carro_id": carro_id,
        "km": km,
        "fecha": fecha,
        "observacion": observacion,
        "estado": "pendiente",
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    }
    if ruta_relativa:
        registro["pdf_path"] = ruta_relativa
    doc_id = db.carros_aceite.insert_one(registro).inserted_id

    mensaje = "Solicitud de cambio de aceite registrada correctamente. Pendiente de aprobación del administrador."
    if ruta_relativa:
        mensaje += f" PDF guardado en: {ruta_relativa}"
    else:
        mensaje += f" No se genero PDF: {pdf_err if pdf_err else 'error desconocido'}"
    return True, mensaje


def aceptar_cambio_aceite(solicitud_id, fecha=None):
    """Acepta una solicitud pendiente y deja el cambio de aceite como aplicado."""
    solicitud_id = str(solicitud_id or "").strip()
    if not solicitud_id:
        return False, "Solicitud invalida."

    try:
        solicitud_obj = ObjectId(solicitud_id)
    except Exception:
        solicitud_obj = solicitud_id

    solicitud = db.carros_aceite.find_one({"_id": solicitud_obj, "estado": "pendiente"})
    if not solicitud:
        return False, "No existe una solicitud pendiente para aceptar."

    carro_id = str(solicitud.get("carro_id") or "").strip()
    if not carro_id:
        return False, "Carro invalido."

    km = int(solicitud.get("km", 0) or 0)
    fecha = fecha or solicitud.get("fecha") or fecha_hoy()

    ultimo_doc = db.carros_aceite.find_one(
        {"carro_id": carro_id, "estado": {"$ne": "pendiente"}},
        projection={"km": 1, "fecha": 1},
        sort=[("created_at", -1), ("fecha", -1), ("_id", -1)],
    )
    ultimo_km = int(ultimo_doc.get("km", 0) or 0) if ultimo_doc else int(
        db.carros.find_one({"_id": carro_id}, projection={"ultimo_cambio_aceite_km": 1}).get("ultimo_cambio_aceite_km", 0) or 0
    )

    try:
        ruta_relativa, pdf_err = _generar_pdf_cambio_aceite(carro_id, km, fecha, solicitud.get("observacion", ""), ultimo_km)
    except Exception as e:
        ruta_relativa = ""
        pdf_err = str(e)

    update = {
        "$set": {
            "estado": "aceptado",
            "aprobado_en": fecha,
            "aprobado_por": "admin",
            "updated_at": datetime.now(),
        }
    }
    if ruta_relativa:
        update["$set"]["pdf_path"] = ruta_relativa

    db.carros_aceite.update_one({"_id": solicitud["_id"]}, update)
    db.carros.update_one(
        {"_id": carro_id},
        {"$set": {"ultimo_cambio_aceite_km": km, "ultimo_cambio_aceite_fecha": fecha}},
    )

    mensaje = "Cambio de aceite aceptado correctamente."
    if ruta_relativa:
        mensaje += f" PDF guardado en: {ruta_relativa}"
    else:
        mensaje += f" No se genero PDF: {pdf_err if pdf_err else 'error desconocido'}"
    return True, mensaje


def obtener_historial_aceite(carro_id):
    return list(db.carros_aceite.find({"carro_id": carro_id}).sort([("updated_at", -1), ("created_at", -1), ("fecha", -1), ("_id", -1)]))






