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
import base64

def get_base64_image(image_path):
    """Convierte una imagen local a un formato que el HTML puede leer directamente."""
    try:
        with open(image_path, "rb") as img_file:
            encoded_string = base64.b64encode(img_file.read()).decode()
        return f"data:image/png;base64,{encoded_string}"
    except Exception:
        return "👑"  
    
EJERCICIOS_BASE = {
    "B_V": {
        "facil": [
            {"masked": "a_uela", "opciones": ["b", "v"], "correcta": "b", "palabra": "abuela"},
            {"masked": "in_ierno", "opciones": ["b", "v"], "correcta": "v", "palabra": "invierno"},
            {"masked": "camina_a", "opciones": ["b", "v"], "correcta": "b", "palabra": "caminaba"},
            {"masked": "nue_o", "opciones": ["b", "v"], "correcta": "v", "palabra": "nuevo"},
            {"masked": "_arco", "opciones": ["b", "v"], "correcta": "b", "palabra": "barco"},
            {"masked": "_aso", "opciones": ["b", "v"], "correcta": "v", "palabra": "vaso"},
            {"masked": "_lanco", "opciones": ["b", "v"], "correcta": "b", "palabra": "blanco"},
            {"masked": "_erde", "opciones": ["b", "v"], "correcta": "v", "palabra": "verde"},
            {"masked": "_eber", "opciones": ["b", "v"], "correcta": "b", "palabra": "beber"},
            {"masked": "_olar", "opciones": ["b", "v"], "correcta": "v", "palabra": "volar"}
        ],
        "intermedio": [
            {"masked": "_izcocho", "opciones": ["b", "v"], "correcta": "b", "palabra": "bizcocho"},
            {"masked": "mo_ilidad", "opciones": ["b", "v"], "correcta": "v", "palabra": "movilidad"},
            {"masked": "ob_io", "opciones": ["b", "v"], "correcta": "v", "palabra": "obvio"},
            {"masked": "her_ir", "opciones": ["b", "v"], "correcta": "v", "palabra": "hervir"},
            {"masked": "vaga_undo", "opciones": ["b", "v"], "correcta": "b", "palabra": "vagabundo"},
            {"masked": "ad_ertir", "opciones": ["b", "v"], "correcta": "v", "palabra": "advertir"},
            {"masked": "a_sorber", "opciones": ["b", "v"], "correcta": "b", "palabra": "absorber"},
            {"masked": "ci_ilidad", "opciones": ["b", "v"], "correcta": "v", "palabra": "civilidad"},
            {"masked": "canta_an", "opciones": ["b", "v"], "correcta": "b", "palabra": "cantaban"},
            {"masked": "sua_e", "opciones": ["b", "v"], "correcta": "v", "palabra": "suave"}
        ],
        "dificil": [
            {"masked": "exacer_ar", "opciones": ["b", "v"], "correcta": "b", "palabra": "exacerbar"},
            {"masked": "nausea_undo", "opciones": ["b", "v"], "correcta": "b", "palabra": "nauseabundo"},
            {"masked": "longe_o", "opciones": ["b", "v"], "correcta": "v", "palabra": "longevo"},
            {"masked": "preca_er", "opciones": ["b", "v"], "correcta": "v", "palabra": "precaver"},
            {"masked": "acer_o (patrimonio)", "opciones": ["b", "v"], "correcta": "v", "palabra": "acervo"},
            {"masked": "omní_oro", "opciones": ["b", "v"], "correcta": "v", "palabra": "omnívoro"},
            {"masked": "sub_ersivo", "opciones": ["b", "v"], "correcta": "v", "palabra": "subversivo"},
            {"masked": "bene_olencia", "opciones": ["b", "v"], "correcta": "v", "palabra": "benevolencia"},
            {"masked": "ví_ora", "opciones": ["b", "v"], "correcta": "b", "palabra": "víbora"},
            {"masked": "absol_er", "opciones": ["b", "v"], "correcta": "v", "palabra": "absolver"}
        ]
    },
    "G_J": {
        "facil": [
            {"masked": "gara_e", "opciones": ["g", "j"], "correcta": "j", "palabra": "garaje"},
            {"masked": "_igante", "opciones": ["g", "j"], "correcta": "g", "palabra": "gigante"},
            {"masked": "via_e", "opciones": ["g", "j"], "correcta": "j", "palabra": "viaje"},
            {"masked": "_ente", "opciones": ["g", "j"], "correcta": "g", "palabra": "gente"},
            {"masked": "_ugar", "opciones": ["g", "j"], "correcta": "j", "palabra": "jugar"},
            {"masked": "_irar", "opciones": ["g", "j"], "correcta": "g", "palabra": "girar"},
            {"masked": "_efe", "opciones": ["g", "j"], "correcta": "j", "palabra": "jefe"},
            {"masked": "_ato", "opciones": ["g", "j"], "correcta": "g", "palabra": "gato"},
            {"masked": "ro_o", "opciones": ["g", "j"], "correcta": "j", "palabra": "rojo"},
            {"masked": "ma_ia", "opciones": ["g", "j"], "correcta": "g", "palabra": "magia"}
        ],
        "intermedio": [
            {"masked": "extran_ero", "opciones": ["g", "j"], "correcta": "j", "palabra": "extranjero"},
            {"masked": "co_er", "opciones": ["g", "j"], "correcta": "g", "palabra": "coger"},
            {"masked": "te_er", "opciones": ["g", "j"], "correcta": "j", "palabra": "tejer"},
            {"masked": "prote_er", "opciones": ["g", "j"], "correcta": "g", "palabra": "proteger"},
            {"masked": "ru_ir", "opciones": ["g", "j"], "correcta": "j", "palabra": "rugir"},
            {"masked": "sumer_ir", "opciones": ["g", "j"], "correcta": "g", "palabra": "sumergir"},
            {"masked": "mensa_e", "opciones": ["g", "j"], "correcta": "j", "palabra": "mensaje"},
            {"masked": "fin_ir", "opciones": ["g", "j"], "correcta": "g", "palabra": "fingir"},
            {"masked": "pea_e", "opciones": ["g", "j"], "correcta": "j", "palabra": "peaje"},
            {"masked": "cerra_ería", "opciones": ["g", "j"], "correcta": "j", "palabra": "cerrajería"}
        ],
        "dificil": [
            {"masked": "he_emonía", "opciones": ["g", "j"], "correcta": "g", "palabra": "hegemonía"},
            {"masked": "cru_ir", "opciones": ["g", "j"], "correcta": "j", "palabra": "crujir"},
            {"masked": "ambi_uo", "opciones": ["g", "j"], "correcta": "g", "palabra": "ambiguo"},
            {"masked": "para_e", "opciones": ["g", "j"], "correcta": "j", "palabra": "paraje"},
            {"masked": "here_ía", "opciones": ["g", "j"], "correcta": "j", "palabra": "herejía"},
            {"masked": "amba_es", "opciones": ["g", "j"], "correcta": "g", "palabra": "ambages"},
            {"masked": "esfin_e", "opciones": ["g", "j"], "correcta": "g", "palabra": "esfinge"},
            {"masked": "cónyu_e", "opciones": ["g", "j"], "correcta": "g", "palabra": "cónyuge"},
            {"masked": "demago_ia", "opciones": ["g", "j"], "correcta": "g", "palabra": "demagogia"},
            {"masked": "apople_ía", "opciones": ["g", "j"], "correcta": "j", "palabra": "apoplejía"}
        ]
    },
    "Y_LL": {
        "facil": [
            {"masked": "_ogur", "opciones": ["y", "ll"], "correcta": "y", "palabra": "yogur"},
            {"masked": "caba_o", "opciones": ["y", "ll"], "correcta": "ll", "palabra": "caballo"},
            {"masked": "a_er", "opciones": ["y", "ll"], "correcta": "y", "palabra": "ayer"},
            {"masked": "ca_e", "opciones": ["y", "ll"], "correcta": "ll", "palabra": "calle"},
            {"masked": "_uvia", "opciones": ["y", "ll"], "correcta": "ll", "palabra": "lluvia"},
            {"masked": "pla_a", "opciones": ["y", "ll"], "correcta": "y", "palabra": "playa"},
            {"masked": "_orar", "opciones": ["y", "ll"], "correcta": "ll", "palabra": "llorar"},
            {"masked": "ma_o", "opciones": ["y", "ll"], "correcta": "y", "palabra": "mayo"},
            {"masked": "_ave", "opciones": ["y", "ll"], "correcta": "ll", "palabra": "llave"},
            {"masked": "a_uda", "opciones": ["y", "ll"], "correcta": "y", "palabra": "ayuda"}
        ],
        "intermedio": [
            {"masked": "pro_ecto", "opciones": ["y", "ll"], "correcta": "y", "palabra": "proyecto"},
            {"masked": "deta_e", "opciones": ["y", "ll"], "correcta": "ll", "palabra": "detalle"},
            {"masked": "atrope_ar", "opciones": ["y", "ll"], "correcta": "ll", "palabra": "atropellar"},
            {"masked": "in_ección", "opciones": ["y", "ll"], "correcta": "y", "palabra": "inyección"},
            {"masked": "zapati_a", "opciones": ["y", "ll"], "correcta": "ll", "palabra": "zapatilla"},
            {"masked": "tra_ecto", "opciones": ["y", "ll"], "correcta": "y", "palabra": "trayecto"},
            {"masked": "murmu_o", "opciones": ["y", "ll"], "correcta": "ll", "palabra": "murmullo"},
            {"masked": "jo_a", "opciones": ["y", "ll"], "correcta": "y", "palabra": "joya"},
            {"masked": "rodi_a", "opciones": ["y", "ll"], "correcta": "ll", "palabra": "rodilla"},
            {"masked": "re_es", "opciones": ["y", "ll"], "correcta": "y", "palabra": "reyes"}
        ],
        "dificil": [
            {"masked": "subra_ar", "opciones": ["y", "ll"], "correcta": "y", "palabra": "subrayar"},
            {"masked": "zambu_ir", "opciones": ["y", "ll"], "correcta": "ll", "palabra": "zambullir"},
            {"masked": "plebe_o", "opciones": ["y", "ll"], "correcta": "y", "palabra": "plebeyo"},
            {"masked": "_acer", "opciones": ["y", "ll"], "correcta": "y", "palabra": "yacer"},
            {"masked": "abo_ar", "opciones": ["y", "ll"], "correcta": "ll", "palabra": "abollar"},
            {"masked": "epope_a", "opciones": ["y", "ll"], "correcta": "y", "palabra": "epopeya"},
            {"masked": "sosla_ar", "opciones": ["y", "ll"], "correcta": "y", "palabra": "soslayar"},
            {"masked": "quere_a", "opciones": ["y", "ll"], "correcta": "ll", "palabra": "querella"},
            {"masked": "convo_es", "opciones": ["y", "ll"], "correcta": "y", "palabra": "convoyes"},
            {"masked": "au_ar", "opciones": ["y", "ll"], "correcta": "ll", "palabra": "aullar"}
        ]
    },
    "C_Z": {
        "facil": [
            {"masked": "cora_ón", "opciones": ["c", "z", "s"], "correcta": "z", "palabra": "corazón"},
            {"masked": "pe_es", "opciones": ["c", "z", "s"], "correcta": "c", "palabra": "peces"},
            {"masked": "ta_a", "opciones": ["c", "z", "s"], "correcta": "z", "palabra": "taza"},
            {"masked": "_ielo", "opciones": ["c", "z", "s"], "correcta": "c", "palabra": "cielo"},
            {"masked": "_apato", "opciones": ["c", "z", "s"], "correcta": "z", "palabra": "zapato"},
            {"masked": "_apo", "opciones": ["c", "z", "s"], "correcta": "s", "palabra": "sapo"},
            {"masked": "_irco", "opciones": ["c", "z", "s"], "correcta": "c", "palabra": "circo"},
            {"masked": "_orro", "opciones": ["c", "z", "s"], "correcta": "z", "palabra": "zorro"},
            {"masked": "_opa", "opciones": ["c", "z", "s"], "correcta": "s", "palabra": "sopa"},
            {"masked": "_ine", "opciones": ["c", "z", "s"], "correcta": "c", "palabra": "cine"}
        ],
        "intermedio": [
            {"masked": "deci_ión", "opciones": ["c", "z", "s"], "correcta": "s", "palabra": "decisión"},
            {"masked": "ilu_ión", "opciones": ["c", "z", "s"], "correcta": "s", "palabra": "ilusión"},
            {"masked": "ambi_ión", "opciones": ["c", "z", "s"], "correcta": "c", "palabra": "ambición"},
            {"masked": "can_ión", "opciones": ["c", "z", "s"], "correcta": "c", "palabra": "canción"},
            {"masked": "pere_a", "opciones": ["c", "z", "s"], "correcta": "z", "palabra": "pereza"},
            {"masked": "pala_io", "opciones": ["c", "z", "s"], "correcta": "c", "palabra": "palacio"},
            {"masked": "trave_ía", "opciones": ["c", "z", "s"], "correcta": "s", "palabra": "travesía"},
            {"masked": "calaba_a", "opciones": ["c", "z", "s"], "correcta": "z", "palabra": "calabaza"},
            {"masked": "velo_idad", "opciones": ["c", "z", "s"], "correcta": "c", "palabra": "velocidad"},
            {"masked": "compa_ión", "opciones": ["c", "z", "s"], "correcta": "s", "palabra": "compasión"}
        ],
        "dificil": [
            {"masked": "idiosincra_ia", "opciones": ["c", "z", "s"], "correcta": "s", "palabra": "idiosincrasia"},
            {"masked": "ascen_ión", "opciones": ["c", "z", "s"], "correcta": "s", "palabra": "ascensión"},
            {"masked": "exacerba_ión", "opciones": ["c", "z", "s"], "correcta": "c", "palabra": "exacerbación"},
            {"masked": "vicisi_ud", "opciones": ["c", "z", "s"], "correcta": "t", "palabra": "vicisitud"}, # Trampa de T, pero dejaremos s/t en un nivel general, o usemos otra
            {"masked": "suspica_ia", "opciones": ["c", "z", "s"], "correcta": "c", "palabra": "suspicacia"},
            {"masked": "locua_idad", "opciones": ["c", "z", "s"], "correcta": "c", "palabra": "locuacidad"},
            {"masked": "zo_obra", "opciones": ["c", "z", "s"], "correcta": "z", "palabra": "zozobra"},
            {"masked": "efervescen_ia", "opciones": ["c", "z", "s"], "correcta": "c", "palabra": "efervescencia"},
            {"masked": "perspica_", "opciones": ["c", "z", "s"], "correcta": "z", "palabra": "perspicaz"},
            {"masked": "concupiscen_ia", "opciones": ["c", "z", "s"], "correcta": "c", "palabra": "concupiscencia"}
        ]
    },
    "H": {
        "facil": [
            {"masked": "_ielo", "opciones": ["h", "Ø (nada)"], "correcta": "h", "palabra": "hielo"},
            {"masked": "_orario", "opciones": ["h", "Ø (nada)"], "correcta": "h", "palabra": "horario"},
            {"masked": "_ojalá", "opciones": ["h", "Ø (nada)"], "correcta": "Ø (nada)", "palabra": "ojalá"},
            {"masked": "_ueso", "opciones": ["h", "Ø (nada)"], "correcta": "h", "palabra": "hueso"},
            {"masked": "_acer", "opciones": ["h", "Ø (nada)"], "correcta": "h", "palabra": "hacer"},
            {"masked": "_ola (saludo)", "opciones": ["h", "Ø (nada)"], "correcta": "h", "palabra": "hola"},
            {"masked": "_ola (del mar)", "opciones": ["h", "Ø (nada)"], "correcta": "Ø (nada)", "palabra": "ola"},
            {"masked": "_umo", "opciones": ["h", "Ø (nada)"], "correcta": "h", "palabra": "humo"},
            {"masked": "_orno", "opciones": ["h", "Ø (nada)"], "correcta": "h", "palabra": "horno"},
            {"masked": "_uerto", "opciones": ["h", "Ø (nada)"], "correcta": "h", "palabra": "huerto"}
        ],
        # ---> ATENCIÓN: ESTE ES EL NIVEL DE LA DEMO <---
        "intermedio": [
            {"masked": "almo_ada", "opciones": ["h", "Ø (nada)"], "correcta": "h", "palabra": "almohada"},
            {"masked": "ex_ibición", "opciones": ["h", "Ø (nada)"], "correcta": "h", "palabra": "exhibición"},
            {"masked": "zana_oria", "opciones": ["h", "Ø (nada)"], "correcta": "h", "palabra": "zanahoria"},
            {"masked": "co_ete", "opciones": ["h", "Ø (nada)"], "correcta": "h", "palabra": "cohete"},
            {"masked": "caca_uete", "opciones": ["h", "Ø (nada)"], "correcta": "h", "palabra": "cacahuete"},
            {"masked": "_echo (del verbo echar)", "opciones": ["h", "Ø (nada)"], "correcta": "Ø (nada)", "palabra": "echo"},
            {"masked": "a_ogar", "opciones": ["h", "Ø (nada)"], "correcta": "h", "palabra": "ahogar"},
            {"masked": "ba_ía", "opciones": ["h", "Ø (nada)"], "correcta": "h", "palabra": "bahía"},
            {"masked": "bú_o", "opciones": ["h", "Ø (nada)"], "correcta": "h", "palabra": "búho"},
            {"masked": "pro_ibir", "opciones": ["h", "Ø (nada)"], "correcta": "h", "palabra": "prohibir"}
        ],
        "dificil": [
            {"masked": "e_xhaustivo", "opciones": ["h", "Ø (nada)"], "correcta": "h", "palabra": "exhaustivo"},
            {"masked": "in_erente", "opciones": ["h", "Ø (nada)"], "correcta": "h", "palabra": "inherente"},
            {"masked": "ve_emencia", "opciones": ["h", "Ø (nada)"], "correcta": "h", "palabra": "vehemencia"},
            {"masked": "ex_uberante", "opciones": ["h", "Ø (nada)"], "correcta": "Ø (nada)", "palabra": "exuberante"},
            {"masked": "_uelga", "opciones": ["h", "Ø (nada)"], "correcta": "h", "palabra": "huelga"},
            {"masked": "en_ebrar", "opciones": ["h", "Ø (nada)"], "correcta": "h", "palabra": "enhebrar"},
            {"masked": "reta_íla", "opciones": ["h", "Ø (nada)"], "correcta": "h", "palabra": "retahíla"},
            {"masked": "tras_umante", "opciones": ["h", "Ø (nada)"], "correcta": "h", "palabra": "trashumante"},
            {"masked": "aza_ar", "opciones": ["h", "Ø (nada)"], "correcta": "h", "palabra": "azahar"},
            {"masked": "in_óspito", "opciones": ["h", "Ø (nada)"], "correcta": "h", "palabra": "inhóspito"}
        ]
    },
    "TILDES": {
        "facil": [
            {"masked": "canci_n", "opciones": ["o", "ó"], "correcta": "ó", "palabra": "canción"},
            {"masked": "arbol", "opciones": ["a", "á"], "correcta": "á", "palabra": "árbol"},
            {"masked": "exam_n", "opciones": ["e", "é"], "correcta": "e", "palabra": "examen"},
            {"masked": "cami_n", "opciones": ["o", "ó"], "correcta": "ó", "palabra": "camión"},
            {"masked": "p_jaro", "opciones": ["a", "á"], "correcta": "á", "palabra": "pájaro"},
            {"masked": "l_piz", "opciones": ["a", "á"], "correcta": "á", "palabra": "lápiz"},
            {"masked": "caf_", "opciones": ["e", "é"], "correcta": "é", "palabra": "café"},
            {"masked": "m_sa", "opciones": ["e", "é"], "correcta": "e", "palabra": "mesa"},
            {"masked": "s_l", "opciones": ["o", "ó"], "correcta": "o", "palabra": "sol"},
            {"masked": "mel_n", "opciones": ["o", "ó"], "correcta": "ó", "palabra": "melón"}
        ],
        "intermedio": [
            {"masked": "r_pido", "opciones": ["a", "á"], "correcta": "á", "palabra": "rápido"},
            {"masked": "vol_men", "opciones": ["u", "ú"], "correcta": "u", "palabra": "volumen"},
            {"masked": "car_cter", "opciones": ["a", "á"], "correcta": "á", "palabra": "carácter"},
            {"masked": "jov_n", "opciones": ["e", "é"], "correcta": "e", "palabra": "joven"},
            {"masked": "m_rmol", "opciones": ["a", "á"], "correcta": "á", "palabra": "mármol"},
            {"masked": "resum_n", "opciones": ["e", "é"], "correcta": "e", "palabra": "resumen"},
            {"masked": "_til", "opciones": ["u", "ú"], "correcta": "ú", "palabra": "útil"},
            {"masked": "c_rcel", "opciones": ["a", "á"], "correcta": "á", "palabra": "cárcel"},
            {"masked": "dif_cil", "opciones": ["i", "í"], "correcta": "í", "palabra": "difícil"},
            {"masked": "cr_ter", "opciones": ["a", "á"], "correcta": "á", "palabra": "cráter"}
        ],
        "dificil": [
            {"masked": "transe_nte", "opciones": ["u", "ú"], "correcta": "ú", "palabra": "transeúnte"},
            {"masked": "sutilm_nte", "opciones": ["e", "é"], "correcta": "e", "palabra": "sutilmente"},
            {"masked": "re_unir", "opciones": ["e", "é"], "correcta": "e", "palabra": "reunir"},
            {"masked": "historico-critico", "opciones": ["o-i", "ó-í"], "correcta": "ó-í", "palabra": "histórico-crítico"},
            {"masked": "corta_ñas", "opciones": ["u", "ú"], "correcta": "ú", "palabra": "cortaúñas"},
            {"masked": "veintid_s", "opciones": ["o", "ó"], "correcta": "ó", "palabra": "veintidós"},
            {"masked": "f_rceps", "opciones": ["o", "ó"], "correcta": "ó", "palabra": "fórceps"},
            {"masked": "gui_n", "opciones": ["o", "ó"], "correcta": "o", "palabra": "guion"},
            {"masked": "tiov_vo", "opciones": ["i", "í"], "correcta": "i", "palabra": "tiovivo"},
            {"masked": "decimos_ptimo", "opciones": ["e", "é"], "correcta": "é", "palabra": "decimoséptimo"}
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

MODE_OPTIONS = {
    "📝 Ortografía completa (B/V, G/J, Y/LL, H, C/Z, tildes)": "ortografia",
    "👤 Tú impersonal → impersonal con “se”": "tu_impersonal",
}

# =========================
# CSS
# =========================
st.markdown("""
<style>
form[data-testid="stForm"] { margin-top: 5rem !important; }
div[data-testid="stVegaLiteChart"] { margin-bottom: -0.5rem !important; }
.spacer-1cm { height: 0.25rem; }
.spacer-tabs { height: 1.1rem; }
.block-container { padding-top: 2.0rem; padding-bottom: 1.5rem; }
.h-section, .stMarkdown h2, .stMarkdown h3 { font-size: 1.25rem !important; font-weight: 700 !important; margin-top: .5rem !important; margin-bottom: 0 !important; line-height: 1.2; color: #111827; }
[data-testid="stVerticalBlock"] > div { margin-bottom: 0.3rem; }
.stTabs { margin-top: 0.35rem; }
.stTabs [data-baseweb="tab"], .stTabs button[role="tab"] { font-size: 1.30rem !important; font-weight: 700 !important; padding: .50rem 1.00rem !important; border: 1px solid rgba(49,51,63,0.12) !important; border-radius: .55rem !important; background: #fff !important; margin-right: .5rem !important; line-height: 1.2 !important; min-height: 2.4rem !important; }
.stTabs [aria-selected="true"], .stTabs button[role="tab"][aria-selected="true"] { border-color: #2563eb !important; box-shadow: 0 0 0 2px rgba(37,99,235,0.08) inset !important; }
div[data-testid="stMetric"] { padding: 0.5rem 0.6rem !important; border: 1px solid rgba(49,51,63,0.15) !important; border-radius: 0.5rem !important; background: #ffffff !important; text-align: center !important; box-shadow: 0 1px 2px rgba(0,0,0,0.04); }
div[data-testid="stMetricLabel"] { font-size: 1rem !important; font-weight: 500 !important; color: #111827 !important; margin-bottom: 0.15rem !important; line-height: 1.15 !important; text-align: center !important; }
div[data-testid="stMetricValue"] { font-size: 1.15rem !important; font-weight: 600 !important; color: #000000 !important; text-align: center !important; line-height: 1.2 !important; }
.readonly-box { border: 1px solid rgba(49,51,63,0.2); border-radius: 0.5rem; padding: 0.5rem 0.6rem; background: #ffffff; color: inherit; font-family: inherit; line-height: 1.45; width: 100%; box-sizing: border-box; max-width: 100%; overflow-x: hidden; overflow-y: auto; min-height: 150px; max-height: 300px; }
.readonly-box[readonly] { background: #ffffff; color: inherit; cursor: default; }
div[data-testid="stRadio"], div[data-testid="stTextInput"], div[data-testid="stFileUploader"] { margin-top: -0.35rem !important; margin-bottom: -0.15rem !important; }
div[data-testid="stTextArea"] { overflow: visible !important; margin-right: 0 !important; padding-right: 0 !important; width: 100% !important; box-sizing: border-box !important; }
div[data-testid="stTextArea"] > div { overflow: visible !important; width: 100% !important; }
div[data-testid="stTextArea"] textarea { overflow-x: hidden !important; overflow-y: auto !important; width: 100% !important; max-width: 100% !important; box-sizing: border-box !important; resize: vertical !important; font-size: 1rem !important; line-height: 1.5 !important; border: 1px solid rgba(49,51,63,0.2) !important; border-radius: 0.5rem !important; padding: 0.5rem 0.6rem !important; background: #ffffff !important; }
</style>
""", unsafe_allow_html=True)

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
            return {"modelo_listo": bool(data.get("modelo_listo", False)), "progress": int(data.get("progress", 0)), "message": data.get("message", "⚡ Cargando…")}
    except Exception:
        return {"modelo_listo": False, "progress": 0, "message": "No conectado al backend."}
    return {"modelo_listo": False, "progress": 0, "message": "Desconocido"}

def _normalize_for_diff(text: str) -> str:
    if not text: return ""
    t = text.replace("…", "...").replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'").replace("—", "-").replace("–", "-").replace("\r\n", "\n").replace("\r", "\n")
    return t.strip()

def word_levenshtein_count(a_text: str, b_text: str) -> int:
    a_tokens = _normalize_for_diff(a_text).split()
    b_tokens = _normalize_for_diff(b_text).split()
    return int(L.distance(a_tokens, b_tokens))

def pretty_int(x):
    try:
        fx = float(x)
        return int(fx) if fx.is_integer() else fx
    except Exception: return x

def pretty_hms(seconds: float) -> str:
    try: s = int(round(float(seconds)))
    except Exception: s = 0
    h, m, ss = s // 3600, (s % 3600) // 60, s % 60
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
        return fetch(url, {{method: "POST", mode: "cors", headers: {{"Content-Type":"application/x-www-form-urlencoded"}}, body: formData.toString()}}).catch(()=>{{}});
      }}
      const sendHeartbeat = () => postForm(hbUrl, {{username}});
      sendHeartbeat(); setInterval(sendHeartbeat, 20000);
      function beaconLogout() {{ try {{ if (!navigator.sendBeacon) {{ postForm(loUrl, {{username}}); return; }} const data = new URLSearchParams(); data.append("username", username); const blob = new Blob([data.toString()], {{type: "application/x-www-form-urlencoded"}}); navigator.sendBeacon(loUrl, blob); }} catch (e) {{}} }}
      window.addEventListener("beforeunload", beaconLogout);
      document.addEventListener("visibilitychange", function(){{ if (document.visibilityState === "hidden") beaconLogout(); }});
    }})();
    </script>
    """
    st_html(js, height=0)

def has_current_analysis() -> bool:
    anal = st.session_state.get("last_analysis")
    return bool(anal.get("original_text") or anal.get("corrected_text")) if anal else False

def clear_current_analysis():
    for k in ["last_input_digest","last_pdf_name","last_doc_id","last_analysis","edited_text_area","__edited_for_doc"]:
        st.session_state.pop(k, None)

def _clear_status_cache():
    for k in ["modelo_listo","status_progress","status_message","notificado_listo","last_status_check"]:
        st.session_state.pop(k, None)

def _clear_metrics_cache():
    for k in ["__cache_overview","__cache_documents"]: st.session_state.pop(k, None)
    for k in list(st.session_state.keys()):
        if str(k).startswith("__cache_doc_"): st.session_state.pop(k, None)

def _fetch_and_cache_doc_metrics(backend_url, doc_id: int):
    try:
        m = requests.get(f"{backend_url}/documents/{doc_id}/metrics", timeout=20).json()["metrics"]
        st.session_state[f"__cache_doc_{doc_id}"] = m
    except Exception: pass

def _post_user_changes(backend_url, doc_id: int, changes: int):
    try:
        requests.post(f"{backend_url}/documents/{doc_id}/user_changes", data={"changes": changes}, timeout=10)
        st.session_state[f"__last_saved_changes_{doc_id}"] = int(changes)
        _fetch_and_cache_doc_metrics(backend_url, doc_id)
    except Exception: pass

# =========================
# Auth forms
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
                        try: msg = r.json().get("detail", r.text)
                        except Exception: msg = r.text
                        st.error(msg or "No se pudo iniciar sesión.")
                except Exception as e: st.error(f"Error conectando con backend: {e}")
            else: st.warning("Por favor, escribe un nombre de usuario.")

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
                        try: msg = r.json().get("detail", r.text)
                        except Exception: msg = r.text
                        st.error(msg or "No se pudo crear la cuenta.")
                except Exception as e: st.error(f"Error conectando con backend: {e}")
            else: st.warning("Por favor, escribe un nombre de usuario.")


# =========================
# VISTAS PROFESOR (ADMIN)
# =========================
def mostrar_admin_alumnos(backend_url):
    if st.session_state.get("admin_view_student"):
        if st.button("⬅️ Volver a la lista de alumnos", type="primary"):
            st.session_state.admin_view_student = None
            st.rerun()
        mostrar_perfil(st.session_state.admin_view_student, backend_url)
        return

    st.markdown("<h1 style='text-align: center; color: #1e3a8a;'>👥 Vista de Profesor: Mis Alumnos</h1>", unsafe_allow_html=True)
    st.markdown("<div class='spacer-1cm'></div>", unsafe_allow_html=True)
    
    try:
        r = requests.get(f"{backend_url}/admin/students", timeout=5)
        students = r.json().get("students", [])
    except Exception as e:
        st.error(f"Error cargando alumnos: {e}")
        return
        
    if not students:
        st.info("Aún no hay alumnos registrados en la plataforma.")
        return

    cols = st.columns(3, gap="large")
    for i, s in enumerate(students):
        col = cols[i % 3]
        with col:
            color_lvl = "#eab308" if "Medio" in s['nivel_general'] else "#22c55e" if "Avanzado" in s['nivel_general'] else "#ef4444" if "Bajo" in s['nivel_general'] else "#9ca3af"
            st.markdown(f"""
            <div style="background-color: #f8fafc; border: 2px solid #e2e8f0; border-radius: 15px; padding: 1.5rem; text-align: center; position: relative; margin-bottom: 1rem; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
                <div style="position: absolute; top: 10px; right: 10px; width: 25px; height: 25px; background-color: {color_lvl}; border-radius: 50%; border: 2px solid white;" title="{s['nivel_general']}"></div>
                <div style="font-size: 4.5rem; line-height: 1;">{s['avatar']}</div>
                <div style="font-weight: 800; font-size: 1.3rem; color: #1e3a8a; margin-top: 10px; word-break: break-word;">{s['username']}</div>
                <div style="color: #64748b; font-size: 0.9rem; font-weight: 500; margin-top: 5px;">Nivel: {s['nivel_general'].replace('🟢', '').replace('🟡', '').replace('🔴', '').replace('⚪', '').strip()}</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Ver Expediente", key=f"ver_{s['username']}", use_container_width=True):
                st.session_state.admin_view_student = s['username']
                st.rerun()

