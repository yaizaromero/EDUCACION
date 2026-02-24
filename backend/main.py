# backend/main.py

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import hashlib
import time

import backend.model as model
from backend.metrics import compute_metrics
from backend.utils import extract_text_from_pdf, split_into_sentences, posible_tu_impersonal
from backend.db import (
    init_db, user_exists, create_user, get_user_id,
    record_usage, create_document, insert_metric,
    get_user_overview, get_user_documents, get_document_metrics,
    sanitize_username, delete_document, record_login_ts,
    close_open_session, get_user_weekly_activity
)

app = FastAPI(title="PALABRIA Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()


@app.get("/status/")
def check_status():
    return {
        "modelo_listo": model.MODEL_LOADED,
        "progress": model.LOAD_PROGRESS,
        "message": model.LOAD_MESSAGE,
    }


@app.post("/load/")
def trigger_load():
    model.ensure_model_loaded(async_load=True)
    return {"ok": True}


@app.post("/users/create")
def user_create(username: str = Form(...)):
    username = sanitize_username(username)
    if user_exists(username):
        raise HTTPException(status_code=409, detail="El usuario ya existe.")
    uid = create_user(username)
    record_usage(uid, "login", None)
    record_login_ts(uid, time.time())
    return {"ok": True, "user_id": uid, "username": username}


@app.post("/users/login")
def user_login(username: str = Form(...)):
    username = sanitize_username(username)
    uid = get_user_id(username)
    if uid is None:
        raise HTTPException(status_code=404, detail="La cuenta no existe.")
    record_usage(uid, "login", None)
    record_login_ts(uid, time.time())
    return {"ok": True, "user_id": uid, "username": username}


@app.post("/users/logout")
def user_logout(username: str = Form(...)):
    username = sanitize_username(username)
    uid = get_user_id(username)
    if uid is None:
        raise HTTPException(status_code=404, detail="Usuario no válido.")
    close_open_session(uid, time.time())
    return {"ok": True}


# ============================================================
# PROCESAR TEXTO MANUAL
# ============================================================

@app.post("/process_text/")
async def process_text(
    username: str = Form(...),
    text: str = Form(...),
    mode: str = Form("ortografia"),  # "ortografia" o "tu_impersonal"
    filename: str = Form(None),
):
    username = sanitize_username(username)
    uid = get_user_id(username)
    if uid is None:
        raise HTTPException(status_code=403, detail="Usuario no válido.")

    original_text = text or ""

    # 1. Llamada al modelo pasando el modo elegido ("ortografia" o "tu_impersonal")
    corrected_text = model.correct_full_text(original_text, mode=mode)
    
    # 2. Generar feedback basado en los cambios realizados
    feedback = model.generate_feedback(original_text, corrected_text)

    # 3. Métricas y detección de candidatos a tú impersonal
    metrics = compute_metrics(original_text, corrected_text)
    errores_posibles, _ = posible_tu_impersonal(original_text)
    if not isinstance(errores_posibles, list):
        errores_posibles = []

    # Generar hash y guardar documento
    text_hash = hashlib.sha256(original_text.encode("utf-8")).hexdigest()
    doc_id = create_document(uid, filename or "entrada_texto.txt", text_hash)

    # Guardar métricas en BD
    insert_metric(doc_id, "total_frases", float(metrics["total_sentences"]))
    insert_metric(doc_id, "frases_con_tu_impersonal", float(len(errores_posibles)))
    insert_metric(doc_id, "errores_b_v", float(metrics["errors_bv"]))
    insert_metric(doc_id, "errores_g_j", float(metrics["errors_gj"]))
    insert_metric(doc_id, "errores_y_ll", float(metrics["errors_yll"]))
    insert_metric(doc_id, "errores_h", float(metrics["errors_h"]))
    insert_metric(doc_id, "errores_tildes", float(metrics["errors_tildes"]))
    insert_metric(doc_id, "cambios_propuestos_modelo", float(metrics["changes_proposed_model"]))
    insert_metric(doc_id, "cambios_realizados_usuario", float(metrics["changes_done_user"]))

    record_usage(uid, "text_uploaded", None)

    return {
        "doc_id": doc_id,
        "mode_used": mode,
        "original_text": original_text,
        "corrected": corrected_text,
        "feedback": feedback,
        "errores_posibles": errores_posibles,
        "mensaje_errores": (
            "No se detectaron errores de 'tú' impersonal."
            if not errores_posibles
            else f"Se detectaron {len(errores_posibles)} posibles usos del 'tú' impersonal."
        ),
        "metricas": {
            "total_frases": metrics["total_sentences"],
            "frases_con_tu_impersonal": len(errores_posibles),
            "errores_b_v": metrics["errors_bv"],
            "errores_g_j": metrics["errors_gj"],
            "errores_y_ll": metrics["errors_yll"],
            "errores_h": metrics["errors_h"],
            "errores_tildes": metrics["errors_tildes"],
            "cambios_propuestos_modelo": metrics["changes_proposed_model"],
            "cambios_realizados_usuario": metrics["changes_done_user"],
        },
    }


# ============================================================
# PROCESAR PDF
# ============================================================

@app.post("/process/")
async def process_pdf(
    file: UploadFile = File(...),
    username: str = Form(...),
    mode: str = Form("ortografia"),  # Añadido selector de modo para PDF
):
    username = sanitize_username(username)
    uid = get_user_id(username)
    if uid is None:
        raise HTTPException(status_code=403, detail="Usuario no válido.")

    content = await file.read()
    original_text = extract_text_from_pdf(content)

    # 1. Llamada al modelo pasando el modo elegido
    corrected_text = model.correct_full_text(original_text, mode=mode)
    
    # 2. Feedback
    feedback = model.generate_feedback(original_text, corrected_text)

    # 3. Métricas
    metrics = compute_metrics(original_text, corrected_text)
    errores_posibles, _ = posible_tu_impersonal(original_text)
    if not isinstance(errores_posibles, list):
        errores_posibles = []

    # Registro en base de datos
    text_hash = hashlib.sha256(original_text.encode("utf-8")).hexdigest()
    doc_id = create_document(uid, file.filename, text_hash)

    insert_metric(doc_id, "total_frases", float(metrics["total_sentences"]))
    insert_metric(doc_id, "frases_con_tu_impersonal", float(len(errores_posibles)))
    insert_metric(doc_id, "errores_b_v", float(metrics["errors_bv"]))
    insert_metric(doc_id, "errores_g_j", float(metrics["errors_gj"]))
    insert_metric(doc_id, "errores_y_ll", float(metrics["errors_yll"]))
    insert_metric(doc_id, "errores_h", float(metrics["errors_h"]))
    insert_metric(doc_id, "errores_tildes", float(metrics["errors_tildes"]))
    insert_metric(doc_id, "cambios_propuestos_modelo", float(metrics["changes_proposed_model"]))
    insert_metric(doc_id, "cambios_realizados_usuario", float(metrics["changes_done_user"]))

    record_usage(uid, "pdf_uploaded", None)

    return {
        "doc_id": doc_id,
        "mode_used": mode,
        "original_text": original_text,
        "corrected": corrected_text,
        "feedback": feedback,
        "errores_posibles": errores_posibles,
        "mensaje_errores": (
            "No se detectaron errores de 'tú' impersonal."
            if not errores_posibles
            else f"Se detectaron {len(errores_posibles)} posibles usos del 'tú' impersonal."
        ),
        "metricas": {
            "total_frases": metrics["total_sentences"],
            "frases_con_tu_impersonal": len(errores_posibles),
            "errores_b_v": metrics["errors_bv"],
            "errores_g_j": metrics["errors_gj"],
            "errores_y_ll": metrics["errors_yll"],
            "errores_h": metrics["errors_h"],
            "errores_tildes": metrics["errors_tildes"],
            "cambios_propuestos_modelo": metrics["changes_proposed_model"],
            "cambios_realizados_usuario": metrics["changes_done_user"],
        },
    }

# ============================================================
# GESTIÓN DE DOCUMENTOS Y MÉTRICAS RESTANTES
# ============================================================

@app.post("/documents/{doc_id}/metrics")
def add_document_metric(doc_id: int, name: str = Form(...), value: float = Form(...)):
    try:
        insert_metric(doc_id, name, float(value))
        return {"ok": True, "document_id": doc_id, "metric_name": name, "metric_value": float(value)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/documents/{doc_id}/user_changes")
def update_user_changes(doc_id: int, changes: int = Form(...)):
    try:
        insert_metric(doc_id, "cambios_realizados_usuario", float(changes))
        return {"ok": True, "document_id": doc_id, "metric_name": "cambios_realizados_usuario", "metric_value": float(changes)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/users/{username}/overview")
def user_overview(username: str):
    return get_user_overview(username)

@app.get("/users/{username}/documents")
def user_documents(username: str):
    return {"documents": get_user_documents(username)}

@app.get("/documents/{doc_id}/metrics")
def document_metrics(doc_id: int):
    return {"doc_id": doc_id, "metrics": get_document_metrics(doc_id)}

@app.get("/users/{username}/weekly_activity")
def user_weekly_activity(username: str):
    return {"username": username, "activity": get_user_weekly_activity(username)}

@app.delete("/documents/{doc_id}")
def delete_doc(doc_id: int):
    ok = delete_document(doc_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Documento no encontrado.")
    return {"ok": True, "deleted_id": doc_id}