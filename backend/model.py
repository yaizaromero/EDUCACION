import time
import threading
from typing import List, Optional
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

MODEL_LOADED: bool = False
LOAD_PROGRESS: int = 0
LOAD_MESSAGE: str = "Modelo no cargado."

_lock = threading.Lock()
_thread = None
_tokenizer: Optional[AutoTokenizer] = None
_model: Optional[AutoModelForCausalLM] = None

MODEL_ID = "mistralai/Mistral-7B-Instruct-v0.3"

# --- PROMPTS SEPARADOS ---

PROMPT_ORTOGRAFIA = """<s>[INST] <<SYS>>
Eres un experto en ortografía española. Tu única tarea es corregir:
- Confusión entre B/V, G/J, Y/LL.
- Uso de la H.
- Tildes y acentuación.
REGLA: No cambies el "tú" impersonal ni el estilo. No añadas comentarios.
<</SYS>>
Texto a corregir:
[TEXTO] [/INST]"""

PROMPT_TU_IMPERSONAL = """<s>[INST] <<SYS>>
Eres un experto en redacción académica. Tu única tarea es:
- Transformar verbos en 2ª persona singular (tú impersonal) a la forma impersonal con "se".
REGLA: No corrijas ortografía ni tildes. No cambies el tiempo verbal. No añadas comentarios.
<</SYS>>
Texto a corregir:
[TEXTO] [/INST]"""

# --- GENERACIÓN ---

@torch.inference_mode()
def _generate_once(text: str, mode: str = "ortografia", max_new_tokens: int = 512) -> str:
    global _tokenizer, _model
    if not MODEL_LOADED or _tokenizer is None or _model is None:
        raise RuntimeError("El modelo no está cargado.")
    
    # Selección dinámica del prompt
    template = PROMPT_ORTOGRAFIA if mode == "ortografia" else PROMPT_TU_IMPERSONAL
    prompt = template.replace("[TEXTO]", text.strip())
    
    inputs = _tokenizer(prompt, return_tensors="pt", padding=True, truncation=True)
    if hasattr(_model, "device"):
        inputs = {k: v.to(_model.device) for k, v in inputs.items()}
    
    output_ids = _model.generate(
        **inputs, 
        max_new_tokens=max_new_tokens, 
        do_sample=False, 
        temperature=0.0,
        eos_token_id=_tokenizer.eos_token_id,
        pad_token_id=_tokenizer.pad_token_id
    )
    
    generated = output_ids[0][inputs["input_ids"].shape[-1]:]
    return _tokenizer.decode(generated, skip_special_tokens=True).strip()

def correct_full_text(text: str, mode: str = "ortografia") -> str:
    if not text: return ""
    return _generate_once(text, mode=mode)

# --- FEEDBACK ---

def generate_feedback(original: str, corrected: str) -> str:
    if not original or not corrected:
        return ""

    from backend.metrics import extract_word_changes

    if original.strip() == corrected.strip():
        return "No se han detectado errores para corregir en este modo."

    RULES = {
        "bv": "B/V: se escriben según la raíz de la palabra.",
        "gj": "G/J: corrección de sonido fuerte/suave ante e/i.",
        "yll": "Y/LL: corrección ortográfica de grafías similares.",
        "h": "H: corrección de h muda u omitida.",
        "tildes": "Tildes: ajuste de acentuación según reglas generales.",
        "tu_impersonal": "Transformación del 'tú' impersonal a forma con 'se'.",
        "ortografia": "Corrección ortográfica general.",
    }

    # 🔥 SIN LÍMITE DE CAMBIOS
    changes = extract_word_changes(original, corrected, max_items=1000)

    # Si no detecta cambios pero el texto cambió → tú impersonal
    if not changes:
        return "Se ha transformado el estilo directo (tú) a una forma impersonal con 'se'."

    lines = ["Cambios realizados:\n"]

    for idx, ch in enumerate(changes, 1):
        orig_w = ch.get("original", "")
        corr_w = ch.get("corrected", "")
        cat = ch.get("categories", ["ortografia"])[0]
        rule = RULES.get(cat, "Mejora de la precisión léxica.")
        lines.append(f"{idx}. {orig_w} → {corr_w} ({rule})")

    return "\n".join(lines)


# --- CARGA DEL MODELO (Igual que el tuyo) ---

def _set(progress: int, message: str):
    global LOAD_PROGRESS, LOAD_MESSAGE
    with _lock:
        LOAD_PROGRESS = max(0, min(100, int(progress)))
        LOAD_MESSAGE = message

def _load_impl():
    global MODEL_LOADED, _tokenizer, _model
    try:
        _set(5, "Iniciando Mistral...")
        compute_dtype = torch.bfloat16 if torch.cuda.is_available() else torch.float16
        nf4_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=compute_dtype,
        )
        _tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, use_fast=True)
        if _tokenizer.pad_token is None: _tokenizer.pad_token = _tokenizer.eos_token
        
        _model = AutoModelForCausalLM.from_pretrained(
            MODEL_ID, quantization_config=nf4_config, device_map="auto"
        )
        _model.eval()
        MODEL_LOADED = True
        _set(100, "✅ Modelo listo")
    except Exception as e:
        _set(0, f"❌ Error: {e}")

def ensure_model_loaded(async_load: bool = True):
    global _thread
    if MODEL_LOADED: return
    if _thread and _thread.is_alive(): return
    if async_load:
        _thread = threading.Thread(target=_load_impl, daemon=True)
        _thread.start()
    else:
        _load_impl()