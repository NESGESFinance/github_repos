"""Expedientes: CRUD básico, máquina de estados, documentos y análisis consultivo UASI."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy import select

from ngfs import rbac
from ngfs.api.dependencias import CfgDep, ClaimsDep, SesionDep, UsuarioDep, cargar_expediente, exigir_global, obtener_uasi
from ngfs.auditoria import registrar_evento
from ngfs.esquemas import (
    AnalisisSalida,
    DocumentoSalida,
    ExpedienteCrear,
    ExpedienteEditar,
    ExpedienteSalida,
    HistorialSalida,
    SolicitudTransicion,
    TransicionDisponible,
    VerificacionDocumento,
)
from ngfs.estados import ETAPAS, Estado, Rol, TransicionInvalida, buscar_transicion, transiciones_desde
from ngfs.modelos import AnalisisConsultivo, Documento, Expediente, HistorialTransicion
from ngfs.uasi_adaptador import AdaptadorUASI

router = APIRouter(tags=["expedientes"])
_TROZO = 1024 * 1024


def a_salida(exp: Expediente) -> ExpedienteSalida:
    etapa, nombre = ETAPAS[Estado(exp.estado)]
    return ExpedienteSalida(
        id=exp.id, codigo=exp.codigo, titulo=exp.titulo, descripcion=exp.descripcion,
        monto_solicitado=exp.monto_solicitado, moneda=exp.moneda, estado=exp.estado, etapa=etapa,
        etapa_nombre=nombre, solicitante_id=exp.solicitante_id, creado_en=exp.creado_en, actualizado_en=exp.actualizado_en,
    )


@router.post("/expedientes", response_model=ExpedienteSalida, status_code=201)
def crear_expediente(datos: ExpedienteCrear, usuario: UsuarioDep, sesion: SesionDep) -> ExpedienteSalida:
    exigir_global(usuario, rbac.CREAR_EXPEDIENTE)
    exp = Expediente(codigo=f"TMP-{uuid4().hex[:16]}", titulo=datos.titulo, descripcion=datos.descripcion,
                     monto_solicitado=datos.monto_solicitado, moneda=datos.moneda,
                     estado=Estado.BORRADOR.value, solicitante_id=usuario.id)
    sesion.add(exp)
    sesion.flush()
    exp.codigo = f"NGFS-{datetime.now(UTC).year}-{exp.id:05d}"
    registrar_evento(sesion, actor=usuario, accion="expediente_creado", entidad_tipo="expediente", entidad_id=exp.id,
                     datos={"codigo": exp.codigo, "titulo": exp.titulo, "estado": exp.estado})
    sesion.commit()
    return a_salida(exp)


@router.get("/expedientes", response_model=list[ExpedienteSalida])
def listar_expedientes(usuario: UsuarioDep, sesion: SesionDep, estado: Estado | None = None) -> list[ExpedienteSalida]:
    rol = Rol(usuario.rol)
    visibles = [e.value for e in Estado if rbac.permitido(rol, e, rbac.VER)]
    consulta = select(Expediente).where(Expediente.estado.in_(visibles)).order_by(Expediente.id)
    if rol == Rol.SOLICITANTE:
        consulta = consulta.where(Expediente.solicitante_id == usuario.id)
    if estado is not None:
        consulta = consulta.where(Expediente.estado == estado.value)
    return [a_salida(e) for e in sesion.execute(consulta).scalars()]


@router.get("/expedientes/{expediente_id}", response_model=ExpedienteSalida)
def ver_expediente(expediente_id: int, usuario: UsuarioDep, sesion: SesionDep) -> ExpedienteSalida:
    return a_salida(cargar_expediente(sesion, usuario, expediente_id))


@router.patch("/expedientes/{expediente_id}", response_model=ExpedienteSalida)
def editar_expediente(expediente_id: int, datos: ExpedienteEditar, usuario: UsuarioDep, sesion: SesionDep) -> ExpedienteSalida:
    exp = cargar_expediente(sesion, usuario, expediente_id, rbac.EDITAR)
    cambios = datos.model_dump(exclude_unset=True, exclude_none=True)
    for campo, valor in cambios.items():
        setattr(exp, campo, valor)
    if cambios:
        registrar_evento(sesion, actor=usuario, accion="expediente_editado", entidad_tipo="expediente",
                         entidad_id=exp.id, datos={k: str(v) for k, v in cambios.items()})
    sesion.commit()
    return a_salida(exp)


@router.get("/expedientes/{expediente_id}/transiciones-disponibles", response_model=list[TransicionDisponible])
def transiciones_disponibles(expediente_id: int, usuario: UsuarioDep, sesion: SesionDep) -> list[TransicionDisponible]:
    exp = cargar_expediente(sesion, usuario, expediente_id)
    rol = Rol(usuario.rol)
    return [
        TransicionDisponible(accion=t.accion, hacia=t.hacia.value, decision_humana=t.decision_humana,
                             requiere_justificacion=t.requiere_justificacion, descripcion=t.descripcion)
        for t in transiciones_desde(Estado(exp.estado)) if rol in t.roles
    ]


@router.post("/expedientes/{expediente_id}/transiciones", response_model=ExpedienteSalida)
def ejecutar_transicion(
    expediente_id: int, solicitud: SolicitudTransicion, usuario: UsuarioDep, claims: ClaimsDep, sesion: SesionDep
) -> ExpedienteSalida:
    exp = cargar_expediente(sesion, usuario, expediente_id)
    estado_actual = Estado(exp.estado)
    try:
        t = buscar_transicion(estado_actual, solicitud.accion)
    except TransicionInvalida as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    if not rbac.permitido(Rol(usuario.rol), estado_actual, t.accion):
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            f"El rol '{usuario.rol}' no puede ejecutar '{t.accion}' en la etapa '{estado_actual.value}'.")
    justificacion = solicitud.justificacion.strip()
    if t.requiere_justificacion and len(justificacion) < 10:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                            "Esta transición exige una justificación de al menos 10 caracteres.")
    if t.decision_humana:
        if claims.get("tipo") != "humano" or not solicitud.confirmacion_humana:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                                "Las decisiones exigen confirmación humana explícita (confirmacion_humana=true).")
        if exp.solicitante_id == usuario.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN,
                                "Segregación de funciones: no puede decidir sobre un expediente que usted mismo presentó.")
    exp.estado = t.hacia.value
    sesion.add(HistorialTransicion(expediente_id=exp.id, accion=t.accion, desde=t.desde.value, hacia=t.hacia.value,
                                   actor_id=usuario.id, justificacion=justificacion, decision_humana=t.decision_humana))
    registrar_evento(sesion, actor=usuario, accion="transicion", entidad_tipo="expediente", entidad_id=exp.id,
                     datos={"accion": t.accion, "desde": t.desde.value, "hacia": t.hacia.value,
                            "justificacion": justificacion, "decision_humana": t.decision_humana})
    sesion.commit()
    return a_salida(exp)


@router.get("/expedientes/{expediente_id}/historial", response_model=list[HistorialSalida])
def historial(expediente_id: int, usuario: UsuarioDep, sesion: SesionDep) -> list[HistorialTransicion]:
    exp = cargar_expediente(sesion, usuario, expediente_id)
    consulta = select(HistorialTransicion).where(HistorialTransicion.expediente_id == exp.id).order_by(HistorialTransicion.id)
    return list(sesion.execute(consulta).scalars())


def _hash_archivo(archivo: UploadFile, limite_bytes: int) -> tuple[str, int]:
    h = hashlib.sha256()
    total = 0
    while trozo := archivo.file.read(_TROZO):
        total += len(trozo)
        if total > limite_bytes:
            raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "El documento supera el tamaño máximo permitido.")
        h.update(trozo)
    return h.hexdigest(), total


@router.post("/expedientes/{expediente_id}/documentos", response_model=DocumentoSalida, status_code=201)
def adjuntar_documento(expediente_id: int, archivo: UploadFile, usuario: UsuarioDep, sesion: SesionDep, cfg: CfgDep) -> Documento:
    exp = cargar_expediente(sesion, usuario, expediente_id, rbac.ADJUNTAR)
    sha, tamano = _hash_archivo(archivo, cfg.max_tamano_documento_mb * 1024 * 1024)
    doc = Documento(expediente_id=exp.id, nombre=(archivo.filename or "sin_nombre")[:255],
                    tipo_mime=(archivo.content_type or "application/octet-stream")[:128], tamano_bytes=tamano,
                    sha256=sha, subido_por_id=usuario.id, etapa=exp.estado)
    sesion.add(doc)
    sesion.flush()
    registrar_evento(sesion, actor=usuario, accion="documento_registrado", entidad_tipo="documento", entidad_id=doc.id,
                     datos={"expediente_id": exp.id, "nombre": doc.nombre, "sha256": sha, "tamano_bytes": tamano})
    sesion.commit()
    return doc


@router.get("/expedientes/{expediente_id}/documentos", response_model=list[DocumentoSalida])
def listar_documentos(expediente_id: int, usuario: UsuarioDep, sesion: SesionDep) -> list[Documento]:
    exp = cargar_expediente(sesion, usuario, expediente_id)
    return list(sesion.execute(select(Documento).where(Documento.expediente_id == exp.id).order_by(Documento.id)).scalars())


@router.post("/documentos/{documento_id}/verificar", response_model=VerificacionDocumento)
def verificar_documento(documento_id: int, archivo: UploadFile, usuario: UsuarioDep, sesion: SesionDep,
                        cfg: CfgDep) -> VerificacionDocumento:
    doc = sesion.get(Documento, documento_id)
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Documento no encontrado.")
    cargar_expediente(sesion, usuario, doc.expediente_id)
    sha, _ = _hash_archivo(archivo, cfg.max_tamano_documento_mb * 1024 * 1024)
    return VerificacionDocumento(documento_id=doc.id, coincide=sha == doc.sha256,
                                 sha256_registrado=doc.sha256, sha256_recibido=sha)


@router.post("/expedientes/{expediente_id}/analisis-uasi", response_model=AnalisisSalida, status_code=201, tags=["uasi"])
def solicitar_analisis_uasi(expediente_id: int, usuario: UsuarioDep, sesion: SesionDep,
                            uasi: Annotated[AdaptadorUASI, Depends(obtener_uasi)]) -> AnalisisConsultivo:
    exp = cargar_expediente(sesion, usuario, expediente_id, rbac.CONSULTAR_UASI)
    docs = sesion.execute(select(Documento.sha256).where(Documento.expediente_id == exp.id)).scalars().all()
    resumen: dict[str, Any] = {"codigo": exp.codigo, "titulo": exp.titulo, "descripcion": exp.descripcion,
                               "monto_solicitado": str(exp.monto_solicitado) if exp.monto_solicitado is not None else None,
                               "moneda": exp.moneda, "estado": exp.estado, "documentos_sha256": list(docs)}
    estado_previo = exp.estado
    resultado = uasi.analizar(resumen)
    if exp.estado != estado_previo:  # salvaguarda: el adaptador nunca puede alterar estados
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Violación de aislamiento del adaptador UASI.")
    analisis = AnalisisConsultivo(expediente_id=exp.id, solicitado_por_id=usuario.id, disponible=resultado.disponible,
                                  resultado=resultado.como_dict())
    sesion.add(analisis)
    sesion.flush()
    registrar_evento(sesion, actor=usuario, accion="uasi_consulta", entidad_tipo="expediente", entidad_id=exp.id,
                     datos={"analisis_id": analisis.id, "disponible": resultado.disponible, "motivo": resultado.motivo})
    sesion.commit()
    return analisis


@router.get("/expedientes/{expediente_id}/analisis-uasi", response_model=list[AnalisisSalida], tags=["uasi"])
def listar_analisis(expediente_id: int, usuario: UsuarioDep, sesion: SesionDep) -> list[AnalisisConsultivo]:
    exp = cargar_expediente(sesion, usuario, expediente_id)
    consulta = select(AnalisisConsultivo).where(AnalisisConsultivo.expediente_id == exp.id).order_by(AnalisisConsultivo.id)
    return list(sesion.execute(consulta).scalars())
