# frontend/app.py
import streamlit as st
import requests
from fpdf import FPDF
import os
import time
import hashlib
from rapidfuzz.distance import Levenshtein as L
from streamlit.components.v1 import html as st_html
import altair as alt
import random

EJERCICIOS_BASE = {
    "B_V": {
        "facil": [
            {"masked": "a_uela", "opciones": ["b", "v"], "correcta": "b", "palabra": "abuela"},
            {"masked": "in_ierno", "opciones": ["b", "v"], "correcta": "v", "palabra": "invierno"},
            {"masked": "camina_a", "opciones": ["b", "v"], "correcta": "b", "palabra": "caminaba"},
            {"masked": "nue_o", "opciones": ["b", "v"], "correcta": "v", "palabra": "nuevo"},
        ],
        "intermedio": [
            {"masked": "_izcocho", "opciones": ["b", "v"], "correcta": "b", "palabra": "bizcocho"},
            {"masked": "mo_ilidad", "opciones": ["b", "v"], "correcta": "v", "palabra": "movilidad"},
            {"masked": "ob_io", "opciones": ["b", "v"], "correcta": "v", "palabra": "obvio"},
            {"masked": "her_ir", "opciones": ["b", "v"], "correcta": "v", "palabra": "hervir"},
        ],
        "dificil": [
            {"masked": "exacer_ar", "opciones": ["b", "v"], "correcta": "b", "palabra": "exacerbar"},
            {"masked": "nausea_undo", "opciones": ["b", "v"], "correcta": "b", "palabra": "nauseabundo"},
            {"masked": "longe_o", "opciones": ["b", "v"], "correcta": "v", "palabra": "longevo"},
            {"masked": "preca_er", "opciones": ["b", "v"], "correcta": "v", "palabra": "precaver"},
        ]
    },
    "G_J": {
        "facil": [
            {"masked": "gara_e", "opciones": ["g", "j"], "correcta": "j", "palabra": "garaje"},
            {"masked": "_igante", "opciones": ["g", "j"], "correcta": "g", "palabra": "gigante"},
            {"masked": "via_e", "opciones": ["g", "j"], "correcta": "j", "palabra": "viaje"},
        ],
        "intermedio": [
            {"masked": "extrran_ero", "opciones": ["g", "j"], "correcta": "j", "palabra": "extranjero"},
            {"masked": "co_er", "opciones": ["g", "j"], "correcta": "g", "palabra": "coger"},
            {"masked": "te_er", "opciones": ["g", "j"], "correcta": "j", "palabra": "tejer"},
        ],
        "dificil": [
            {"masked": "he_emonía", "opciones": ["g", "j"], "correcta": "g", "palabra": "hegemonía"},
            {"masked": "cru_ir", "opciones": ["g", "j"], "correcta": "j", "palabra": "crujir"},
            {"masked": "ambi_üo", "opciones": ["g", "j"], "correcta": "g", "palabra": "ambiguo"},
            {"masked": "para_e", "opciones": ["g", "j"], "correcta": "j", "palabra": "paraje"},
        ]
    },
    "Y_LL": {
        "facil": [
            {"masked": "_ogur", "opciones": ["y", "ll"], "correcta": "y", "palabra": "yogur"},
            {"masked": "caba_o", "opciones": ["y", "ll"], "correcta": "ll", "palabra": "caballo"},
            {"masked": "a_er", "opciones": ["y", "ll"], "correcta": "y", "palabra": "ayer"},
        ],
        "intermedio": [
            {"masked": "pro_ecto", "opciones": ["y", "ll"], "correcta": "y", "palabra": "proyecto"},
            {"masked": "deta_e", "opciones": ["y", "ll"], "correcta": "ll", "palabra": "detalle"},
            {"masked": "atrape_ar", "opciones": ["y", "ll"], "correcta": "ll", "palabra": "atropellar"},
        ],
        "dificil": [
            {"masked": "subra_ar", "opciones": ["y", "ll"], "correcta": "y", "palabra": "subrayar"},
            {"masked": "zambu_ir", "opciones": ["y", "ll"], "correcta": "ll", "palabra": "zambullir"},
            {"masked": "plebe_o", "opciones": ["y", "ll"], "correcta": "y", "palabra": "plebeyo"},
        ]
    },
    "C_Z": {
        "facil": [
            {"masked": "cora_ón", "opciones": ["c", "z", "s"], "correcta": "z", "palabra": "corazón"},
            {"masked": "pe_es", "opciones": ["c", "z", "s"], "correcta": "c", "palabra": "peces"},
            {"masked": "zapato_", "opciones": ["c", "z", "s"], "correcta": "s", "palabra": "zapatos"},
        ],
        "intermedio": [
            {"masked": "deci_ión", "opciones": ["c", "z", "s"], "correcta": "s", "palabra": "decisión"},
            {"masked": "ilu_ión", "opciones": ["c", "z", "s"], "correcta": "s", "palabra": "ilusión"},
            {"masked": "ambi_ión", "opciones": ["c", "z", "s"], "correcta": "c", "palabra": "ambición"},
        ],
        "dificil": [
            {"masked": "idiosincra_ia", "opciones": ["c", "z", "s"], "correcta": "s", "palabra": "idiosincrasia"},
            {"masked": "ascen_ión", "opciones": ["c", "z", "s"], "correcta": "s", "palabra": "ascensión"},
            {"masked": "exacerba_ión", "opciones": ["c", "z", "s"], "correcta": "c", "palabra": "exacerbación"},
        ]
    },
    "H": {
        "facil": [
            {"masked": "_ielo", "opciones": ["h", "Ø (nada)"], "correcta": "h", "palabra": "hielo"},
            {"masked": "_orario", "opciones": ["h", "Ø (nada)"], "correcta": "h", "palabra": "horario"},
            {"masked": "_ojalá", "opciones": ["h", "Ø (nada)"], "correcta": "Ø (nada)", "palabra": "ojalá"},
        ],
        "intermedio": [
            {"masked": "almo_ada", "opciones": ["h", "Ø (nada)"], "correcta": "h", "palabra": "almohada"},
            {"masked": "e_xhibición", "opciones": ["h", "Ø (nada)"], "correcta": "Ø (nada)", "palabra": "exhibición"},
            {"masked": "ana_oria", "opciones": ["h", "Ø (nada)"], "correcta": "h", "palabra": "zanahoria"},
        ],
        "dificil": [
            {"masked": "e_xhaustivo", "opciones": ["h", "Ø (nada)"], "correcta": "h", "palabra": "exhaustivo"},
            {"masked": "in_erente", "opciones": ["h", "Ø (nada)"], "correcta": "h", "palabra": "inherente"},
            {"masked": "ve_emencia", "opciones": ["h", "Ø (nada)"], "correcta": "h", "palabra": "vehemencia"},
            {"masked": "e_xuberante", "opciones": ["h", "Ø (nada)"], "correcta": "Ø (nada)", "palabra": "exuberante"},
        ]
    },
    "TILDES": {
        "facil": [
            {"masked": "canci_n", "opciones": ["o", "ó"], "correcta": "ó", "palabra": "canción"},
            {"masked": "arbol", "opciones": ["a", "á"], "correcta": "á", "palabra": "árbol"},
            {"masked": "exam_n", "opciones": ["e", "é"], "correcta": "e", "palabra": "examen"},
        ],
        "intermedio": [
            {"masked": "r_pido", "opciones": ["a", "á"], "correcta": "á", "palabra": "rápido"},
            {"masked": "vol_men", "opciones": ["u", "ú"], "correcta": "u", "palabra": "volumen"},
            {"masked": "car_cter", "opciones": ["a", "á"], "correcta": "á", "palabra": "carácter"},
        ],
        "dificil": [
            {"masked": "transe_nte", "opciones": ["u", "ú"], "correcta": "ú", "palabra": "transeúnte"},
            {"masked": "sutilmente", "opciones": ["i", "í"], "correcta": "i", "palabra": "sutilmente"},
            {"masked": "re_unir", "opciones": ["e", "é"], "correcta": "e", "palabra": "reunir"},
            {"masked": "historico-critico", "opciones": ["o-i", "ó-í"], "correcta": "ó-í", "palabra": "histórico-crítico"},
        ]
    }
}



st.set_page_config(page_title="PALABRIA", layout="centered")

# =========================
# UI: labels/keys
# =========================
PRETTY = {
    "total_frases": "Total de frases",
    "frases_con_tu_impersonal": "Posibles frases con 'tú' impersonal",
    "errores_b_v": "Errores de B vs V",
    "errores_g_j": "Errores de G vs J",
    "errores_y_ll": "Errores de Y vs LL",
    "errores_h": "Errores de H",
    "errores_tildes": "Errores de tildes",
    "errores_c_z": "Errores de C / Z / S",
    "cambios_propuestos_modelo": "Cambios propuestos (modelo)",
    "cambios_realizados_usuario": "Cambios realizados (usuario)",
}
SHOW_KEYS = list(PRETTY.keys())

