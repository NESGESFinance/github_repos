"""AC-01 a AC-05: expedientes, máquina de estados y decisión humana."""

from __future__ import annotations

from conftest import Entorno

JUST = "Justificación suficiente para la decisión."


def test_ac01_crear_expediente_en_borrador(env: Entorno) -> None:
    exp = env.crear_expediente()
    assert exp["estado"] == "borrador"
    assert exp["etapa"] == 1
    assert exp["codigo"].startswith("NGFS-")
    assert exp["monto_solicitado"] == "15000.50"


def test_ac01_solo_solicitante_crea(env: Entorno) -> None:
    for usuario in ("ana", "com", "aud", "adm"):
        r = env.cliente.post("/expedientes", json={"titulo": "Intento"}, headers=env.h(usuario))
        assert r.status_code == 403


def test_ac02_flujo_completo_ocho_etapas(env: Entorno) -> None:
    exp_id = env.crear_expediente()["id"]
    env.llevar_a_cumplimiento(exp_id)
    r = env.transicion(exp_id, "com", "aprobar", JUST, True)
    assert r.status_code == 200 and r.json()["estado"] == "aprobado"
    assert env.transicion(exp_id, "ana", "iniciar_ejecucion").json()["estado"] == "en_ejecucion"
    r = env.transicion(exp_id, "com", "cerrar", "Ejecución concluida y verificada.")
    assert r.json()["estado"] == "cerrado" and r.json()["etapa"] == 8
    hist = env.cliente.get(f"/expedientes/{exp_id}/historial", headers=env.h("aud")).json()
    assert [h["accion"] for h in hist] == ["enviar", "iniciar_revision", "aceptar_documentacion", "enviar_a_cumplimiento",
                                           "aprobar", "iniciar_ejecucion", "cerrar"]
    assert [h["decision_humana"] for h in hist].count(True) == 1


def test_ac02_rechazo_y_archivo(env: Entorno) -> None:
    exp_id = env.crear_expediente()["id"]
    env.llevar_a_cumplimiento(exp_id)
    assert env.transicion(exp_id, "com", "rechazar", JUST, True).json()["estado"] == "rechazado"
    assert env.transicion(exp_id, "adm", "archivar", "Archivo administrativo.").json()["estado"] == "cerrado"


def test_ac02_devolucion_para_subsanar(env: Entorno) -> None:
    exp_id = env.crear_expediente()["id"]
    env.transicion(exp_id, "sol", "enviar")
    env.transicion(exp_id, "ana", "iniciar_revision")
    assert env.transicion(exp_id, "ana", "devolver_a_solicitante").status_code == 422  # exige justificación
    assert env.transicion(exp_id, "ana", "devolver_a_solicitante", "Falta el estudio de impacto.").json()["estado"] == "borrador"


def test_ac03_transiciones_invalidas_rechazadas(env: Entorno) -> None:
    exp_id = env.crear_expediente()["id"]
    assert env.transicion(exp_id, "sol", "aprobar", JUST, True).status_code == 409  # salto de etapas
    assert env.transicion(exp_id, "sol", "accion_inexistente").status_code == 409
    env.transicion(exp_id, "sol", "enviar")
    assert env.transicion(exp_id, "sol", "enviar").status_code == 409  # repetida
    assert env.cliente.get(f"/expedientes/{exp_id}", headers=env.h("sol")).json()["estado"] == "enviado"


def test_ac03_estado_final_sin_salidas(env: Entorno) -> None:
    exp_id = env.crear_expediente()["id"]
    env.llevar_a_cumplimiento(exp_id)
    env.transicion(exp_id, "com", "rechazar", JUST, True)
    env.transicion(exp_id, "com", "archivar", "Archivo tras rechazo.")
    assert env.cliente.get(f"/expedientes/{exp_id}/transiciones-disponibles", headers=env.h("com")).json() == []


def test_ac04_decision_exige_confirmacion_humana_y_justificacion(env: Entorno) -> None:
    exp_id = env.crear_expediente()["id"]
    env.llevar_a_cumplimiento(exp_id)
    assert env.transicion(exp_id, "com", "aprobar", JUST, False).status_code == 422
    assert env.transicion(exp_id, "com", "aprobar", "", True).status_code == 422
    assert env.transicion(exp_id, "com", "rechazar", "corta", True).status_code == 422
    assert env.cliente.get(f"/expedientes/{exp_id}", headers=env.h("com")).json()["estado"] == "revision_cumplimiento"


def test_ac05_solo_comite_decide(env: Entorno) -> None:
    exp_id = env.crear_expediente()["id"]
    env.llevar_a_cumplimiento(exp_id)
    for usuario in ("ana", "cum", "aud", "adm"):
        assert env.transicion(exp_id, usuario, "aprobar", JUST, True).status_code == 403


def test_ac05_segregacion_de_funciones(env: Entorno) -> None:
    """Un usuario que presentó el expediente no puede decidirlo aunque luego reciba el rol de Comité."""
    exp_id = env.crear_expediente()["id"]
    env.llevar_a_cumplimiento(exp_id)
    with env.sesion() as s:
        from ngfs.modelos import Usuario

        sol_id = s.query(Usuario).filter_by(usuario="sol").one().id
    r = env.cliente.patch(f"/usuarios/{sol_id}", json={"rol": "comite"}, headers=env.h("adm"))
    assert r.status_code == 200
    # el token antiguo queda invalidado por el cambio de rol
    assert env.cliente.get("/auth/yo", headers=env.h("sol")).status_code == 401
    env._cabeceras.pop("sol")
    assert env.transicion(exp_id, "sol", "aprobar", JUST, True).status_code == 403


def test_editar_solo_en_borrador(env: Entorno) -> None:
    exp_id = env.crear_expediente()["id"]
    r = env.cliente.patch(f"/expedientes/{exp_id}", json={"titulo": "Título actualizado"}, headers=env.h("sol"))
    assert r.status_code == 200 and r.json()["titulo"] == "Título actualizado"
    env.transicion(exp_id, "sol", "enviar")
    assert env.cliente.patch(f"/expedientes/{exp_id}", json={"titulo": "Otro"}, headers=env.h("sol")).status_code == 403