def mostrar_admin_metricas(backend_url):
    st.markdown("<h1 style='text-align: center; color: #1e3a8a;'>📊 Métricas Globales de la Clase</h1>", unsafe_allow_html=True)
    st.markdown("<div class='spacer-1cm'></div>", unsafe_allow_html=True)
    try:
        r = requests.get(f"{backend_url}/admin/metrics", timeout=5)
        data = r.json().get("metrics", {})
    except:
        st.warning("Error conectando con el backend para las métricas.")
        return
        
    c1, c2 = st.columns(2)
    c1.metric("👥 Total de Alumnos Registrados", data.get("total_students", 0))
    c2.metric("📄 Total de Documentos Analizados", data.get("total_docs", 0))
    
    st.markdown("<div class='spacer-1cm'></div>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["📝 Corrector de Textos", "🏋️ Gimnasio Ortográfico"])
    
    with tab1:
        avg_metrics = data.get("avg_metrics", {})
        if avg_metrics:
            st.markdown("<h3 class='h-section'>Tasa media de errores por regla</h3>", unsafe_allow_html=True)
            chart_data = []
            for k, v in avg_metrics.items():
                if k.startswith("errores_") and k != "errores_otros":
                    cat = k.replace("errores_", "").upper()
                    chart_data.append({"Regla": cat, "Errores Medios": v})
            
            if chart_data:
                import pandas as pd
                df = pd.DataFrame(chart_data)
                chart = alt.Chart(df).mark_bar(color="#3b82f6", cornerRadiusTopLeft=8, cornerRadiusTopRight=8).encode(
                    x=alt.X("Regla:N", sort="-y", title="Regla Ortográfica"),
                    y=alt.Y("Errores Medios:Q", title="Promedio de errores por documento"),
                    tooltip=[alt.Tooltip("Regla:N"), alt.Tooltip("Errores Medios:Q", format=".2f")]
                ).properties(height=350)
                st.altair_chart(chart, use_container_width=True)
        else:
            st.info("Todavía no hay suficientes datos en la clase para mostrar gráficas.")

    with tab2:
        st.markdown("<h3 class='h-section'>Rendimiento de los alumnos por nivel</h3>", unsafe_allow_html=True)
        try:
            r_gym = requests.get(f"{backend_url}/admin/gym_stats", timeout=5)
            gym_stats = r_gym.json().get("stats", [])
            if gym_stats:
                import pandas as pd
                df_gym = pd.DataFrame(gym_stats)
                chart_gym = alt.Chart(df_gym).mark_bar(cornerRadiusTopLeft=8, cornerRadiusTopRight=8).encode(
                    x=alt.X("nivel:N", title="Nivel de Dificultad", sort=["facil", "intermedio", "dificil"]),
                    y=alt.Y("avg_score:Q", title="% de Acierto Medio", scale=alt.Scale(domain=[0, 100])),
                    color=alt.Color("nivel:N", scale=alt.Scale(domain=["facil", "intermedio", "dificil"], range=["#22c55e", "#facc15", "#ef4444"]), legend=None),
                    tooltip=[
                        alt.Tooltip("nivel:N", title="Nivel"), 
                        alt.Tooltip("avg_score:Q", title="% Acierto", format=".1f"), 
                        alt.Tooltip("sessions:Q", title="Partidas jugadas")
                    ]
                ).properties(height=350)
                st.altair_chart(chart_gym, use_container_width=True)
            else:
                st.info("Aún no se han jugado partidas en el gimnasio.")
        except Exception as e:
            st.warning("No se pudo cargar el rendimiento del gimnasio.")


# =========================
# VISTA DE PERFIL (ALUMNO Y PROFE)
# =========================
def cargar_metricas(username, backend_url):
    ov = requests.get(f"{backend_url}/users/{username}/overview", timeout=20).json()
    docs = requests.get(f"{backend_url}/users/{username}/documents", timeout=20).json().get("documents", [])
    st.session_state["__cache_overview"] = ov
    st.session_state["__cache_documents"] = docs

def mostrar_perfil(username, backend_url):
    es_propietario = (st.session_state.get('usuario') == username)
    es_admin = (st.session_state.get('usuario') == 'admin')
    
    try:
        r_prof = requests.get(f"{backend_url}/users/{username}/profile", timeout=5)
        perfil = r_prof.json().get("profile", {}) if r_prof.ok else {"avatar": "🐼", "current_streak": 1, "active_feedback": None}
    except:
        perfil = {"avatar": "🐼", "current_streak": 1, "active_feedback": None}

    titulo = "👤 Mi Perfil" if es_propietario else f"👤 Perfil del Alumno: {username}"
    st.markdown(f"<h1 style='text-align: center; margin-bottom: 2rem;'>{titulo}</h1>", unsafe_allow_html=True)
    
    if es_admin:
        st.markdown("""
        <div style='background-color: #f8fafc; border: 2px dashed #3b82f6; border-radius: 10px; padding: 1.5rem; margin-bottom: 2rem;'>
            <h4 style='text-align: center; color: #1e3a8a; margin-top: 0;'>👨‍🏫 Enviar Feedback Rápido</h4>
            <p style='text-align: center; color: #64748b; font-size: 0.9rem;'>Elige una pegatina para premiar o animar al alumno.</p>
        </div>
        """, unsafe_allow_html=True)
        
        stickers = ["sticker_increible", "sticker_animo", "sticker_sigueasi", "sticker_mejor"]
        nombres_stickers = ["¡Increíble!", "¡Ánimo!", "¡Sigue así!", "Puede mejorar"]
        cols_stickers = st.columns(4)
        
        for i, st_name in enumerate(stickers):
            with cols_stickers[i]:
                s_b64 = get_base64_image(f"frontend/assets/{st_name}.png")
                st.markdown(f"<div style='text-align:center; margin-bottom: 10px;'><img src='{s_b64}' style='width: 80px; filter: drop-shadow(0px 4px 6px rgba(0,0,0,0.1));'></div>", unsafe_allow_html=True)
                if st.button(nombres_stickers[i], key=f"btn_send_{st_name}", use_container_width=True):
                    requests.post(f"{backend_url}/admin/students/{username}/feedback", data={"sticker": st_name})
                    st.toast(f"Pegatina '{nombres_stickers[i]}' enviada a {username}", icon="✅")
                    st.rerun()
        
        if perfil.get("active_feedback"):
            st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
            if st.button("❌ Quitar feedback actual", use_container_width=True):
                requests.post(f"{backend_url}/admin/students/{username}/feedback", data={"sticker": ""})
                st.rerun()
        
        st.markdown("<hr style='margin: 2rem 0;'/>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 2, 1])
    
    with c2:
        st.markdown(f"<div style='font-size: 6rem; text-align: center; line-height: 1;'>{perfil.get('avatar')}</div>", unsafe_allow_html=True)
        st.markdown(f"<h2 style='text-align: center; margin-top: 0.5rem;'>{username}</h2>", unsafe_allow_html=True)
        st.markdown(f"<h4 style='text-align: center; color: #f59e0b; margin-top: -10px;'>🔥 Racha actual: {perfil.get('current_streak')} días</h4>", unsafe_allow_html=True)
        
        if es_propietario:
            with st.expander("Cambiar Avatar", expanded=False):
                avatares = ['🐼', '🦊', '🐱', '🐶', '🦄', '🐸', '🦉', '🐙', '🦁', '🐻', '🐵', '🐮']
                idx = avatares.index(perfil.get("avatar")) if perfil.get("avatar") in avatares else 0
                nuevo_avatar = st.selectbox("Elige tu nuevo avatar", avatares, index=idx, key="sel_avatar_profile")
                if st.button("Guardar Avatar", use_container_width=True):
                    requests.post(f"{backend_url}/users/{username}/avatar", data={"avatar": nuevo_avatar})
                    st.session_state["mi_avatar"] = nuevo_avatar  
                    st.rerun()

    with c3:
        active_fb = perfil.get("active_feedback")
        if active_fb and active_fb != "":
            fb_b64 = get_base64_image(f"frontend/assets/{active_fb}.png")
            st.markdown(f"""
            <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; animation: floatSticker 3s ease-in-out infinite;">
                <div style="background: #ef4444; color: white; padding: 4px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: bold; margin-bottom: -5px; z-index: 10;">Mensaje del Profe</div>
                <img src='{fb_b64}' style='width: 120px; filter: drop-shadow(0px 10px 15px rgba(0,0,0,0.2));'>
            </div>
            <style>@keyframes floatSticker {{ 0% {{ transform: translateY(0px) rotate(0deg); }} 50% {{ transform: translateY(-10px) rotate(3deg); }} 100% {{ transform: translateY(0px) rotate(0deg); }} }}</style>
            """, unsafe_allow_html=True)

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
                nivel_gen = niveles.get("nivel_general", "⚪ Sin datos")
                color_bg = "#f3f4f6"
                color_border = "#d1d5db"
                if "Avanzado" in nivel_gen: color_bg, color_border = "#dcfce7", "#22c55e"
                elif "Medio" in nivel_gen: color_bg, color_border = "#fef08a", "#eab308"
                elif "Bajo" in nivel_gen: color_bg, color_border = "#fee2e2", "#ef4444"

                st.markdown(f"""
                <div style='text-align: center; padding: 1.5rem; background: {color_bg}; border-radius: 15px; border: 2px solid {color_border}; margin-bottom: 1.5rem; box-shadow: 0 4px 6px rgba(0,0,0,0.05);'>
                    <h3 style='margin:0; color: #374151; font-weight: 600;'>Nivel General Ortográfico</h3>
                    <h1 style='margin:0; font-size: 2.5rem; color: #111827;'>{nivel_gen}</h1>
                </div>
                """, unsafe_allow_html=True)
                
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
    div[data-testid="stMetric"] { display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center !important; }
    div[data-testid="stMetricLabel"] { text-align: center !important; justify-content: center !important; align-items: center !important; font-weight: 600 !important; }
    div[data-testid="stMetricValue"] { text-align: center !important; justify-content: center !important; align-items: center !important; font-weight: 500 !important; color: #000 !important; font-size: 0.97rem !important; }
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
            html_rows = ""
            for key in SHOW_KEYS:
                if key in avg_metrics:
                    label = PRETTY.get(key, key)
                    value = pretty_int(round(avg_metrics[key], 2))
                    html_rows += f"<div style='padding: 0.4rem 0.8rem; border-radius: 0.4rem; background-color: #f9fafb; margin-bottom: 0.25rem;'><span style='font-weight: 400; color: #374151;'>{label}</span><span style='float: right; font-weight: 500; color: #000000;'>{value}</span></div>"
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
                            color=alt.Color("categoria:N", title="Nivel de actividad", scale=alt.Scale(domain=order, range=["#ef4444","#f97316","#facc15","#22c55e","#3b82f6"])),
                            tooltip=[alt.Tooltip("day:T", title="Fecha"), alt.Tooltip("minutos:Q", title="Minutos totales", format=".1f"), alt.Tooltip("categoria:N", title="Nivel")],
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
                chart_prog = (
                    alt.Chart(df_prog)
                    .mark_line(point=True, strokeWidth=3, size=80)
                    .encode(
                        x=alt.X("doc_index:O", title="Textos evaluados cronológicamente (1 = más antiguo)"),
                        y=alt.Y("porcentaje_error:Q", title="% de Error cometido", scale=alt.Scale(domain=[0, 100])),
                        color=alt.Color("categoria:N", title="Categoría"),
                        tooltip=[alt.Tooltip("categoria:N", title="Regla"), alt.Tooltip("porcentaje_error:Q", title="% de Error", format=".1f"), alt.Tooltip("fecha:T", title="Fecha")]
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
        user_badges = r_badges.json().get("badges", []) if r_badges.ok else []

        st.markdown("""
        <style>
        .vitrina { display: flex; flex-wrap: wrap; justify-content: center; gap: 2rem; margin-top: 3rem; margin-bottom: 3rem; }
        .insignia-box { display: flex; flex-direction: column; align-items: center; width: 140px; text-align: center; }
        .insignia-circle { width: 110px; height: 110px; border-radius: 50%; background-color: #f3f4f6; display: flex; align-items: center; justify-content: center; font-size: 3rem; margin-bottom: 1rem; transition: transform 0.3s ease, box-shadow 0.3s ease; box-shadow: inset 0 4px 6px rgba(0,0,0,0.1); filter: grayscale(100%) opacity(0.4); }
        .insignia-earned { background: linear-gradient(135deg, #fbbf24, #f59e0b); box-shadow: 0 10px 25px rgba(245, 158, 11, 0.4); filter: grayscale(0%) opacity(1); transform: scale(1.05); }
        .insignia-earned:hover { transform: scale(1.1) translateY(-5px); }
        .insignia-master { background: linear-gradient(135deg, #a855f7, #7e22ce); box-shadow: 0 10px 30px rgba(168, 85, 247, 0.5); width: 140px; height: 140px; font-size: 4rem; }
        .insignia-title { font-size: 0.95rem; font-weight: 700; color: #374151; line-height: 1.3; }
        .insignia-subtitle { font-size: 0.75rem; color: #6b7280; margin-top: 0.2rem; }
        </style>
        """, unsafe_allow_html=True)
        
        img_bv = get_base64_image("frontend/assets/BV.png")
        img_gj = get_base64_image("frontend/assets/GJ.png")
        img_cz = get_base64_image("frontend/assets/CZ.png")
        img_yll = get_base64_image("frontend/assets/YLL.png")
        img_tildes = get_base64_image("frontend/assets/tilde.png")
        img_master = get_base64_image("frontend/assets/master.png")
        img_be = get_base64_image("frontend/assets/buenaescritura.png")
        img_h = get_base64_image("frontend/assets/H.png")

        todas_insignias = [
            {"id": "dominio_b_v", "titulo": "Dominio B/V", "sub": "15 textos impecables", "emoji": f"<img src='{img_bv}' style='width:100%; height:100%; object-fit:cover; border-radius:50%;'>"},
            {"id": "dominio_g_j", "titulo": "Dominio G/J", "sub": "15 textos impecables", "emoji": f"<img src='{img_gj}' style='width:100%; height:100%; object-fit:cover; border-radius:50%;'>"},
            {"id": "dominio_y_ll", "titulo": "Dominio Y/LL", "sub": "15 textos impecables", "emoji": f"<img src='{img_yll}' style='width:100%; height:100%; object-fit:cover; border-radius:50%;'>"},
            {"id": "dominio_c_z", "titulo": "Dominio C/Z/S", "sub": "15 textos impecables", "emoji": f"<img src='{img_cz}' style='width:100%; height:100%; object-fit:cover; border-radius:50%;'>"},
            {"id": "dominio_tildes", "titulo": "Francotirador", "sub": "Rey de las tildes", "emoji": f"<img src='{img_tildes}' style='width:100%; height:100%; object-fit:cover; border-radius:50%;'>"},
            {"id": "dominio_h", "titulo": "Cazafantasmas", "sub": "Dominio de la H", "emoji": f"<img src='{img_h}' style='width:100%; height:100%; object-fit:cover; border-radius:50%;'>"},
            {"id": "dominio_otros", "titulo": "Pluma de Oro", "sub": "Buena Escritura general", "emoji": f"<img src='{img_be}' style='width:100%; height:100%; object-fit:cover; border-radius:50%;'>"}
        ]

        html_insignias = "<div class='vitrina'>"
        for ins in todas_insignias:
            clase_extra = "insignia-earned" if ins["id"] in user_badges else ""
            html_insignias += f"<div class='insignia-box'><div class='insignia-circle {clase_extra}'>{ins['emoji']}</div><div class='insignia-title'>{ins['titulo']}</div><div class='insignia-subtitle'>{ins['sub']}</div></div>"
            
        html_insignias += "</div>"
        html_insignias = html_insignias.replace('\n', '').replace('\r', '')
        st.markdown(html_insignias, unsafe_allow_html=True)
        
        clase_master = "insignia-earned insignia-master" if "master_ortografia" in user_badges else "insignia-master"
        html_master = f"""<div class='vitrina' style='margin-top: 0;'><div class="insignia-box" style="width: 200px;"><div class="insignia-circle {clase_master}"><img src='{img_master}' style='width:100%; height:100%; object-fit:cover; border-radius:50%;'></div><div class="insignia-title" style="font-size: 1.2rem; margin-top: 0.5rem;">Máster de la Ortografía</div><div class="insignia-subtitle" style="font-size: 0.85rem;">Consigue todas las demás</div></div></div>"""
        st.markdown(html_master.replace('\n', '').replace('\r', ''), unsafe_allow_html=True)

    except Exception as e:
        st.warning(f"Error cargando vitrina: {e}")
        
    st.markdown("<h2 class='h-section'>Documentos del alumno</h2>", unsafe_allow_html=True)
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

                if es_propietario:
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
                                    if st.session_state.get("last_doc_id") == d['id']:
                                        clear_current_analysis()
                                    st.session_state.pop(f"__cache_doc_{d['id']}", None)
                                    cargar_metricas(username, backend_url)
                                    st.session_state[del_flag_key] = False
                                    st.rerun()
                            except:
                                pass
                        if col_cancel.button("Cancelar", key=f"cancel_{d['id']}", use_container_width=True):
                            st.session_state[del_flag_key] = False
                else:
                    st.info("Solo el alumno puede eliminar sus documentos.")
    else:
        st.info("No hay documentos aún.")

# =========================
# Status
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
    .flashcard-container { perspective: 1000px; margin: 2rem auto; }
    .flashcard { background: #ffffff; border-radius: 20px; padding: 2.5rem; box-shadow: 0 10px 25px rgba(0, 0, 0, 0.08); border-top: 8px solid #3b82f6; transition: transform 0.3s ease, box-shadow 0.3s ease; position: relative; overflow: hidden; }
    .flashcard:hover { transform: translateY(-5px); box-shadow: 0 15px 35px rgba(0, 0, 0, 0.12); }
    .flashcard-title { color: #1e3a8a; font-size: 2.2rem !important; font-weight: 800 !important; margin-bottom: 1.5rem !important; text-align: center; letter-spacing: -0.5px; }
    .flashcard-content { font-size: 1.15rem; color: #374151; line-height: 1.7; }
    .flashcard-content ul { margin-top: 0.5rem; margin-bottom: 1.5rem; }
    .flashcard-content li { margin-bottom: 0.8rem; }
    .flashcard-examples { background: linear-gradient(135deg, #eff6ff, #dbeafe); padding: 1.2rem; border-radius: 12px; color: #1e40af; font-weight: 500; margin-top: 1.5rem; border-left: 4px solid #60a5fa; }
    .example-word { font-weight: 800; color: #2563eb; }
    </style>
    """, unsafe_allow_html=True)

    tarjetas = [
        {"titulo": "Uso de la B y la V", "emoji": "🅱️ / ✌️", "reglas": ["Se escriben con <b>B</b> los verbos terminados en <i>-bir</i> y <i>-buir</i>.", "Se escriben con <b>V</b> los adjetivos terminados en <i>-avo, -ave, -evo, -eve, -ivo, -iva</i>."], "ejemplos": "Escribir, contribuir, <span class='example-word'>suave</span>, <span class='example-word'>obvio</span>."},
        {"titulo": "Uso de la G y la J", "emoji": "🦒 / 🐆", "reglas": ["Se escriben con <b>G</b> los verbos terminados en <i>-ger, -gir</i>.", "Se escriben con <b>J</b> las palabras que terminan en <i>-aje, -eje</i>."], "ejemplos": "Recoger, <span class='example-word'>geografía</span>, <span class='example-word'>garaje</span>, <span class='example-word'>conduje</span>."},
        {"titulo": "Uso de Y y LL", "emoji": "🪀 / 🗝️", "reglas": ["Se escriben con <b>LL</b> las palabras terminadas en <i>-illo, -illa</i>.", "Se escribe <b>Y</b> en plurales terminados en <i>-y</i>."], "ejemplos": "Pasillo, <span class='example-word'>zambullir</span>, reyes."},
        {"titulo": "Uso de C, Z y S", "emoji": "🦊 / 🐍", "reglas": ["Se usa <b>Z</b> delante de a, o, u y <b>C</b> delante de e, i.", "Los plurales de palabras que terminan en Z, se escriben con <b>C</b>."], "ejemplos": "<span class='example-word'>Zorro</span>, <span class='example-word'>canción</span>, <span class='example-word'>peces</span>."},
        {"titulo": "Uso de la H", "emoji": "👻", "reglas": ["Se escriben con <b>H</b> las palabras que empiezan por los diptongos <i>hie-, hue-</i>.", "Todas las formas de haber, hacer, hallar, hablar y habitar llevan <b>H</b>."], "ejemplos": "<span class='example-word'>Hielo</span>, <span class='example-word'>hueso</span>, <span class='example-word'>hicimos</span>."},
        {"titulo": "Acentuación (Tildes)", "emoji": "🎯", "reglas": ["<b>Agudas:</b> Llevan tilde si terminan en vocal, <i>-n</i> o <i>-s</i>.", "<b>Llanas:</b> Llevan tilde si NO terminan en vocal, <i>-n</i> ni <i>-s</i>.", "<b>Esdrújulas:</b> ¡Llevan tilde siempre!"], "ejemplos": "<span class='example-word'>Camión</span>, <span class='example-word'>árbol</span>, <span class='example-word'>rápido</span>."}
    ]

    if "repaso_index" not in st.session_state:
        st.session_state.repaso_index = 0

    st.markdown("<h1 style='text-align: center; margin-bottom: 0.5rem;'>📖 Tarjetas de Repaso</h1>", unsafe_allow_html=True)
    
    total_tarjetas = len(tarjetas)
    idx = st.session_state.repaso_index
    tarjeta = tarjetas[idx]

    st.progress((idx + 1) / total_tarjetas)
    html_reglas = "".join([f"<li>{r}</li>" for r in tarjeta["reglas"]])
    
    st.markdown(f"""
    <div class="flashcard-container">
        <div class="flashcard">
            <h2 class="flashcard-title">{tarjeta['emoji']} {tarjeta['titulo']}</h2>
            <div class="flashcard-content"><ul>{html_reglas}</ul></div>
            <div class="flashcard-examples">💡 <b>Ejemplos:</b><br>{tarjeta['ejemplos']}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("⬅️ Anterior", use_container_width=True, disabled=(idx == 0)):
            st.session_state.repaso_index -= 1
            st.rerun()
    with col3:
        if st.button("Siguiente ➡️", use_container_width=True, disabled=(idx == total_tarjetas - 1)):
            st.session_state.repaso_index += 1
            st.rerun()

def obtener_ejercicios_backend(backend_url, username, categoria):
    try:
        r = requests.get(f"{backend_url}/users/{username}/ejercicios", timeout=10)
        if r.ok:
            palabras_bolsa = r.json().get("ejercicios", [])
            ejercicios_formateados = []
            for p in palabras_bolsa:
                cat_db = p["categoria"].upper()
                if categoria != "REMIX" and cat_db not in categoria: continue
                opciones = [p["palabra_correcta"], p["palabra_fallada"]]
                import random
                random.shuffle(opciones)
                ejercicios_formateados.append({"masked": "¿Cómo se escribe?", "opciones": opciones, "correcta": p["palabra_correcta"], "palabra": p["palabra_correcta"], "backend_id": p["id"]})
            return ejercicios_formateados
    except Exception as e:
        st.error(f"Error cargando tu bolsa de palabras: {e}")
    return []

def mostrar_gimnasio(backend_url, username):
    st.markdown("""
    <style>
    .gym-card { background: linear-gradient(135deg, #e0eafc, #cfdef3); border-radius: 15px; padding: 2rem; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 2rem; }
    .gym-word { font-size: 3rem !important; font-weight: 800; color: #1e3a8a; letter-spacing: 2px; margin-bottom: 1rem; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("<h1 style='text-align: center;'>🏋️ Gimnasio Ortográfico</h1>", unsafe_allow_html=True)
    
    if "gym_estado" not in st.session_state:
        st.session_state.gym_estado = "configuracion" 
        st.session_state.gym_preguntas = []
        st.session_state.gym_index = 0
        st.session_state.gym_score = 0
        st.session_state.gym_categoria = "REMIX"
        st.session_state.gym_dificultad = "facil"

    if st.session_state.gym_estado == "configuracion":
        st.markdown("<h3 class='h-section'>1. Elige tu entrenamiento</h3>", unsafe_allow_html=True)
        categoria = st.selectbox("Categoría a repasar:", ["REMIX", "B_V", "G_J", "Y_LL", "C_Z", "H", "TILDES"], key="gym_cat_select")
        
        if st.button("🚀 ¡Empezar Entrenamiento!", use_container_width=True):
            nivel_dificultad = "facil" 
            try:
                r_niveles = requests.get(f"{backend_url}/users/{username}/levels", timeout=5)
                if r_niveles.ok:
                    niveles_data = r_niveles.json().get("niveles", {})
                    llave_nivel = "nivel_general" if categoria == "REMIX" else f"nivel_{categoria.lower()}"
                    nivel_usuario = niveles_data.get(llave_nivel, "")
                    if "Avanzado" in nivel_usuario: nivel_dificultad = "dificil"
                    elif "Medio" in nivel_usuario: nivel_dificultad = "intermedio"
            except Exception: pass 
            
            st.toast(f"Adaptando gimnasio a tu nivel: {nivel_dificultad.upper()}", icon="🧠")

            preguntas = []
            if categoria == "REMIX":
                for cat, niveles_dict in EJERCICIOS_BASE.items():
                    preguntas.extend(niveles_dict.get(nivel_dificultad, []))
            else:
                preguntas.extend(EJERCICIOS_BASE.get(categoria, {}).get(nivel_dificultad, []))
            
            preguntas_backend = obtener_ejercicios_backend(backend_url, username, categoria)
            preguntas.extend(preguntas_backend)

            import random
            random.shuffle(preguntas)
            st.session_state.gym_preguntas = preguntas[:10]
            st.session_state.gym_index = 0
            st.session_state.gym_score = 0
            st.session_state.gym_categoria = categoria
            st.session_state.gym_dificultad = nivel_dificultad
            
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

        st.markdown(f"""<div class="gym-card"><div class="gym-word">{pregunta_actual['masked']}</div></div>""", unsafe_allow_html=True)
        st.markdown("<h3 style='text-align:center;'>Selecciona la respuesta correcta:</h3>", unsafe_allow_html=True)
        
        cols = st.columns(len(pregunta_actual['opciones']))
        for i, opcion in enumerate(pregunta_actual['opciones']):
            if cols[i].button(opcion, key=f"btn_{st.session_state.gym_index}_{i}", use_container_width=True):
                if opcion == pregunta_actual['correcta']:
                    st.toast("¡Correcto! 🎉", icon="✅")
                    st.session_state.gym_score += 1
                    if "backend_id" in pregunta_actual:
                        try: requests.post(f"{backend_url}/ejercicios/{pregunta_actual['backend_id']}/acierto", timeout=5)
                        except: pass
                else:
                    st.toast(f"¡Oops! La correcta era '{pregunta_actual['palabra']}'", icon="❌")
                
                st.session_state.gym_index += 1
                if st.session_state.gym_index >= total_preguntas:
                    st.session_state.gym_estado = "resultados"
                    
                    try:
                        requests.post(f"{backend_url}/users/{username}/gym_result", data={
                            "categoria": st.session_state.gym_categoria,
                            "nivel": st.session_state.gym_dificultad,
                            "score": st.session_state.gym_score,
                            "total": total_preguntas
                        }, timeout=5)
                    except: pass
                    
                st.rerun()

        if st.button("Abandonar entrenamiento", type="secondary"):
            st.session_state.gym_estado = "configuracion"
            st.rerun()

    elif st.session_state.gym_estado == "resultados":
        score = st.session_state.gym_score
        total = len(st.session_state.gym_preguntas)
        porcentaje_acierto = (score / total) * 100 if total > 0 else 100
        
        if porcentaje_acierto >= 60:
            st.balloons()
            st.markdown("<div class='gym-card'>", unsafe_allow_html=True)
            st.markdown("<h2 style='color: #1e3a8a;'>¡Entrenamiento Completado! 🏆</h2>", unsafe_allow_html=True)
            st.markdown(f"<h1>{score} / {total}</h1>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
            
            if st.button("Volver al Gimnasio", use_container_width=True):
                st.session_state.gym_estado = "configuracion"
                st.rerun()
        else:
            st.markdown("<div class='gym-card' style='background: linear-gradient(135deg, #fee2e2, #fecaca);'>", unsafe_allow_html=True)
            st.markdown("<h2 style='color: #b91c1c;'>¡Sigue practicando! 💪</h2>", unsafe_allow_html=True)
            st.markdown(f"<h1 style='color: #991b1b;'>{score} / {total}</h1>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
            
            st.info("💡 Hemos detectado varios fallos. ¡Un pequeño repaso a la teoría te vendrá genial!")
            
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Volver al Gimnasio", use_container_width=True):
                    st.session_state.gym_estado = "configuracion"
                    st.rerun()
            with c2:
                if st.button("📖 Repasar Teoría", use_container_width=True, type="primary"):
                    mapa_teoria = {"B_V": 0, "G_J": 1, "Y_LL": 2, "C_Z": 3, "H": 4, "TILDES": 5}
                    cat_actual = st.session_state.get("gym_categoria", "B_V")
                    st.session_state.repaso_index = mapa_teoria.get(cat_actual, 0)
                    st.session_state.nav_actual = "Repaso"
                    st.session_state.gym_estado = "configuracion"
                    st.rerun()

# =========================
# Main app
# =========================
def main_app():
    st.sidebar.title("Opciones")
    backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")

    if st.session_state.get("logged_in", False):
        usuario = st.session_state['usuario']
        es_admin = (usuario == 'admin')
        
        if not es_admin:
            if "mi_avatar" not in st.session_state:
                try:
                    r_prof = requests.get(f"{backend_url}/users/{usuario}/profile", timeout=2)
                    st.session_state["mi_avatar"] = r_prof.json().get("profile", {}).get("avatar", "🐼") if r_prof.ok else "🐼"
                except:
                    st.session_state["mi_avatar"] = "🐼"

        inject_session_js(backend_url, usuario)
        
        st.markdown("""
        <style>
        [data-testid="stSidebar"] div.stButton button { justify-content: flex-start !important; padding-left: 1rem !important; font-size: 1.05rem !important; font-weight: 500 !important; border-radius: 8px !important; border: none !important; box-shadow: none !important; margin-bottom: 0.1rem !important; transition: all 0.2s ease; }
        [data-testid="stSidebar"] div.stButton button[kind="secondary"] { background-color: transparent !important; color: #475569 !important; }
        [data-testid="stSidebar"] div.stButton button[kind="secondary"]:hover { background-color: #f1f5f9 !important; color: #0f172a !important; }
        [data-testid="stSidebar"] div.stButton button[kind="primary"] { background-color: #1e3a8a !important; color: white !important; }
        .sidebar-divider { margin: 1.5rem 0 1rem 0; border-top: 1px solid #e2e8f0; }
        </style>
        """, unsafe_allow_html=True)

        if es_admin:
            # SIDEBAR PROFESOR (ADMIN)
            c_ava, c_name = st.sidebar.columns([1.2, 2.5], gap="small")
            with c_ava:
                st.markdown("<div style='font-size: 3.5rem; text-align: center; height: 85px; display: flex; align-items: center; justify-content: center;'>👨‍🏫</div>", unsafe_allow_html=True)
            with c_name:
                st.markdown(f"<div style='display: flex; align-items: center; height: 85px;'><div style='font-weight: 800; font-size: 1.5rem; color: #1e3a8a;'>Profesor</div></div>", unsafe_allow_html=True)

            st.sidebar.markdown("<div style='color: #64748b; font-weight: 700; font-size: 0.85rem; margin-top: 1.5rem; margin-bottom: 0.5rem;'>ADMINISTRACIÓN</div>", unsafe_allow_html=True)

            if "nav_actual" not in st.session_state or st.session_state.nav_actual not in ["Alumnos", "Metricas"]:
                st.session_state.nav_actual = "Alumnos"

            opciones_admin = [("👥 Mis Alumnos", "Alumnos"), ("📊 Métricas de Clase", "Metricas")]
            for etiqueta, valor in opciones_admin:
                tipo_boton = "primary" if st.session_state.nav_actual == valor else "secondary"
                if st.sidebar.button(etiqueta, type=tipo_boton, key=f"nav_{valor}", use_container_width=True):
                    st.session_state.nav_actual = valor
                    st.session_state.admin_view_student = None 
                    st.rerun()

        else:
            # SIDEBAR ALUMNO (NORMAL)
            st.markdown("""
            <style>
            [data-testid="stSidebar"] [data-testid="column"]:nth-child(1) div.stButton button {
                width: 85px !important; height: 85px !important; min-width: 85px !important;
                border-radius: 50% !important; font-size: 4rem !important; padding: 0 !important;
                background: #ffffff !important; border: 3px solid #e2e8f0 !important;
                box-shadow: 0 4px 6px rgba(0,0,0,0.05) !important; display: flex !important;
                align-items: center !important; justify-content: center !important;
                margin-top: 0.5rem !important; cursor: pointer !important; z-index: 99 !important;
            }
            [data-testid="stSidebar"] [data-testid="column"]:nth-child(1) div.stButton button p { line-height: 1 !important; margin: 0 !important; }
            [data-testid="stSidebar"] [data-testid="column"]:nth-child(1) div.stButton button:hover { border-color: #3b82f6 !important; transform: scale(1.05) !important; background: #f8fafc !important; }
            </style>
            """, unsafe_allow_html=True)

            if "nav_actual" not in st.session_state or st.session_state.nav_actual in ["Alumnos", "Metricas"]:
                st.session_state.nav_actual = "Corrector"

            c_ava, c_name = st.sidebar.columns([1.2, 2.5], gap="small")
            with c_ava:
                if st.button(st.session_state['mi_avatar'], key="btn_top_avatar"):
                    st.session_state.nav_actual = "Mi Perfil"
                    st.rerun()
            with c_name:
                st.markdown(f"""
                <div style="display: flex; align-items: center; height: 85px; margin-top: 0.5rem; padding-left: 5px;">
                    <div style="font-weight: 800; font-size: 1.4rem; color: #1e3a8a; line-height: 1.1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                        {usuario}
                    </div>
                </div>
                """, unsafe_allow_html=True)

            st.sidebar.markdown("<div style='color: #64748b; font-weight: 700; font-size: 0.85rem; margin-top: 1.5rem; margin-bottom: 0.5rem; letter-spacing: 1px;'>NAVEGACIÓN</div>", unsafe_allow_html=True)

            opciones_menu = [
                ("📝 Corrector de Textos", "Corrector"),
                ("🏋️ Gimnasio Ortográfico", "Gimnasio"),
                ("📖 Repaso Teórico", "Repaso")
            ]

            for etiqueta, valor in opciones_menu:
                tipo_boton = "primary" if st.session_state.nav_actual == valor else "secondary"
                if st.sidebar.button(etiqueta, type=tipo_boton, key=f"nav_{valor}", use_container_width=True):
                    st.session_state.nav_actual = valor
                    st.rerun()

            st.sidebar.markdown("<div class='sidebar-divider'></div>", unsafe_allow_html=True)
            if st.sidebar.button("🧹 Limpiar análisis", use_container_width=True, key="btn_limpiar"):
                clear_current_analysis()
                st.rerun()

        # Botón de Cerrar Sesión
        if st.sidebar.button("🔚 Cerrar sesión", use_container_width=True, key="btn_cerrar"):
            try: requests.post(f"{backend_url}/users/logout", data={"username": usuario}, timeout=5)
            except: pass
            st.session_state["logged_in"] = False
            st.session_state.pop("usuario", None)
            st.session_state.pop("mi_avatar", None)
            _clear_status_cache()
            _clear_metrics_cache()
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

    # ==========================================
    # LÓGICA DE RUTAS
    # ==========================================
    if not st.session_state.get("logged_in", False):
        st.title("📝 PALABRIA")
        if st.session_state.get("show_login", False):
            login()
            return
        elif st.session_state.get("show_create_account", False):
            create_account()
            return
        else:
            st.warning("Por favor, selecciona una opción en la barra lateral para iniciar sesión o registrarte.")
            return

    modo_app = st.session_state.get("nav_actual")
    es_admin = (st.session_state['usuario'] == 'admin')
    
    if es_admin:
        if modo_app == "Alumnos":
            mostrar_admin_alumnos(backend_url)
        elif modo_app == "Metricas":
            mostrar_admin_metricas(backend_url)
        return
        
    if modo_app == "Gimnasio":
        mostrar_gimnasio(backend_url, st.session_state["usuario"])
        return 
    elif modo_app == "Repaso":
        mostrar_repaso()
        return
    elif modo_app == "Mi Perfil":
        mostrar_perfil(st.session_state["usuario"], backend_url)
        return

    st.title("📝 PALABRIA - Corrector de Textos")

    if "load_disparado" not in st.session_state:
        st.session_state["load_disparado"] = False
    if not st.session_state["load_disparado"]:
        try: requests.post(f"{backend_url}/load/", timeout=5)
        except: pass
        st.session_state["load_disparado"] = True

    st.markdown("<h2 class='h-section'>Estado del modelo</h2>", unsafe_allow_html=True)
    render_status(backend_url)

    if not st.session_state.get("modelo_listo", False): return

    st.markdown("<div class='spacer-1cm'></div>", unsafe_allow_html=True)
    st.markdown("<h2 class='h-section'>📤 ANALIZA TU PDF O PEGA TU TEXTO</h2>", unsafe_allow_html=True)

    st.markdown("<h2 class='h-section'>Modo de corrección</h2>", unsafe_allow_html=True)
    def on_mode_change(): st.session_state["last_input_digest"] = None
    mode_label = st.radio(" ", list(MODE_OPTIONS.keys()), on_change=on_mode_change, horizontal=False, label_visibility="collapsed")
    selected_mode = MODE_OPTIONS[mode_label]
    st.caption(f"Modo seleccionado: **{selected_mode}**")

    st.markdown("<h2 class='h-section'>Fuente de entrada</h2>", unsafe_allow_html=True)
    modo_entrada = st.radio(" ", ["Subir PDF", "Escribir texto"], horizontal=True, label_visibility="collapsed")

    texto_plano = uploaded_file = file_bytes = digest = None

    if "last_input_digest" not in st.session_state:
        st.session_state["last_input_digest"] = None
    if "last_doc_id" not in st.session_state:
        st.session_state["last_doc_id"] = None
    if "last_analysis" not in st.session_state:
        st.session_state["last_analysis"] = None

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
                corrected = str(data.get("corrected", ""))
                st.session_state["last_analysis"] = {"original_text": data.get("original_text", ""), "metricas": data.get("metricas", {}), "corrected_text": corrected, "feedback": data.get("feedback", ""), "mode_used": data.get("mode_used", selected_mode)}
                st.session_state["edited_text_area"] = corrected
                st.session_state["__edited_for_doc"] = st.session_state["last_doc_id"]
            else:
                st.error(f"❌ Error al procesar el PDF (código {response.status_code})")
                st.stop()
    else:
        st.markdown("<h2 class='h-section'>Escribir texto</h2>", unsafe_allow_html=True)
        texto_plano = st.text_area("Pega aquí tu texto", height=200, key="__input_texto_plano")
        default_name = st.session_state.get("__input_filename", "mi_texto.txt")
        nombre_doc = st.text_input("Nombre del documento", value=default_name, key="__input_filename")
        nombre_doc_norm = (nombre_doc or "mi_texto.txt").strip()
        if "." not in nombre_doc_norm: nombre_doc_norm += ".txt"

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
                        data = {'username': st.session_state["usuario"], 'text': texto_plano, 'filename': nombre_doc_norm, 'mode': selected_mode}
                        response = requests.post(f"{backend_url}/process_text/", data=data, timeout=180)

                    if response.status_code == 200:
                        resp = response.json()
                        st.session_state["last_input_digest"] = digest
                        st.session_state["last_pdf_name"] = nombre_doc_norm
                        st.session_state["last_doc_id"] = resp.get("doc_id")
                        corrected = str(resp.get("corrected", ""))
                        st.session_state["last_analysis"] = {"original_text": resp.get("original_text", ""), "metricas": resp.get("metricas", {}), "corrected_text": corrected, "feedback": resp.get("feedback", ""), "mode_used": resp.get("mode_used", selected_mode)}
                        st.session_state["edited_text_area"] = corrected
                        st.session_state["__edited_for_doc"] = st.session_state["last_doc_id"]
                    else:
                        st.error(f"❌ Error al procesar el texto")
                        st.stop()

    st.markdown("<div class='spacer-tabs'></div><hr>", unsafe_allow_html=True)

    if has_current_analysis():
        anal = st.session_state["last_analysis"]
        metricas = anal.get("metricas", {})
        original_joined = anal.get("original_text", "")
        corrected_text = anal.get("corrected_text", "") or ""
        
        st.markdown("<h2 class='h-section'>⚙️ Modo usado</h2>", unsafe_allow_html=True)
        st.info(anal.get("mode_used", "(sin modo)"))

        if st.session_state.get("__edited_for_doc") != st.session_state.get("last_doc_id"):
            st.session_state["edited_text_area"] = corrected_text
            st.session_state["__edited_for_doc"] = st.session_state.get("last_doc_id")

        if "edited_text_area" not in st.session_state:
            st.session_state["edited_text_area"] = corrected_text

        edited_text_current = st.session_state.get("edited_text_area", corrected_text)
        cambios_usuario_total = word_levenshtein_count(original_joined or "", edited_text_current or "")

        if metricas:
            st.markdown("<h2 class='h-section'>📊 Métricas del texto actual</h2>", unsafe_allow_html=True)
            col1, col2 = st.columns(2, gap="medium")
            col1.metric("Total de frases", metricas.get("total_frases", 0))
            col2.metric("Posibles frases con 'tú' impersonal", metricas.get("frases_con_tu_impersonal", 0))

            c_o1, c_o2, c_o3 = st.columns(3, gap="medium")
            c_o1.metric("Errores B/V", metricas.get("errores_b_v", 0))
            c_o2.metric("Errores G/J", metricas.get("errores_g_j", 0))
            c_o3.metric("Errores Y/LL", metricas.get("errores_y_ll", 0))

            c_o4, c_o5, c_o6 = st.columns(3, gap="medium")
            c_o4.metric("Errores de H", metricas.get("errores_h", 0))
            c_o5.metric("Errores de Tildes", metricas.get("errores_tildes", 0))
            c_o6.metric("Errores de C/Z/S", metricas.get("errores_c_z", 0))

            col3, col4 = st.columns(2, gap="medium")
            col3.metric("Cambios propuestos", metricas.get("cambios_propuestos_modelo", 0))
            col4.metric("Cambios realizados", cambios_usuario_total)

        st.markdown("<h2 class='h-section'>📥 Texto original</h2>", unsafe_allow_html=True)
        st.markdown(f"""<textarea class="readonly-box" readonly style="white-space: pre-wrap; line-height: 1.5;">{(anal.get("original_text", "") or "").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")}</textarea>""", unsafe_allow_html=True)

        st.markdown("<h2 class='h-section'>💻 Salida del modelo</h2>", unsafe_allow_html=True)
        st.markdown(f"""<textarea class="readonly-box" readonly>{(corrected_text or "").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")}</textarea>""", unsafe_allow_html=True)

        st.markdown("<h2 class='h-section'>📚 Feedback</h2>", unsafe_allow_html=True)
        st.markdown(f"""<textarea class="readonly-box" readonly style="white-space: pre-wrap; line-height: 1.5;">{(anal.get("feedback", "") or "").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")}</textarea>""", unsafe_allow_html=True)

        st.markdown("<h2 class='h-section'>📝 Revisa y edita el texto corregido</h2>", unsafe_allow_html=True)

        def _save_user_changes_callback():
            edited_now = st.session_state.get("edited_text_area", "")
            changes_now = word_levenshtein_count(original_joined or "", edited_now or "")
            last_saved = st.session_state.get(f"__last_saved_changes_{st.session_state.get('last_doc_id')}")
            if last_saved is None or int(last_saved) != int(changes_now):
                _post_user_changes(backend_url, st.session_state["last_doc_id"], int(changes_now))

        edited_text = st.text_area("Tu versión final", key="edited_text_area", height=300, on_change=_save_user_changes_callback)

        if st.button("📅 Descargar PDF corregido"):
            base = (st.session_state.get("last_pdf_name") or "Texto_Corregido").rsplit(".", 1)[0]
            pdf_filename = save_text_as_pdf(edited_text, filename=f"{base}.pdf")
            with open(pdf_filename, "rb") as file:
                st.download_button("Descargar el PDF", file, file_name=pdf_filename, mime="application/pdf")
    else:
        st.info("No hay análisis activo. Sube un PDF o escribe texto y pulsa “Analizar texto”.")

if __name__ == "__main__":
    main_app()