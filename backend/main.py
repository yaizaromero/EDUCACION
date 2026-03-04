# backend/main.py
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import hashlib
import time
import json
import os
from datetime import datetime
from backend.db import get_user_error_progress
import backend.model as model
from backend.metrics import compute_metrics, word_levenshtein_count
from backend.utils import (
    extract_text_from_pdf, 
    split_into_sentences, 
    posible_tu_impersonal, 
    corregir_y_extraer_errores,
    contar_palabras_susceptibles,
   
)

from backend.db import (
    init_db, user_exists, create_user, get_user_id,
    record_usage, create_document, insert_metric,
    get_user_overview, get_user_documents, get_document_metrics,
    sanitize_username, delete_document, record_login_ts,
    close_open_session, get_user_weekly_activity,
    agregar_palabras_bolsa, obtener_palabras_repaso, 
    registrar_acierto_palabra,
    actualizar_niveles_usuario,
    get_niveles_usuario,
    check_and_award_badges, 
    get_user_badges,
    update_user_streak, get_user_profile, update_user_avatar,
    get_all_students_info, get_class_overview_metrics,
    set_user_feedback,
    save_gym_result, get_admin_gym_stats
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
    try:
        username = sanitize_username(username)
        if user_exists(username):
            raise HTTPException(status_code=409, detail="El usuario ya existe. Elige otro nombre.")
        uid = create_user(username)
        record_usage(uid, "login", None)
        record_login_ts(uid, time.time())
        update_user_streak(uid)
        return {"ok": True, "user_id": uid, "username": username}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/users/login")
def user_login(username: str = Form(...)):
    try:
        username = sanitize_username(username)
        
        # 🔑 PASE VIP PARA EL PROFESOR: Si es admin y no existe, se crea en la sombra
        if username == "admin":
            if not user_exists("admin"):
                create_user("admin")
                
        uid = get_user_id(username)
        if uid is None:
            raise HTTPException(status_code=404, detail="La cuenta no existe. Crea una nueva.")
            
        record_usage(uid, "login", None)
        record_login_ts(uid, time.time())
        update_user_streak(uid)
        return {"ok": True, "user_id": uid, "username": username}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/users/logout")
def user_logout(username: str = Form(...)):
    try:
        username = sanitize_username(username)
        uid = get_user_id(username)
        if uid is None:
            raise HTTPException(status_code=404, detail="Usuario no válido.")
        close_open_session(uid, time.time())
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/users/heartbeat")
def user_heartbeat(username: str = Form(...)):
    try:
        username = sanitize_username(username)
        uid = get_user_id(username)
        if uid is None:
            raise HTTPException(status_code=404, detail="Usuario no válido.")
        now = time.time()
        record_usage(uid, "heartbeat", now)
        close_open_session(uid, now_epoch=now, idle_secs=1800)
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ============================================================
# LÓGICA DE PROCESAMIENTO UNIFICADA
# ============================================================

def procesar_analisis_completo(original_text, uid, filename, mode="ortografia"):
    # 0) Guardas de seguridad
    original_text = original_text or ""
    if not original_text.strip():
        raise HTTPException(status_code=400, detail="Texto vacío.")

    # ------------------------------------------------------------
    # 1) CORRECCIÓN (1 sola vez) + EXTRACCIÓN DE ERRORES (determinista)
    # ------------------------------------------------------------
    # OJO: corregir_y_extraer_errores YA hace: correct_full_text(mode) + diff para listas
    corrected_text, errores_extraidos = corregir_y_extraer_errores(original_text, mode=mode)

    # Susceptibles se calculan siempre sobre el texto corregido (mejor baseline)
    susceptibles = contar_palabras_susceptibles(corrected_text)

    # ------------------------------------------------------------
    # 2) FEEDBACK (según modo)
    # ------------------------------------------------------------
    if mode == "ortografia":
        # ✅ Feedback robusto: determinista + (opcional) redacción con LLM a partir de JSON
        # Esto evita que el LLM "invente" cambios o reglas.
        feedback = model.feedback_orthography(original_text, corrected_text, use_llm=True)
    else:
        # ✅ Tú impersonal: feedback como lo tenías (explica cambios entre original/corregido)
        feedback = model.generate_feedback(original_text, corrected_text, mode=mode)

    # ------------------------------------------------------------
    # 3) DETECCIÓN DE TÚ IMPERSONAL (solo para métricas; no cambia texto aquí)
    # ------------------------------------------------------------
    errores_posibles, _ = posible_tu_impersonal(original_text)
    num_tu = len(errores_posibles) if isinstance(errores_posibles, list) else 0

    # ------------------------------------------------------------
    # 4) MÉTRICAS GENERALES
    # ------------------------------------------------------------
    sentences = split_into_sentences(original_text)
    total_frases = len(sentences)

    cambios_modelo = word_levenshtein_count(original_text, corrected_text)

    # ------------------------------------------------------------
    # 5) GUARDADO EN BD + BOLSA DE PALABRAS
    # ------------------------------------------------------------
    text_hash = hashlib.sha256(original_text.encode("utf-8")).hexdigest()
    doc_id = create_document(uid, filename, text_hash)

    agregar_palabras_bolsa(uid, errores_extraidos)

    metrics_to_save = {
        "total_frases": total_frases,
        "frases_con_tu_impersonal": num_tu,

        "errores_b_v": len(errores_extraidos.get("B_V", [])),
        "susceptibles_b_v": susceptibles.get("B_V", 0),

        "errores_g_j": len(errores_extraidos.get("G_J", [])),
        "susceptibles_g_j": susceptibles.get("G_J", 0),

        "errores_y_ll": len(errores_extraidos.get("Y_LL", [])),
        "susceptibles_y_ll": susceptibles.get("Y_LL", 0),

        "errores_h": len(errores_extraidos.get("H", [])),
        "susceptibles_h": susceptibles.get("H", 0),

        # ✅ preparado para cuando añadas C_Z en extraer_listas_errores
        "errores_c_z": len(errores_extraidos.get("C_Z", [])),
        "susceptibles_c_z": susceptibles.get("C_Z", 0),

        "errores_tildes": len(errores_extraidos.get("TILDES", [])),
        "susceptibles_tildes": susceptibles.get("TILDES", 0),

        "errores_otros": len(errores_extraidos.get("OTROS", [])),
        "susceptibles_otros": susceptibles.get("OTROS", 0),

        "cambios_propuestos_modelo": cambios_modelo,
        "cambios_realizados_usuario": cambios_modelo,
    }

    for name, value in metrics_to_save.items():
        insert_metric(doc_id, name, float(value))

    actualizar_niveles_usuario(uid, limit=15)
    check_and_award_badges(uid)

    return {
        "doc_id": doc_id,
        "original_text": original_text,
        "corrected": corrected_text,
        "feedback": feedback,
        "errores_posibles": errores_posibles,
        "metricas": metrics_to_save,
        "listas_errores": errores_extraidos,
    }
@app.post("/process/")
async def process_pdf(file: UploadFile = File(...), username: str = Form(...), mode: str = Form("ortografia")):
    username = sanitize_username(username)
    uid = get_user_id(username)
    if uid is None:
        raise HTTPException(status_code=403, detail="Usuario no válido.")
    content = await file.read()
    text = extract_text_from_pdf(content)
    record_usage(uid, "pdf_uploaded", None)
    return procesar_analisis_completo(text, uid, file.filename, mode)

@app.post("/process_text/")
async def process_text(username: str = Form(...), text: str = Form(...), mode: str = Form("ortografia"), filename: str = Form(None)):
    username = sanitize_username(username)
    uid = get_user_id(username)
    if uid is None:
        raise HTTPException(status_code=403, detail="Usuario no válido.")
    record_usage(uid, "text_uploaded", None)
    return procesar_analisis_completo(text, uid, filename or "texto_manual.txt", mode)

# ============================================================
# GESTIÓN DE DOCUMENTOS
# ============================================================

@app.post("/documents/{doc_id}/user_changes")
def update_user_changes(doc_id: int, changes: int = Form(...)):
    try:
        insert_metric(doc_id, "cambios_realizados_usuario", float(changes))
        return {"ok": True}
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
    if not delete_document(doc_id):
        raise HTTPException(status_code=404, detail="Documento no encontrado.")
    return {"ok": True, "deleted_id": doc_id}

@app.get("/users/{username}/ejercicios")
def obtener_ejercicios(username: str):
    """Devuelve la bolsa de palabras pendientes del usuario."""
    username = sanitize_username(username)
    palabras = obtener_palabras_repaso(username)
    return {"ok": True, "palabras_pendientes": len(palabras), "ejercicios": palabras}

@app.post("/ejercicios/{palabra_id}/acierto")
def registrar_acierto(palabra_id: int):
    """El frontend llama aquí cuando el usuario acierta la palabra en el ejercicio."""
    try:
        registrar_acierto_palabra(palabra_id)
        return {"ok": True, "mensaje": "Acierto registrado"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@app.get("/users/{username}/progress")
def user_error_progress(username: str):
    # Trae un histórico de tamaño 15 (ventana deslizante)
    return {"username": username, "progress": get_user_error_progress(username, limit=15)}

@app.get("/users/{username}/levels")
def user_levels_endpoint(username: str):
    try:
        username = sanitize_username(username)
        niveles = get_niveles_usuario(username)
        if not niveles:
            return {"ok": True, "niveles": {}}
        return {"ok": True, "niveles": niveles}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@app.get("/users/{username}/badges")
def user_badges_endpoint(username: str):
    try:
        username = sanitize_username(username)
        badges = get_user_badges(username)
        return {"ok": True, "badges": badges}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@app.get("/users/{username}/profile")
def user_profile_endpoint(username: str):
    username = sanitize_username(username)
    return {"ok": True, "profile": get_user_profile(username)}

@app.post("/users/{username}/avatar")
def user_avatar_endpoint(username: str, avatar: str = Form(...)):
    username = sanitize_username(username)
    update_user_avatar(username, avatar)
    return {"ok": True}

# ============================================================
# PANEL DE CONTROL DEL PROFESOR (ADMIN)
# ============================================================

@app.get("/admin/students")
def admin_students():
    try:
        return {"ok": True, "students": get_all_students_info()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/admin/metrics")
def admin_metrics():
    try:
        return {"ok": True, "metrics": get_class_overview_metrics()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@app.post("/admin/students/{username}/feedback")
def set_feedback_endpoint(username: str, sticker: str = Form(...)):
    try:
        username = sanitize_username(username)
        set_user_feedback(username, sticker)
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@app.post("/users/{username}/gym_result")
def api_save_gym_result(username: str, categoria: str = Form(...), nivel: str = Form(...), score: int = Form(...), total: int = Form(...)):
    save_gym_result(username, categoria, nivel, score, total)
    return {"ok": True}

@app.get("/admin/gym_stats")
def api_admin_gym_stats():
    return {"ok": True, "stats": get_admin_gym_stats()}