# Backend modes
MODE_OPTIONS = {
    "📝 Ortografía completa (B/V, G/J, Y/LL, H, C/Z, tildes)": "ortografia",
    "👤 Tú impersonal → impersonal con “se”": "tu_impersonal",
}

# =========================
# CSS (tuyo)
# =========================
st.markdown("""
<style>
form[data-testid="stForm"] {
    margin-top: 5rem !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
div[data-testid="stVegaLiteChart"] {
    margin-bottom: -0.5rem !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown(
    """
    <style>
    .spacer-1cm { height: 0.25rem; }
    .spacer-tabs { height: 1.1rem; }
    .block-container { padding-top: 2.0rem; padding-bottom: 1.5rem; }
    .h-section, .stMarkdown h2, .stMarkdown h3 {
      font-size: 1.25rem !important; font-weight: 700 !important;
      margin-top: .5rem !important; margin-bottom: 0 !important;
      line-height: 1.2; color: #111827;
    }
    [data-testid="stVerticalBlock"] > div { margin-bottom: 0.3rem; }

    .stTabs { margin-top: 0.35rem; }
    .stTabs [data-baseweb="tab"],
    .stTabs button[role="tab"] {
      font-size: 1.30rem !important; font-weight: 700 !important;
      padding: .50rem 1.00rem !important;
      border: 1px solid rgba(49,51,63,0.12) !important;
      border-radius: .55rem !important; background: #fff !important;
      margin-right: .5rem !important; line-height: 1.2 !important;
      min-height: 2.4rem !important;
    }
    .stTabs [data-baseweb="tab"] p,
    .stTabs button[role="tab"] p,
    .stTabs [data-baseweb="tab"] span,
    .stTabs button[role="tab"] span {
      font-size: 1.20rem !important; font-weight: 700 !important;
      line-height: 1.2 !important;
    }
    .stTabs [aria-selected="true"],
    .stTabs button[role="tab"][aria-selected="true"] {
      border-color: #2563eb !important;
      box-shadow: 0 0 0 2px rgba(37,99,235,0.08) inset !important;
    }

    /* --- Cajas de métricas --- */
    div[data-testid="stMetric"] {
      padding: 0.5rem 0.6rem !important;
      border: 1px solid rgba(49,51,63,0.15) !important;
      border-radius: 0.5rem !important;
      background: #ffffff !important;
      text-align: center !important;
      box-shadow: 0 1px 2px rgba(0,0,0,0.04);
    }

    /* --- Título de cada métrica --- */
    div[data-testid="stMetricLabel"] {
      font-size: 1rem !important;
      font-weight: 500 !important;
      color: #111827 !important;
      margin-bottom: 0.15rem !important;
      line-height: 1.15 !important;
      text-align: center !important;
    }

    /* --- Valor numérico --- */
    div[data-testid="stMetricValue"] {
      font-size: 1.15rem !important;
      font-weight: 600 !important;
      color: #000000 !important;
      text-align: center !important;
      line-height: 1.2 !important;
    }

    /* --- Cuadros de texto de lectura (original/modelo) --- */
    .readonly-box {
      border: 1px solid rgba(49,51,63,0.2);
      border-radius: 0.5rem;
      padding: 0.5rem 0.6rem;
      background: #ffffff;
      color: inherit;
      font-family: inherit;
      line-height: 1.45;
      width: 100%;
      box-sizing: border-box;
      max-width: 100%;
      overflow-x: hidden;
      overflow-y: auto;
      min-height: 150px;
      max-height: 300px;
    }
    .readonly-box[readonly] {
      background: #ffffff;
      color: inherit;
      cursor: default;
    }

    /* --- Formularios --- */
    div[data-testid="stRadio"],
    div[data-testid="stTextInput"],
    div[data-testid="stFileUploader"] {
        margin-top: -0.35rem !important;
        margin-bottom: -0.15rem !important;
    }

    /* --- Áreas de texto editables --- */
    div[data-testid="stTextArea"] {
        overflow: visible !important;
        margin-right: 0 !important;
        padding-right: 0 !important;
        width: 100% !important;
        box-sizing: border-box !important;
    }
    div[data-testid="stTextArea"] > div {
        overflow: visible !important;
        width: 100% !important;
    }
    div[data-testid="stTextArea"] textarea {
        overflow-x: hidden !important;
        overflow-y: auto !important;
        width: 100% !important;
        max-width: 100% !important;
        box-sizing: border-box !important;
        resize: vertical !important;
        font-size: 1rem !important;
        line-height: 1.5 !important;
        border: 1px solid rgba(49,51,63,0.2) !important;
        border-radius: 0.5rem !important;
        padding: 0.5rem 0.6rem !important;
        background: #ffffff !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# =========================
# Helpers
# =========================
def save_text_as_pdf(text, filename="Texto_Corregido.pdf"):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    for line in (text or "").split("\n"):
        pdf.multi_cell(0, 10, line)
    pdf.output(filename)
    return filename

def fetch_status(backend_url, timeout=5):
    try:
        r = requests.get(f"{backend_url}/status/", timeout=timeout)
        if r.ok:
            data = r.json()
            return {
                "modelo_listo": bool(data.get("modelo_listo", False)),
                "progress": int(data.get("progress", 0)),
                "message": data.get("message", "⚡ Cargando…"),
            }
    except Exception as e:
        return {"modelo_listo": False, "progress": 0, "message": f"No conectado: {e}"}
    return {"modelo_listo": False, "progress": 0, "message": "Desconocido"}

def _normalize_for_diff(text: str) -> str:
    if not text:
        return ""
    t = text
    t = t.replace("…", "...")
    t = t.replace("“", '"').replace("”", '"')
    t = t.replace("‘", "'").replace("’", "'")
    t = t.replace("—", "-").replace("–", "-")
    t = t.replace("\r\n", "\n").replace("\r", "\n")
    return t.strip()

def word_levenshtein_count(a_text: str, b_text: str) -> int:
    a_tokens = _normalize_for_diff(a_text).split()
    b_tokens = _normalize_for_diff(b_text).split()
    return int(L.distance(a_tokens, b_tokens))

def pretty_int(x):
    try:
        fx = float(x)
        return int(fx) if fx.is_integer() else fx
    except Exception:
        return x

def pretty_hms(seconds: float) -> str:
    try:
        s = int(round(float(seconds)))
    except Exception:
        s = 0
    h = s // 3600
    m = (s % 3600) // 60
    ss = s % 60
    parts = []
    if h > 0: parts.append(f"{h} h")
    if m > 0 or h > 0: parts.append(f"{m} min")
    parts.append(f"{ss} s")
    return " ".join(parts)

def inject_session_js(backend_url: str, username: str):
    js = f"""
    <script>
    (function(){{
      const backend = {repr(backend_url)};
      const username = {repr(username)};
      const hbUrl = backend + "/users/heartbeat";
      const loUrl = backend + "/users/logout";

      function postForm(url, dataObj) {{
        const formData = new URLSearchParams();
        for (const k in dataObj) formData.append(k, dataObj[k]);
        return fetch(url, {{
          method: "POST",
          mode: "cors",
          headers: {{"Content-Type":"application/x-www-form-urlencoded"}},
          body: formData.toString()
        }}).catch(()=>{{}});
      }}

      const sendHeartbeat = () => postForm(hbUrl, {{username}});
      sendHeartbeat();
      const hbTimer = setInterval(sendHeartbeat, 20000);

      function beaconLogout() {{
        try {{
          if (!navigator.sendBeacon) {{
            postForm(loUrl, {{username}});
            return;
          }}
          const data = new URLSearchParams();
          data.append("username", username);
          const blob = new Blob([data.toString()], {{type: "application/x-www-form-urlencoded"}});
          navigator.sendBeacon(loUrl, blob);
        }} catch (e) {{}}
      }}

      window.addEventListener("beforeunload", beaconLogout);
      document.addEventListener("visibilitychange", function(){{
        if (document.visibilityState === "hidden") beaconLogout();
      }});
    }})();
    </script>
    """
    st_html(js, height=0)

def has_current_analysis() -> bool:
    anal = st.session_state.get("last_analysis")
    if not anal:
        return False
    return bool(anal.get("original_text") or anal.get("corrected_text"))

def clear_current_analysis():
    for k in ["last_input_digest","last_pdf_name","last_doc_id",
              "last_analysis","edited_text_area","__edited_for_doc"]:
        st.session_state.pop(k, None)

def _clear_status_cache():
    for k in ["modelo_listo","status_progress","status_message",
              "notificado_listo","last_status_check"]:
        st.session_state.pop(k, None)

def _clear_metrics_cache():
    for k in ["__cache_overview","__cache_documents"]:
        st.session_state.pop(k, None)
    for k in list(st.session_state.keys()):
        if str(k).startswith("__cache_doc_"):
            st.session_state.pop(k, None)

def _fetch_and_cache_doc_metrics(backend_url, doc_id: int):
    try:
        m = requests.get(f"{backend_url}/documents/{doc_id}/metrics", timeout=20).json()["metrics"]
        st.session_state[f"__cache_doc_{doc_id}"] = m
    except Exception:
        pass

def _post_user_changes(backend_url, doc_id: int, changes: int):
    try:
        requests.post(
            f"{backend_url}/documents/{doc_id}/user_changes",
            data={"changes": changes},
            timeout=10
        )
        st.session_state[f"__last_saved_changes_{doc_id}"] = int(changes)
        _fetch_and_cache_doc_metrics(backend_url, doc_id)
    except Exception:
        pass

# =========================
# Auth forms (tuyas)
# =========================
def login():
    with st.form("login_form"):
        st.markdown("<h2 class='h-section'>🔓 Iniciar sesión</h2>", unsafe_allow_html=True)
        username = st.text_input("Nombre de usuario")
        submit = st.form_submit_button("Entrar")
        if submit:
            if username:
                backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")
                try:
                    r = requests.post(f"{backend_url}/users/login", data={"username": username}, timeout=10)
                    if r.ok and r.json().get("ok"):
                        st.session_state["usuario"] = username
                        st.session_state["logged_in"] = True
                        st.session_state["show_login"] = False
                        st.session_state["show_create_account"] = False
                        st.success(f"Bienvenido/a, {username}")
                        _clear_status_cache()
                        _clear_metrics_cache()
                        clear_current_analysis()
                        st.rerun()
                    else:
                        try:
                            msg = r.json().get("detail", r.text)
                        except Exception:
                            msg = r.text
                        st.error(msg or "No se pudo iniciar sesión.")
                except Exception as e:
                    st.error(f"Error conectando con backend: {e}")
            else:
                st.warning("Por favor, escribe un nombre de usuario.")

def create_account():
    with st.form("create_account_form"):
        st.markdown("<h2 class='h-section'>📝 Crear nueva cuenta</h2>", unsafe_allow_html=True)
        new_username = st.text_input("Elige un nombre de usuario (letras/números/_-. máx 32)")
        submit = st.form_submit_button("Crear cuenta")
        if submit:
            if new_username:
                backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")
                try:
                    r = requests.post(f"{backend_url}/users/create", data={"username": new_username}, timeout=10)
                    if r.ok and r.json().get("ok"):
                        st.session_state["usuario"] = new_username
                        st.session_state["logged_in"] = True
                        st.session_state["show_login"] = False
                        st.session_state["show_create_account"] = False
                        st.success(f"Cuenta creada para {new_username}")
                        _clear_status_cache()
                        _clear_metrics_cache()
                        clear_current_analysis()
                        st.rerun()
                    else:
                        try:
                            msg = r.json().get("detail", r.text)
                        except Exception:
                            msg = r.text
                        st.error(msg or "No se pudo crear la cuenta.")
                except Exception as e:
                    st.error(f"Error conectando con backend: {e}")
            else:
                st.warning("Por favor, escribe un nombre de usuario.")

# =========================
# Metrics screens (tuyas)
# =========================
def cargar_metricas(username, backend_url):
    ov = requests.get(f"{backend_url}/users/{username}/overview", timeout=20).json()
    docs = requests.get(f"{backend_url}/users/{username}/documents", timeout=20).json().get("documents", [])
    st.session_state["__cache_overview"] = ov
    st.session_state["__cache_documents"] = docs

def mostrar_perfil(username, backend_url):
    # 1. Obtener datos del perfil (avatar y racha)
    try:
        r_prof = requests.get(f"{backend_url}/users/{username}/profile", timeout=5)
        perfil = r_prof.json().get("profile", {}) if r_prof.ok else {"avatar": "🐼", "current_streak": 1}
    except:
        perfil = {"avatar": "🐼", "current_streak": 1}

    # 2. Dibujar Cabecera
    st.markdown("<h1 style='text-align: center; margin-bottom: 2rem;'>👤 Mi Perfil</h1>", unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown(f"<div style='font-size: 6rem; text-align: center; line-height: 1;'>{perfil.get('avatar')}</div>", unsafe_allow_html=True)
        st.markdown(f"<h2 style='text-align: center; margin-top: 0.5rem;'>{username}</h2>", unsafe_allow_html=True)
        st.markdown(f"<h4 style='text-align: center; color: #f59e0b; margin-top: -10px;'>🔥 Racha actual: {perfil.get('current_streak')} días</h4>", unsafe_allow_html=True)
        
        with st.expander("Cambiar Avatar", expanded=False):
            avatares = ['🐼', '🦊', '🐱', '🐶', '🦄', '🐸', '🦉', '🐙', '🦁', '🐻', '🐵', '🐮']
            idx = avatares.index(perfil.get("avatar")) if perfil.get("avatar") in avatares else 0
            nuevo_avatar = st.selectbox("Elige tu nuevo avatar", avatares, index=idx)
            if st.button("Guardar Avatar", use_container_width=True):
                requests.post(f"{backend_url}/users/{username}/avatar", data={"avatar": nuevo_avatar})
                st.rerun()

    st.markdown("<hr style='margin: 2rem 0;'/>", unsafe_allow_html=True)
    if "__cache_overview" not in st.session_state or "__cache_documents" not in st.session_state:
        try:
            cargar_metricas(username, backend_url)
            for d in st.session_state.get("__cache_documents", []):
                _fetch_and_cache_doc_metrics(backend_url, d["id"])
        except Exception as e:
            st.error(f"No se pudieron cargar las métricas: {e}")
    st.markdown("<h2 class='h-section'>🏆 Tu Nivel Ortográfico</h2>", unsafe_allow_html=True)
    
    try:
        r_niveles = requests.get(f"{backend_url}/users/{username}/levels", timeout=10)
        if r_niveles.ok:
            niveles = r_niveles.json().get("niveles", {})
            if niveles:
                # Dibujar el nivel general destacado como una tarjeta grande
                nivel_gen = niveles.get("nivel_general", "⚪ Sin datos")
                
                # Elegir color de fondo según el nivel general
                color_bg = "#f3f4f6" # Gris por defecto
                color_border = "#d1d5db"
                if "Avanzado" in nivel_gen:
                    color_bg, color_border = "#dcfce7", "#22c55e" # Verde
                elif "Medio" in nivel_gen:
                    color_bg, color_border = "#fef08a", "#eab308" # Amarillo
                elif "Bajo" in nivel_gen:
                    color_bg, color_border = "#fee2e2", "#ef4444" # Rojo

                st.markdown(f"""
                <div style='text-align: center; padding: 1.5rem; background: {color_bg}; border-radius: 15px; border: 2px solid {color_border}; margin-bottom: 1.5rem; box-shadow: 0 4px 6px rgba(0,0,0,0.05);'>
                    <h3 style='margin:0; color: #374151; font-weight: 600;'>Nivel General Ortográfico</h3>
                    <h1 style='margin:0; font-size: 2.5rem; color: #111827;'>{nivel_gen}</h1>
                </div>
                """, unsafe_allow_html=True)
                
                # Dibujar los niveles por categoría en columnas
                st.markdown("<p style='text-align: center; font-weight: 600;'>Desglose por categoría:</p>", unsafe_allow_html=True)
                c1, c2, c3 = st.columns(3)
                c1.metric("B / V", niveles.get("nivel_b_v", "⚪ Sin datos"))
                c2.metric("G / J", niveles.get("nivel_g_j", "⚪ Sin datos"))
                c3.metric("Y / LL", niveles.get("nivel_y_ll", "⚪ Sin datos"))
                
                c4, c5, c6 = st.columns(3)
                c4.metric("C / Z / S", niveles.get("nivel_c_z", "⚪ Sin datos"))
                c5.metric("H", niveles.get("nivel_h", "⚪ Sin datos"))
                c6.metric("Tildes", niveles.get("nivel_tildes", "⚪ Sin datos"))
                
                st.markdown("<hr style='margin-top: 2rem; margin-bottom: 2rem;'/>", unsafe_allow_html=True)
            else:
                st.info("Analiza tu primer texto para desbloquear tu nivel ortográfico 🚀")
    except Exception as e:
        st.warning(f"No se pudieron cargar los niveles: {e}")
    st.markdown(
        """
        <style>
        div[data-testid="stButton"] > button[kind="secondary"],
        div[data-testid="stButton"] > button#btn_refresh_metrics {
            background-color: #f0f0f0 !important;
            color: #333 !important;
            border: 1px solid #d1d5db !important;
            font-weight: 600 !important;
            transition: background-color 0.2s ease;
        }
        div[data-testid="stButton"] > button#btn_refresh_metrics:hover {
            background-color: #e5e5e5 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    if st.button("Actualizar métricas", key="btn_refresh_metrics", use_container_width=True):
        cargar_metricas(username, backend_url)
        for d in st.session_state.get("__cache_documents", []):
            _fetch_and_cache_doc_metrics(backend_url, d["id"])

    st.markdown("""
    <style>
    div[data-testid="stMetric"] {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center !important;
    }
    div[data-testid="stMetricLabel"] {
        text-align: center !important;
        justify-content: center !important;
        align-items: center !important;
        font-weight: 600 !important;
    }
    div[data-testid="stMetricValue"] {
        text-align: center !important;
        justify-content: center !important;
        align-items: center !important;
        font-weight: 500 !important;
        color: #000 !important;
        font-size: 0.97rem !important;
    }
    </style>
    """, unsafe_allow_html=True)

    ov = st.session_state.get("__cache_overview")
    docs = st.session_state.get("__cache_documents")

    if ov:
        usage = ov.get("usage", {})
        c1, c2 = st.columns(2, gap="medium")
        c1.metric("📄 Documentos procesados", ov.get("docs", 0))
        c2.metric("📆 Días en actividad", ov.get("login_days", 0))

        c3, c4 = st.columns(2, gap="medium")
        c3.metric("🔁 Inicios de sesión", usage.get("login", {}).get("count", 0))
        avg_secs = float(ov.get("avg_session_seconds", 0.0) or 0.0)
        c4.metric("⏱️ Tiempo medio por sesión", pretty_hms(avg_secs))

        c5, c6 = st.columns(2, gap="medium")
        c5.metric("📈 % docs con 'tú' impersonal", f"{float(ov.get('docs_with_tu_percent', 0.0) or 0.0):.1f}%")
        c6.metric("🛠️ % docs sin cambios", f"{float(ov.get('docs_no_changes_percent', 0.0) or 0.0):.1f}%")

        st.markdown("<h2 class='h-section'>📊 Promedios por métrica (histórico)</h2>", unsafe_allow_html=True)
        avg_metrics = ov.get("avg_metrics", {})
        if avg_metrics:
            st.markdown("""
            <style>
            .metric-row { padding: 0.4rem 0.8rem; border-radius: 0.4rem; margin-bottom: 0.25rem; }
            .metric-row:nth-child(odd) { background-color: #f9fafb; }
            .metric-row:nth-child(even) { background-color: #ffffff; }
            .metric-label { font-weight: 400; color: #374151; }
            .metric-value { float: right; font-weight: 500; color: #000000; }
            </style>
            """, unsafe_allow_html=True)

            html_rows = ""
            for key in SHOW_KEYS:
                if key in avg_metrics:
                    label = PRETTY.get(key, key)
                    value = pretty_int(round(avg_metrics[key], 2))
                    html_rows += f"<div class='metric-row'><span class='metric-label'>{label}</span><span class='metric-value'>{value}</span></div>"
            st.markdown(html_rows, unsafe_allow_html=True)
        else:
            st.info("Sin métricas históricas todavía.")

        st.markdown("<h2 class='h-section'>📅 Actividad semanal</h2>", unsafe_allow_html=True)
        st.markdown("<div style='margin-bottom: 1.5rem;'></div>", unsafe_allow_html=True)
        try:
            resp = requests.get(f"{backend_url}/users/{username}/weekly_activity", timeout=10)
            if resp.ok:
                data = resp.json().get("activity", [])
                if data:
                    import pandas as pd
                    df = pd.DataFrame(data)
                    df["minutos"] = df["total_seconds"] / 60.0
                    df["day"] = pd.to_datetime(df["day"])
                    df = df.sort_values("day")
                    mapping = {"Monday":"Lun","Tuesday":"Mar","Wednesday":"Mié","Thursday":"Jue","Friday":"Vie","Saturday":"Sáb","Sunday":"Dom"}
                    df["dia_semana"] = df["day"].dt.day_name().map(mapping)
                    order = ["No inició sesión", "Hasta 5 min", "Hasta 15 min", "Hasta 30 min", "Más de 30 min"]

                    chart = (
                        alt.Chart(df)
                        .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
                        .encode(
                            x=alt.X("dia_semana:N", title="Día de la semana", sort=["Lun","Mar","Mié","Jue","Vie","Sáb","Dom"]),
                            y=alt.Y("minutos:Q", title="Minutos totales"),
                            color=alt.Color("categoria:N", title="Nivel de actividad",
                                            scale=alt.Scale(domain=order,
                                                            range=["#ef4444","#f97316","#facc15","#22c55e","#3b82f6"])),
                            tooltip=[
                                alt.Tooltip("day:T", title="Fecha"),
                                alt.Tooltip("minutos:Q", title="Minutos totales", format=".1f"),
                                alt.Tooltip("categoria:N", title="Nivel")
                            ],
                        )
                        .properties(height=300, width="container")
                    )
                    st.altair_chart(chart, use_container_width=True)
                else:
                    st.info("Sin datos de actividad aún.")
            else:
                st.warning("No se pudo obtener la actividad semanal.")
        except Exception as e:
            st.warning(f"Error al obtener la actividad: {e}")
    st.markdown("<h2 class='h-section'>📈 Evolución de errores ortográficos</h2>", unsafe_allow_html=True)
    st.markdown("<p style='font-size: 0.95rem; color: #555;'>Muestra el % de error en los últimos 15 textos para cada categoría (solo se cuentan los textos que contenían palabras con riesgo de fallar).</p>", unsafe_allow_html=True)

    try:
        resp_prog = requests.get(f"{backend_url}/users/{username}/progress", timeout=10)
        if resp_prog.ok:
            prog_data = resp_prog.json().get("progress", [])
            if prog_data:
                import pandas as pd
                df_prog = pd.DataFrame(prog_data)
                
                # Gráfico múltiple con Altair
                chart_prog = (
                    alt.Chart(df_prog)
                    .mark_line(point=True, strokeWidth=3, size=80)
                    .encode(
                        x=alt.X("doc_index:O", title="Textos evaluados cronológicamente (1 = más antiguo)"),
                        y=alt.Y("porcentaje_error:Q", title="% de Error cometido", scale=alt.Scale(domain=[0, 100])),
                        color=alt.Color("categoria:N", title="Categoría"),
                        tooltip=[
                            alt.Tooltip("categoria:N", title="Regla"),
                            alt.Tooltip("porcentaje_error:Q", title="% de Error", format=".1f"),
                            alt.Tooltip("fecha:T", title="Fecha")
                        ]
                    )
                    .properties(height=350, width="container")
                    .interactive()
                )
                
                st.altair_chart(chart_prog, use_container_width=True)
            else:
                st.info("Aún no tienes suficientes datos procesados para ver la evolución de las reglas ortográficas.")
        else:
            st.warning("No se pudo obtener el progreso histórico.")
    except Exception as e:
        st.warning(f"Error cargando la gráfica de progreso: {e}")
    st.markdown("<h1 style='text-align: center; margin-bottom: 0.5rem;'>🏅 Vitrina de Insignias</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #6b7280; font-size: 1.1rem; margin-bottom: 2rem;'>Mantén tu nivel de error por debajo del 10% durante 15 textos seguidos para desbloquearlas.</p>", unsafe_allow_html=True)
    
    try:
        r_badges = requests.get(f"{backend_url}/users/{username}/badges", timeout=10)
        user_badges = []
        if r_badges.ok:
            user_badges = r_badges.json().get("badges", [])

        # CSS para la vitrina
        st.markdown("""
        <style>
        .vitrina {
            display: flex;
            flex-wrap: wrap;
            justify-content: center;
            gap: 2rem;
            margin-top: 3rem;
            margin-bottom: 3rem;
        }
        .insignia-box {
            display: flex;
            flex-direction: column;
            align-items: center;
            width: 140px;
            text-align: center;
        }
        .insignia-circle {
            width: 110px;
            height: 110px;
            border-radius: 50%;
            background-color: #f3f4f6; /* Gris (No conseguida) */
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 3rem;
            margin-bottom: 1rem;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
            box-shadow: inset 0 4px 6px rgba(0,0,0,0.1);
            filter: grayscale(100%) opacity(0.4);
        }
        .insignia-earned {
            background: linear-gradient(135deg, #fbbf24, #f59e0b); /* Dorado */
            box-shadow: 0 10px 25px rgba(245, 158, 11, 0.4);
            filter: grayscale(0%) opacity(1);
            transform: scale(1.05);
        }
        .insignia-earned:hover {
            transform: scale(1.1) translateY(-5px);
        }
        .insignia-master {
            background: linear-gradient(135deg, #a855f7, #7e22ce); /* Morado Mágico */
            box-shadow: 0 10px 30px rgba(168, 85, 247, 0.5);
            width: 140px;
            height: 140px;
            font-size: 4rem;
        }
        .insignia-title {
            font-size: 0.95rem;
            font-weight: 700;
            color: #374151;
            line-height: 1.3;
        }
        .insignia-subtitle {
            font-size: 0.75rem;
            color: #6b7280;
            margin-top: 0.2rem;
        }
        </style>
        """, unsafe_allow_html=True)

        todas_insignias = [
            {"id": "dominio_b_v", "titulo": "Dominio B/V", "sub": "15 textos impecables", "emoji": "🅱️"},
            {"id": "dominio_g_j", "titulo": "Dominio G/J", "sub": "15 textos impecables", "emoji": "🦒"},
            {"id": "dominio_y_ll", "titulo": "Dominio Y/LL", "sub": "15 textos impecables", "emoji": "🗝️"},
            {"id": "dominio_tildes", "titulo": "Francotirador", "sub": "Rey de las tildes", "emoji": "🎯"},
            {"id": "dominio_h", "titulo": "Cazafantasmas", "sub": "Dominio de la H", "emoji": "👻"},
            {"id": "dominio_otros", "titulo": "Pluma de Oro", "sub": "Buena Escritura general", "emoji": "✍️"},
        ]

        # Renderizar insignias básicas
        html_insignias = "<div class='vitrina'>"
        for ins in todas_insignias:
            clase_extra = "insignia-earned" if ins["id"] in user_badges else ""
            
            # HTML compactado sin sangrías para evitar el bug de Markdown en Streamlit
            html_insignias += f"<div class='insignia-box'><div class='insignia-circle {clase_extra}'>{ins['emoji']}</div><div class='insignia-title'>{ins['titulo']}</div><div class='insignia-subtitle'>{ins['sub']}</div></div>"
            
        html_insignias += "</div>"
        
        st.markdown(html_insignias, unsafe_allow_html=True)
        # Renderizar la de Master centrada abajo, más espectacular
        clase_master = "insignia-earned insignia-master" if "master_ortografia" in user_badges else "insignia-master"
        st.markdown(f"""
        <div class='vitrina' style='margin-top: 0;'>
            <div class="insignia-box" style="width: 200px;">
                <div class="insignia-circle {clase_master}">
                    👑
                </div>
                <div class="insignia-title" style="font-size: 1.2rem; margin-top: 0.5rem;">Máster de la Ortografía</div>
                <div class="insignia-subtitle" style="font-size: 0.85rem;">Consigue todas las demás</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    except Exception as e:
        st.warning(f"Error cargando vitrina: {e}")
    st.markdown("<h2 class='h-section'>Mis documentos</h2>", unsafe_allow_html=True)
    if docs:
        for d in docs:
            title = f"📄 {d['filename']} — {d['uploaded_at']}"
            with st.expander(title, expanded=False):
                cache_key = f"__cache_doc_{d['id']}"
                if cache_key not in st.session_state:
                    _fetch_and_cache_doc_metrics(backend_url, d["id"])

                metrics_list = st.session_state.get(cache_key)
                if metrics_list:
                    latest_by_name = {}
                    for row in metrics_list:
                        latest_by_name[row["metric_name"]] = row["metric_value"]

                    cA, cB = st.columns(2, gap="medium")
                    for i, k in enumerate(SHOW_KEYS):
                        if k in latest_by_name:
                            (cA if i % 2 == 0 else cB).metric(PRETTY[k], pretty_int(latest_by_name[k]))

                del_flag_key = f"__confirm_del_{d['id']}"
                if st.button("❌ Eliminar", key=f"del_{d['id']}", use_container_width=True):
                    st.session_state[del_flag_key] = True

                if st.session_state.get(del_flag_key):
                    st.warning("Esta acción eliminará definitivamente el documento y sus métricas. ¿Confirmas?")
                    col_ok, col_cancel = st.columns(2)
                    if col_ok.button("Sí, eliminar", key=f"ok_{d['id']}", use_container_width=True):
                        try:
                            r = requests.delete(f"{backend_url}/documents/{d['id']}", timeout=15)
                            if r.ok and r.json().get("ok"):
                                deleted_id = d['id']
                                if st.session_state.get("last_doc_id") == deleted_id:
                                    clear_current_analysis()
                                st.session_state.pop(f"__cache_doc_{d['id']}", None)
                                cargar_metricas(username, backend_url)
                                st.session_state[del_flag_key] = False
                                st.rerun()
                            else:
                                st.error(f"No se pudo eliminar: {r.text}")
                        except Exception as e:
                            st.error(f"Error eliminando: {e}")
                    if col_cancel.button("Cancelar", key=f"cancel_{d['id']}", use_container_width=True):
                        st.session_state[del_flag_key] = False
    else:
        st.info("No hay documentos aún.")

# =========================
# Status (tuyo)
# =========================
def render_status(backend_url):
    if "modelo_listo" not in st.session_state:
        st.session_state["modelo_listo"] = False
    if "status_progress" not in st.session_state:
        st.session_state["status_progress"] = 0
    if "status_message" not in st.session_state:
        st.session_state["status_message"] = "⚡ Preparando…"

    st.progress(st.session_state["status_progress"])

    if st.session_state["modelo_listo"]:
        st.success("✅ Modelo cargado y listo")
        return

    estado = fetch_status(backend_url, timeout=5)
    st.session_state["modelo_listo"]  = bool(estado.get("modelo_listo"))
    st.session_state["status_progress"] = int(estado.get("progress", 0))
    st.session_state["status_message"]  = estado.get("message", "")
    st.info(st.session_state["status_message"] or "⚡ Cargando…")

    if st.button("🔄 Actualizar estado", key="btn_status_refresh_main", use_container_width=True):
        estado = fetch_status(backend_url, timeout=5)
        st.session_state["modelo_listo"]  = bool(estado.get("modelo_listo"))
        st.session_state["status_progress"] = int(estado.get("progress", 0))
        st.session_state["status_message"]  = estado.get("message", "")

    st.stop()
def mostrar_repaso():
    st.markdown("""
    <style>
    .flashcard-container {
        perspective: 1000px;
        margin: 2rem auto;
    }
    .flashcard {
        background: #ffffff;
        border-radius: 20px;
        padding: 2.5rem;
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.08);
        border-top: 8px solid #3b82f6;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    .flashcard:hover {
        transform: translateY(-5px);
        box-shadow: 0 15px 35px rgba(0, 0, 0, 0.12);
    }
    .flashcard::before {
        content: "";
        position: absolute;
        top: -50px;
        right: -50px;
        width: 150px;
        height: 150px;
        background: rgba(59, 130, 246, 0.05);
        border-radius: 50%;
    }
    .flashcard-title {
        color: #1e3a8a;
        font-size: 2.2rem !important;
        font-weight: 800 !important;
        margin-bottom: 1.5rem !important;
        text-align: center;
        letter-spacing: -0.5px;
    }
    .flashcard-content {
        font-size: 1.15rem;
        color: #374151;
        line-height: 1.7;
    }
    .flashcard-content ul {
        margin-top: 0.5rem;
        margin-bottom: 1.5rem;
    }
    .flashcard-content li {
        margin-bottom: 0.8rem;
    }
    .flashcard-examples {
        background: linear-gradient(135deg, #eff6ff, #dbeafe);
        padding: 1.2rem;
        border-radius: 12px;
        color: #1e40af;
        font-weight: 500;
        margin-top: 1.5rem;
        border-left: 4px solid #60a5fa;
    }
    .example-word {
        font-weight: 800;
        color: #2563eb;
    }
    </style>
    """, unsafe_allow_html=True)

    # Datos de las tarjetas
    tarjetas = [
        {
            "titulo": "Uso de la B y la V",
            "emoji": "🅱️ / ✌️",
            "reglas": [
                "Se escriben con <b>B</b> los verbos terminados en <i>-bir</i> y <i>-buir</i> (excepto hervir, servir y vivir).",
                "Se escriben con <b>B</b> las terminaciones del pretérito imperfecto: <i>-aba, -abas...</i>",
                "Se escriben con <b>V</b> los adjetivos terminados en <i>-avo, -ave, -evo, -eve, -ivo, -iva</i>.",
                "Se escriben con <b>V</b> las palabras que empiezan por <i>ad-, sub-, ob-</i> seguidas de este sonido."
            ],
            "ejemplos": "Escribir, contribuir, cantaba, <span class='example-word'>suave</span>, <span class='example-word'>obvio</span>, <span class='example-word'>advertir</span>."
        },
        {
            "titulo": "Uso de la G y la J",
            "emoji": "🦒 / 🐆",
            "reglas": [
                "Se escriben con <b>G</b> los verbos terminados en <i>-ger, -gir</i> (excepto tejer y crujir).",
                "Se escriben con <b>G</b> las palabras que empiezan por <i>geo-</i> (tierra) o terminan en <i>-logía</i>.",
                "Se escriben con <b>J</b> las palabras que terminan en <i>-aje, -eje</i>.",
                "Se escriben con <b>J</b> las formas de los verbos que no llevan ni G ni J en su infinitivo (ej: decir -> dije)."
            ],
            "ejemplos": "Recoger, <span class='example-word'>geografía</span>, biología, <span class='example-word'>garaje</span>, <span class='example-word'>conduje</span>."
        },
        {
            "titulo": "Uso de Y y LL",
            "emoji": "🪀 / 🗝️",
            "reglas": [
                "Se escriben con <b>LL</b> las palabras terminadas en <i>-illo, -illa</i>.",
                "Se escriben con <b>LL</b> los verbos terminados en <i>-llir, -ullar</i>.",
                "Se escriben con <b>Y</b> los plurales de las palabras que terminan en <i>-y</i> (ley -> leyes).",
                "Se escribe <b>Y</b> en las formas verbales que no tienen LL ni Y en el infinitivo (caer -> cayó)."
            ],
            "ejemplos": "Pasillo, <span class='example-word'>zambullir</span>, reyes, <span class='example-word'>leyendo</span>, <span class='example-word'>oyó</span>."
        },
        {
            "titulo": "Uso de C, Z y S",
            "emoji": "🦊 / 🐍",
            "reglas": [
                "Se usa <b>Z</b> delante de a, o, u (zapato) y <b>C</b> delante de e, i (cielo).",
                "Se usa <b>C</b> en las terminaciones <i>-ción</i> cuando la palabra deriva de otra que termina en <i>-to, -tor, -do, -dor</i>.",
                "Se usa <b>S</b> en las terminaciones <i>-sión</i> cuando deriva de palabras terminadas en <i>-so, -sor, -sivo, -sible</i>.",
                "Los plurales de las palabras que terminan en Z, se escriben con <b>C</b> (luz -> luces)."
            ],
            "ejemplos": "<span class='example-word'>Zorro</span>, <span class='example-word'>canción</span> (cantor), <span class='example-word'>ilusión</span> (iluso), <span class='example-word'>peces</span>."
        },
        {
            "titulo": "Uso de la H",
            "emoji": "👻",
            "reglas": [
                "Se escriben con <b>H</b> las palabras que empiezan por los diptongos <i>hie-, hue-, hui-, hia-</i>.",
                "Se escriben con <b>H</b> los prefijos griegos como <i>hidro-</i> (agua), <i>hiper-</i> (exceso), <i>hipo-</i> (caballo/debajo).",
                "Todas las formas de los verbos haber, hacer, hallar, hablar y habitar llevan <b>H</b>."
            ],
            "ejemplos": "<span class='example-word'>Hielo</span>, <span class='example-word'>hueso</span>, hidrofobia, <span class='example-word'>hicimos</span>, <span class='example-word'>hubo</span>."
        },
        {
            "titulo": "Acentuación (Tildes)",
            "emoji": "🎯",
            "reglas": [
                "<b>Agudas:</b> Llevan tilde si terminan en vocal, <i>-n</i> o <i>-s</i>. (La fuerza va en la última sílaba).",
                "<b>Llanas:</b> Llevan tilde si terminan en consonante que NO sea <i>-n</i> ni <i>-s</i>. (Fuerza en la penúltima).",
                "<b>Esdrújulas y Sobresdrújulas:</b> ¡Llevan tilde siempre! (Fuerza en la antepenúltima o anterior)."
            ],
            "ejemplos": "<span class='example-word'>Camión</span> (aguda), <span class='example-word'>árbol</span> (llana), <span class='example-word'>rápido</span> (esdrújula), <span class='example-word'>examen</span> (llana sin tilde)."
        }
    ]

    # Inicializar el índice de la tarjeta actual en session_state
    if "repaso_index" not in st.session_state:
        st.session_state.repaso_index = 0

    st.markdown("<h1 style='text-align: center; margin-bottom: 0.5rem;'>📖 Tarjetas de Repaso</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; font-size: 1.1rem; color: #6b7280; margin-bottom: 2rem;'>Desliza para recordar las reglas ortográficas más importantes.</p>", unsafe_allow_html=True)

    # Controles superiores (progreso)
    total_tarjetas = len(tarjetas)
    idx = st.session_state.repaso_index
    tarjeta = tarjetas[idx]

    st.progress((idx + 1) / total_tarjetas)
    st.caption(f"<div style='text-align: center;'>Tarjeta {idx + 1} de {total_tarjetas}</div>", unsafe_allow_html=True)

    # Renderizar la tarjeta
    html_reglas = "".join([f"<li>{r}</li>" for r in tarjeta["reglas"]])
    
    st.markdown(f"""
    <div class="flashcard-container">
        <div class="flashcard">
            <h2 class="flashcard-title">{tarjeta['emoji']} {tarjeta['titulo']}</h2>
            <div class="flashcard-content">
                <ul>
                    {html_reglas}
                </ul>
            </div>
            <div class="flashcard-examples">
                💡 <b>Ejemplos:</b><br>{tarjeta['ejemplos']}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)

    # Botones de navegación del carrusel
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        if st.button("⬅️ Anterior", use_container_width=True, disabled=(idx == 0)):
            st.session_state.repaso_index -= 1
            st.rerun()
            
    with col3:
        if st.button("Siguiente ➡️", use_container_width=True, disabled=(idx == total_tarjetas - 1)):
            st.session_state.repaso_index += 1
            st.rerun()

def mostrar_vitrina(backend_url, username):
    st.markdown("<h1 style='text-align: center; margin-bottom: 0.5rem;'>🏅 Vitrina de Insignias</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #6b7280; font-size: 1.1rem; margin-bottom: 2rem;'>Mantén tu nivel de error por debajo del 10% durante 15 textos seguidos para desbloquearlas.</p>", unsafe_allow_html=True)
    
    try:
        r_badges = requests.get(f"{backend_url}/users/{username}/badges", timeout=10)
        user_badges = []
        if r_badges.ok:
            user_badges = r_badges.json().get("badges", [])

        # CSS para la vitrina
        st.markdown("""
        <style>
        .vitrina {
            display: flex;
            flex-wrap: wrap;
            justify-content: center;
            gap: 2rem;
            margin-top: 3rem;
            margin-bottom: 3rem;
        }
        .insignia-box {
            display: flex;
            flex-direction: column;
            align-items: center;
            width: 140px;
            text-align: center;
        }
        .insignia-circle {
            width: 110px;
            height: 110px;
            border-radius: 50%;
            background-color: #f3f4f6; /* Gris (No conseguida) */
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 3rem;
            margin-bottom: 1rem;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
            box-shadow: inset 0 4px 6px rgba(0,0,0,0.1);
            filter: grayscale(100%) opacity(0.4);
        }
        .insignia-earned {
            background: linear-gradient(135deg, #fbbf24, #f59e0b); /* Dorado */
            box-shadow: 0 10px 25px rgba(245, 158, 11, 0.4);
            filter: grayscale(0%) opacity(1);
            transform: scale(1.05);
        }
        .insignia-earned:hover {
            transform: scale(1.1) translateY(-5px);
        }
        .insignia-master {
            background: linear-gradient(135deg, #a855f7, #7e22ce); /* Morado Mágico */
            box-shadow: 0 10px 30px rgba(168, 85, 247, 0.5);
            width: 140px;
            height: 140px;
            font-size: 4rem;
        }
        .insignia-title {
            font-size: 0.95rem;
            font-weight: 700;
            color: #374151;
            line-height: 1.3;
        }
        .insignia-subtitle {
            font-size: 0.75rem;
            color: #6b7280;
            margin-top: 0.2rem;
        }
        </style>
        """, unsafe_allow_html=True)

        todas_insignias = [
            {"id": "dominio_b_v", "titulo": "Dominio B/V", "sub": "15 textos impecables", "emoji": "🅱️"},
            {"id": "dominio_g_j", "titulo": "Dominio G/J", "sub": "15 textos impecables", "emoji": "🦒"},
            {"id": "dominio_y_ll", "titulo": "Dominio Y/LL", "sub": "15 textos impecables", "emoji": "🗝️"},
            {"id": "dominio_tildes", "titulo": "Francotirador", "sub": "Rey de las tildes", "emoji": "🎯"},
            {"id": "dominio_h", "titulo": "Cazafantasmas", "sub": "Dominio de la H", "emoji": "👻"},
            {"id": "dominio_otros", "titulo": "Pluma de Oro", "sub": "Buena Escritura general", "emoji": "✍️"},
        ]

        # Renderizar insignias básicas
        html_insignias = "<div class='vitrina'>"
        for ins in todas_insignias:
            clase_extra = "insignia-earned" if ins["id"] in user_badges else ""
            
            # HTML compactado sin sangrías para evitar el bug de Markdown en Streamlit
            html_insignias += f"<div class='insignia-box'><div class='insignia-circle {clase_extra}'>{ins['emoji']}</div><div class='insignia-title'>{ins['titulo']}</div><div class='insignia-subtitle'>{ins['sub']}</div></div>"
            
        html_insignias += "</div>"
        
        st.markdown(html_insignias, unsafe_allow_html=True)
        # Renderizar la de Master centrada abajo, más espectacular
        clase_master = "insignia-earned insignia-master" if "master_ortografia" in user_badges else "insignia-master"
        st.markdown(f"""
        <div class='vitrina' style='margin-top: 0;'>
            <div class="insignia-box" style="width: 200px;">
                <div class="insignia-circle {clase_master}">
                    👑
                </div>
                <div class="insignia-title" style="font-size: 1.2rem; margin-top: 0.5rem;">Máster de la Ortografía</div>
                <div class="insignia-subtitle" style="font-size: 0.85rem;">Consigue todas las demás</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    except Exception as e:
        st.warning(f"Error cargando vitrina: {e}")
# =========================
# Main app
# =========================
def main_app():
    st.sidebar.title("Opciones")
    backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")

    if st.session_state.get("logged_in", False):
        st.sidebar.success(f"Sesión iniciada como: {st.session_state['usuario']}")
        inject_session_js(backend_url, st.session_state["usuario"])
        
        # --- NUEVO: Menú de navegación ---
        st.sidebar.markdown("---")
        modo_app = st.sidebar.selectbox(
            "📍 ¿A dónde quieres ir?", 
            ["📝 Corrector de Textos", "🏋️ Gimnasio Ortográfico", "📖 Repaso Teórico", "👤 Mi Perfil"]
        )
        st.sidebar.markdown("---")
        # ---------------------------------

        if st.sidebar.button("🔚 Cerrar sesión"):
            try:
                requests.post(f"{backend_url}/users/logout", data={"username": st.session_state['usuario']}, timeout=5)
            except Exception:
                pass
            st.session_state["logged_in"] = False
            st.session_state.pop("usuario", None)
            _clear_status_cache()
            _clear_metrics_cache()
            clear_current_analysis()
            st.rerun()

        if st.sidebar.button("🧹 Limpiar análisis actual"):
            clear_current_analysis()
            st.rerun()

    else:
        st.sidebar.write("No has iniciado sesión.")
        colL, colC = st.sidebar.columns(2)
        if colL.button("🔓 Iniciar sesión"):
            st.session_state["show_login"] = True
            st.session_state["show_create_account"] = False
            st.rerun()
        if colC.button("📝 Crear cuenta"):
            st.session_state["show_create_account"] = True
            st.session_state["show_login"] = False
            st.rerun()

    if st.session_state.get("logged_in", False):
        if modo_app == "🏋️ Gimnasio Ortográfico":
            mostrar_gimnasio(backend_url, st.session_state["usuario"])
            return 
        elif modo_app == "📖 Repaso Teórico":
            mostrar_repaso()
            return
        elif modo_app == "👤 Mi Perfil":
            mostrar_perfil(st.session_state["usuario"], backend_url)
            return
    
    st.title("📝 PALABRIA - Corrector de Textos")

    if st.session_state.get("show_login", False):
        login()
        return
    elif st.session_state.get("show_create_account", False):
        create_account()
        return

    st.title("📝 PALABRIA - Corrector de Textos")

    if "usuario" not in st.session_state:
        st.warning("Por favor, selecciona una opción en la barra lateral.")
        return

    # Dispara carga del modelo una vez
    if "load_disparado" not in st.session_state:
        st.session_state["load_disparado"] = False
    if not st.session_state["load_disparado"]:
        try:
            requests.post(f"{backend_url}/load/", timeout=5)
        except Exception:
            pass
        st.session_state["load_disparado"] = True

    st.markdown("<h2 class='h-section'>Estado del modelo</h2>", unsafe_allow_html=True)
    render_status(backend_url)

    if not st.session_state.get("modelo_listo", False):
        return

    st.markdown("<div class='spacer-1cm'></div>", unsafe_allow_html=True)
    st.markdown("<h2 class='h-section'>📤 ANALIZA TU PDF O PEGA TU TEXTO</h2>", unsafe_allow_html=True)

    # =========================
    # NEW: selector de modo
    # =========================
    st.markdown("<h2 class='h-section'>Modo de corrección</h2>", unsafe_allow_html=True)
    
    def on_mode_change():
        st.session_state["last_input_digest"] = None

    mode_label = st.radio(
        " ", 
        list(MODE_OPTIONS.keys()), 
        on_change=on_mode_change, 
        horizontal=False, 
        label_visibility="collapsed"
    )

    selected_mode = MODE_OPTIONS[mode_label]
    st.caption(f"Modo seleccionado: **{selected_mode}**")

    st.markdown("<h2 class='h-section'>Fuente de entrada</h2>", unsafe_allow_html=True)
    modo_entrada = st.radio(" ", ["Subir PDF", "Escribir texto"], horizontal=True, label_visibility="collapsed")

    texto_plano = None
    uploaded_file = None
    file_bytes = None
    digest = None

    if "last_input_digest" not in st.session_state:
        st.session_state["last_input_digest"] = None
    if "last_doc_id" not in st.session_state:
        st.session_state["last_doc_id"] = None
    if "last_analysis" not in st.session_state:
        st.session_state["last_analysis"] = None

    # =========================
    # PDF flow
    # =========================
    if modo_entrada == "Subir PDF":
        st.markdown("<h2 class='h-section'>Sube tu PDF</h2>", unsafe_allow_html=True)
        uploaded_file = st.file_uploader("", type=["pdf"], label_visibility="collapsed")

        if uploaded_file is not None:
            file_bytes = uploaded_file.getvalue()
            digest = hashlib.sha256(file_bytes + selected_mode.encode("utf-8")).hexdigest()

        should_process = (uploaded_file is not None) and (digest != st.session_state.get("last_input_digest"))

        if should_process:
            with st.spinner("Analizando el PDF..."):
                files = {'file': (uploaded_file.name, file_bytes, "application/pdf")}
                data = {'username': st.session_state["usuario"], 'mode': selected_mode}
                response = requests.post(f"{backend_url}/process/", files=files, data=data, timeout=180)

            if response.status_code == 200:
                data = response.json()
                st.session_state["last_input_digest"] = digest
                st.session_state["last_pdf_name"] = uploaded_file.name
                st.session_state["last_doc_id"] = data.get("doc_id")

                corrected = data.get("corrected", "")
                if not isinstance(corrected, str):
                    corrected = str(corrected)

                st.session_state["last_analysis"] = {
                    "original_text": data.get("original_text", ""),
                    "metricas": data.get("metricas", {}),
                    "corrected_text": corrected,
                    "feedback": data.get("feedback", ""),
                    "mode_used": data.get("mode_used", selected_mode),
                }
                st.session_state["edited_text_area"] = corrected
                st.session_state["__edited_for_doc"] = st.session_state["last_doc_id"]
            else:
                st.error(f"❌ Error al procesar el PDF (código {response.status_code})")
                try:
                    st.code(response.text, language="json")
                except Exception:
                    st.write(response.text)
                st.stop()

    # =========================
    # Text flow
    # =========================
    else:
        st.markdown("<h2 class='h-section'>Escribir texto</h2>", unsafe_allow_html=True)
        texto_plano = st.text_area("Pega aquí tu texto", height=200, key="__input_texto_plano")

        default_name = st.session_state.get("__input_filename", "mi_texto.txt")
        nombre_doc = st.text_input("Nombre del documento", value=default_name, key="__input_filename")

        nombre_doc_norm = (nombre_doc or "mi_texto.txt").strip()
        if "." not in nombre_doc_norm:
            nombre_doc_norm += ".txt"

        col_a, col_b = st.columns([1, 3])
        if col_a.button("Analizar texto"):
            if not texto_plano or not texto_plano.strip():
                st.warning("Escribe algún texto antes de analizar.")
            else:
                st.session_state.pop("edited_text_area", None)
                st.session_state["last_analysis"] = None
                digest = hashlib.sha256(((texto_plano or "") + "|" + selected_mode).encode("utf-8")).hexdigest()
                if digest != st.session_state.get("last_input_digest"):
                    with st.spinner("Analizando el texto..."):
                        data = {
                            'username': st.session_state["usuario"],
                            'text': texto_plano,
                            'filename': nombre_doc_norm,
                            'mode': selected_mode,
                        }
                        response = requests.post(f"{backend_url}/process_text/", data=data, timeout=180)

                    if response.status_code == 200:
                        resp = response.json()
                        st.session_state["last_input_digest"] = digest
                        st.session_state["last_pdf_name"] = nombre_doc_norm
                        st.session_state["last_doc_id"] = resp.get("doc_id")

                        corrected = resp.get("corrected", "")
                        if not isinstance(corrected, str):
                            corrected = str(corrected)

                        st.session_state["last_analysis"] = {
                            "original_text": resp.get("original_text", ""),
                            "metricas": resp.get("metricas", {}),
                            "corrected_text": corrected,
                            "feedback": resp.get("feedback", ""),
                            "mode_used": resp.get("mode_used", selected_mode),
                        }
                        st.session_state["edited_text_area"] = corrected
                        st.session_state["__edited_for_doc"] = st.session_state["last_doc_id"]
                    else:
                        st.error(f"❌ Error al procesar el texto (código {response.status_code})")
                        try:
                            st.code(response.text, language="json")
                        except Exception:
                            st.write(response.text)
                        st.stop()

    st.markdown("<div class='spacer-tabs'></div>", unsafe_allow_html=True)
    st.markdown("<hr>", unsafe_allow_html=True)

    # 👇 Fíjate que aquí ya no hay 'with tabs[0]:', va directo el 'if'
    if has_current_analysis():
        anal = st.session_state["last_analysis"]
        metricas = anal.get("metricas", {})
        original_joined = anal.get("original_text", "")
        corrected_text = anal.get("corrected_text", "") or ""
        mode_used = anal.get("mode_used", "")

        st.markdown("<h2 class='h-section'>⚙️ Modo usado</h2>", unsafe_allow_html=True)
        st.info(mode_used or "(sin modo)")
        
        # ... (aquí sigue todo el código que ya tenías de las métricas del texto actual, 
        # el texto original, la salida del modelo, el feedback y el botón de descargar PDF) ...
        
    else:
        st.info("No hay análisis activo. Sube un PDF o escribe texto y pulsa “Analizar texto”.")
    

def obtener_ejercicios_backend(backend_url, username, categoria):
    """Obtiene palabras de la bolsa del usuario y las formatea como tarjetas."""
    try:
        r = requests.get(f"{backend_url}/users/{username}/ejercicios", timeout=10)
        if r.ok:
            palabras_bolsa = r.json().get("ejercicios", [])
            ejercicios_formateados = []
            for p in palabras_bolsa:
                # Filtramos por categoría si no es REMIX
                cat_db = p["categoria"].upper()
                if categoria != "REMIX" and cat_db not in categoria:
                    continue
                
                # Para los errores del backend, creamos un ejercicio de elegir la correcta
                opciones = [p["palabra_correcta"], p["palabra_fallada"]]
                random.shuffle(opciones)
                ejercicios_formateados.append({
                    "masked": "¿Cómo se escribe?", 
                    "opciones": opciones, 
                    "correcta": p["palabra_correcta"], 
                    "palabra": p["palabra_correcta"],
                    "backend_id": p["id"] # ¡Clave para luego restar el acierto!
                })
            return ejercicios_formateados
    except Exception as e:
        st.error(f"Error cargando tu bolsa de palabras: {e}")
    return []

def mostrar_gimnasio(backend_url, username):
    st.markdown("""
    <style>
    .gym-card {
        background: linear-gradient(135deg, #e0eafc, #cfdef3);
        border-radius: 15px;
        padding: 2rem;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 2rem;
    }
    .gym-word {
        font-size: 3rem !important;
        font-weight: 800;
        color: #1e3a8a;
        letter-spacing: 2px;
        margin-bottom: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("<h1 style='text-align: center;'>🏋️ Gimnasio Ortográfico</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; font-size:1.1rem;'>Entrena tu mente. Las palabras que falles en el corrector aparecerán aquí para que las repases.</p>", unsafe_allow_html=True)
    st.markdown("<div class='spacer-1cm'></div>", unsafe_allow_html=True)

    # Inicializar estado del gimnasio
    if "gym_estado" not in st.session_state:
        st.session_state.gym_estado = "configuracion" # configuracion | jugando | resultados
        st.session_state.gym_preguntas = []
        st.session_state.gym_index = 0
        st.session_state.gym_score = 0

    if st.session_state.gym_estado == "configuracion":
        st.markdown("<h3 class='h-section'>1. Elige tu entrenamiento</h3>", unsafe_allow_html=True)
        categoria = st.selectbox("Categoría a repasar:", ["REMIX", "B_V", "G_J", "Y_LL", "C_Z", "H", "TILDES"])
        
        if st.button("🚀 ¡Empezar Entrenamiento!", use_container_width=True):
            
            # 1. Averiguar el nivel del usuario consultando el endpoint que creamos
            nivel_dificultad = "facil" # Por defecto si no hay datos es Fácil
            try:
                r_niveles = requests.get(f"{backend_url}/users/{username}/levels", timeout=5)
                if r_niveles.ok:
                    niveles_data = r_niveles.json().get("niveles", {})
                    
                    # Ver qué nivel tiene en esta categoría (o en general si es REMIX)
                    llave_nivel = "nivel_general" if categoria == "REMIX" else f"nivel_{categoria.lower()}"
                    nivel_usuario = niveles_data.get(llave_nivel, "")
                    
                    if "Avanzado" in nivel_usuario:
                        nivel_dificultad = "dificil"
                    elif "Medio" in nivel_usuario:
                        nivel_dificultad = "intermedio"
                    else:
                        nivel_dificultad = "facil"
            except Exception as e:
                pass # Si falla el backend, se queda en fácil
            
            # Notificamos al usuario de la dificultad adaptada
            st.toast(f"Adaptando gimnasio a tu nivel: {nivel_dificultad.upper()}", icon="🧠")

            # 2. Cargar palabras base de ese nivel específico
            preguntas = []
            if categoria == "REMIX":
                for cat, niveles_dict in EJERCICIOS_BASE.items():
                    preguntas.extend(niveles_dict.get(nivel_dificultad, []))
            else:
                preguntas.extend(EJERCICIOS_BASE.get(categoria, {}).get(nivel_dificultad, []))
            
            # 3. Cargar palabras de la bolsa del usuario (Sus propios fallos siempre salen)
            preguntas_backend = obtener_ejercicios_backend(backend_url, username, categoria)
            preguntas.extend(preguntas_backend)

            # 4. Mezclar y seleccionar 10 preguntas
            import random
            random.shuffle(preguntas)
            st.session_state.gym_preguntas = preguntas[:10]
            st.session_state.gym_index = 0
            st.session_state.gym_score = 0
            
            if len(st.session_state.gym_preguntas) > 0:
                st.session_state.gym_estado = "jugando"
                st.rerun()
            else:
                st.warning("No hay suficientes palabras para esta categoría. ¡Prueba con REMIX!")
         
    elif st.session_state.gym_estado == "jugando":
        pregunta_actual = st.session_state.gym_preguntas[st.session_state.gym_index]
        total_preguntas = len(st.session_state.gym_preguntas)
        
        st.progress((st.session_state.gym_index) / total_preguntas)
        st.caption(f"Pregunta {st.session_state.gym_index + 1} de {total_preguntas}")

        # Tarjeta visual
        st.markdown(f"""
        <div class="gym-card">
            <div class="gym-word">{pregunta_actual['masked']}</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<h3 style='text-align:center;'>Selecciona la respuesta correcta:</h3>", unsafe_allow_html=True)
        
        cols = st.columns(len(pregunta_actual['opciones']))
        for i, opcion in enumerate(pregunta_actual['opciones']):
            if cols[i].button(opcion, key=f"btn_{st.session_state.gym_index}_{i}", use_container_width=True):
                # Verificar respuesta
                if opcion == pregunta_actual['correcta']:
                    st.toast("¡Correcto! 🎉", icon="✅")
                    st.session_state.gym_score += 1
                    
                    # Si es del backend, restar un acierto en la base de datos
                    if "backend_id" in pregunta_actual:
                        requests.post(f"{backend_url}/ejercicios/{pregunta_actual['backend_id']}/acierto", timeout=5)
                else:
                    st.toast(f"¡Oops! La correcta era '{pregunta_actual['palabra']}'", icon="❌")
                
                # Siguiente pregunta
                st.session_state.gym_index += 1
                if st.session_state.gym_index >= total_preguntas:
                    st.session_state.gym_estado = "resultados"
                st.rerun()

        if st.button("Abandonar entrenamiento", type="secondary"):
            st.session_state.gym_estado = "configuracion"
            st.rerun()

    elif st.session_state.gym_estado == "resultados":
        st.balloons()
        st.markdown("<div class='gym-card'>", unsafe_allow_html=True)
        st.markdown("<h2 style='color: #1e3a8a;'>¡Entrenamiento Completado! 🏆</h2>", unsafe_allow_html=True)
        st.markdown(f"<h1>{st.session_state.gym_score} / {len(st.session_state.gym_preguntas)}</h1>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
        if st.button("Volver al Gimnasio", use_container_width=True):
            st.session_state.gym_estado = "configuracion"
            st.rerun()

if __name__ == "__main__":
    main_app()