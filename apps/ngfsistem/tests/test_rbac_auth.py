"""AC-06 a AC-10: control de acceso por roles y autenticación."""

from __future__ import annotations

import jwt
import pytest

from conftest import PASSWORD, Entorno, cfg_pruebas
from ngfs import rbac
from ngfs.estados import TRANSICIONES, Estado, Rol


def test_ac06_matriz_coherente_con_transiciones() -> None:
    for t in TRANSICIONES:
        for rol in Rol:
            assert rbac.permitido(rol, t.desde, t.accion) == (rol in t.roles)
    # Auditor: solo lectura en todas las etapas
    assert all(rbac.MATRIZ[Rol.AUDITOR][e] == {rbac.VER} for e in Estado)
    # Nadie salvo Comité puede aprobar o rechazar
    assert [r for r in Rol if rbac.permitido(r, Estado.REVISION_CUMPLIMIENTO, "aprobar")] == [Rol.COMITE]


def test_ac06_api_respeta_matriz(env: Entorno) -> None:
    exp_id = env.crear_expediente()["id"]
    env.transicion(exp_id, "sol", "enviar")
    assert env.transicion(exp_id, "cum", "iniciar_revision").status_code == 403
    assert env.transicion(exp_id, "sol", "iniciar_revision").status_code == 403
    assert env.transicion(exp_id, "ana", "iniciar_revision").status_code == 200


def test_ac07_solicitante_solo_ve_lo_suyo(env: Entorno) -> None:
    exp_id = env.crear_expediente("sol")["id"]
    env.crear_expediente("sol2", "Otro proyecto")
    assert env.cliente.get(f"/expedientes/{exp_id}", headers=env.h("sol2")).status_code == 404
    assert [e["id"] for e in env.cliente.get("/expedientes", headers=env.h("sol")).json()] == [exp_id]
    # los borradores no son visibles para analistas
    assert env.cliente.get(f"/expedientes/{exp_id}", headers=env.h("ana")).status_code == 404
    env.transicion(exp_id, "sol", "enviar")
    assert env.cliente.get(f"/expedientes/{exp_id}", headers=env.h("ana")).status_code == 200


def test_ac08_auditor_solo_lectura(env: Entorno) -> None:
    exp_id = env.crear_expediente()["id"]
    h = env.h("aud")
    assert env.cliente.get(f"/expedientes/{exp_id}", headers=h).status_code == 200
    assert env.cliente.get("/auditoria", headers=h).status_code == 200
    assert env.cliente.patch(f"/expedientes/{exp_id}", json={"titulo": "Cambio"}, headers=h).status_code == 403
    assert env.cliente.post(f"/expedientes/{exp_id}/documentos", files={"archivo": ("a.txt", b"x")}, headers=h).status_code == 403
    assert env.transicion(exp_id, "aud", "enviar").status_code == 403
    nuevo = {"usuario": "intruso", "password": PASSWORD, "rol": "analista"}
    assert env.cliente.post("/usuarios", json=nuevo, headers=h).status_code == 403


def test_ac09_password_hasheada_con_bcrypt(env: Entorno) -> None:
    r = env.cliente.post("/usuarios", json={"usuario": "nuevo", "password": PASSWORD, "rol": "analista"}, headers=env.h("adm"))
    assert r.status_code == 201 and "password" not in r.text
    with env.sesion() as s:
        from ngfs.modelos import Usuario

        u = s.query(Usuario).filter_by(usuario="nuevo").one()
        assert u.password_hash.startswith("$2") and PASSWORD not in u.password_hash


def test_ac09_password_debil_rechazada(env: Entorno) -> None:
    for pw in ("corta1!", "soloLetrasLargas", "123456789012345"):
        r = env.cliente.post("/usuarios", json={"usuario": "debil", "password": pw, "rol": "analista"}, headers=env.h("adm"))
        assert r.status_code == 422


def test_ac09_autenticacion_obligatoria_y_tokens(env: Entorno) -> None:
    assert env.cliente.get("/expedientes").status_code == 401
    assert env.cliente.get("/expedientes", headers={"Authorization": "Bearer basura"}).status_code == 401
    assert env.login("sol", "incorrecta-123").status_code == 401
    assert env.login("no_existe").status_code == 401
    falso = jwt.encode({"sub": "1", "rol": "administrador", "exp": 9999999999}, "otro-secreto-" * 4, algorithm="HS256")
    assert env.cliente.get("/auth/yo", headers={"Authorization": f"Bearer {falso}"}).status_code == 401
    expirado = jwt.encode({"sub": "1", "rol": "solicitante", "exp": 1}, "x" * 40, algorithm="HS256")
    r = env.cliente.get("/auth/yo", headers={"Authorization": f"Bearer {expirado}"})
    assert r.status_code == 401 and "expirado" in r.json()["detail"]
    assert env.cliente.get("/auth/yo", headers=env.h("sol")).json()["rol"] == "solicitante"


def test_ac09_usuario_desactivado_pierde_acceso(env: Entorno) -> None:
    h = env.h("ana")
    with env.sesion() as s:
        from ngfs.modelos import Usuario

        ana_id = s.query(Usuario).filter_by(usuario="ana").one().id
    assert env.cliente.patch(f"/usuarios/{ana_id}", json={"activo": False}, headers=env.h("adm")).status_code == 200
    assert env.cliente.get("/auth/yo", headers=h).status_code == 401


def test_ac09_produccion_exige_secreto_fuerte() -> None:
    with pytest.raises(ValueError):
        cfg_pruebas(entorno="produccion", jwt_secreto="corto")
    assert cfg_pruebas(entorno="produccion", jwt_secreto="s" * 48).entorno == "produccion"


def test_ac10_bloqueo_por_intentos_fallidos(env: Entorno) -> None:
    for _ in range(3):  # max_intentos_login=3 en pruebas
        assert env.login("cum", "incorrecta-123").status_code == 401
    assert env.login("cum").status_code == 423  # bloqueada incluso con la contraseña correcta
    eventos = env.cliente.get("/auditoria", headers=env.h("aud")).json()
    assert sum(e["accion"] == "login_fallido" for e in eventos) == 3
