# backend/model.py
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

# --- PROMPTS UNIFICADOS Y MEJORADOS ---

PROMPT_ORTOGRAFIA = """<s>[INST] <<SYS>>
Eres un experto lingüista de la RAE. Tu tarea es corregir TODAS las faltas de ortografía:
- Confusión entre B/V, G/J, Y/LL.
- Confusión entre C, Z y S (ej: 'asé' -> 'haz').
- Uso de la H (omitida o mal puesta).
- Tildes y acentuación académica.
- Errores generales (M antes de P, S por X, etc.).

REGLAS: 
1. NO cambies el "tú" impersonal ni el estilo. 
2. NO sustituyas palabras por sinónimos. 
3. No añadas comentarios. Solo devuelve el texto corregido.
<</SYS>>
Texto a corregir:
[TEXTO] [/INST]"""

PROMPT_TU_IMPERSONAL = """<s>[INST] <<SYS>>
Eres un experto en redacción académica. Tu única tarea es:
- Transformar verbos en 2ª persona singular (tú impersonal) a la forma impersonal con "se" o infinitivos.
REGLA: No corrijas ortografía ni tildes. No cambies el tiempo verbal. No añadas comentarios. Solo devuelve el texto corregido.
<</SYS>>
Texto a corregir:
[TEXTO] [/INST]"""

PROMPT_FEEDBACK = """<s>[INST] <<SYS>>
Eres un tutor de español meticuloso. Tu tarea es explicar las correcciones realizadas.
Categoriza en: B vs V, G vs J, Y vs LL, uso de H, tildes, C/Z/S o tú impersonal.
Indica: Palabra original -> Palabra corregida y la regla aplicada.
<</SYS>>
Texto original: [ORIGINAL]
Texto corregido: [CORREGIDO]
Explicación: [/INST]"""

# --- GENERACIÓN ---

@torch.inference_mode()
def _generate_once(text: str, mode: str = "ortografia", max_new_tokens: int = 1024) -> str:
    global _tokenizer, _model
    if not MODEL_LOADED or _tokenizer is None or _model is None:
        raise RuntimeError("El modelo no está cargado.")
    
    # Selección de template según el modo
    template = PROMPT_ORTOGRAFIA if mode == "ortografia" else PROMPT_TU_IMPERSONAL
    prompt = template.replace("[TEXTO]", text.strip())
    
    inputs = _tokenizer(prompt, return_tensors="pt", padding=True, truncation=True, max_length=4096)
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
    if not original or not corrected: return ""
    
    # Si el texto es idéntico, no hay feedback
    if original.strip() == corrected.strip():
        return "No se han detectado errores para corregir en este modo."

    # Intentar generar feedback pedagógico con el modelo
    prompt = PROMPT_FEEDBACK.replace("[ORIGINAL]", original).replace("[CORREGIDO]", corrected)
    
    # Si prefieres el feedback por reglas programadas, podrías importar extract_word_changes aquí
    # Por ahora usamos la generación del modelo para mayor flexibilidad pedagógica
    inputs = _tokenizer(prompt, return_tensors="pt", padding=True, truncation=True)
    if hasattr(_model, "device"):
        inputs = {k: v.to(_model.device) for k, v in inputs.items()}
    
    output_ids = _model.generate(**inputs, max_new_tokens=512, do_sample=False, temperature=0.0)
    generated = output_ids[0][inputs["input_ids"].shape[-1]:]
    return _tokenizer.decode(generated, skip_special_tokens=True).strip()

# --- CARGA DEL MODELO ---

def _set(progress: int, message: str):
    global LOAD_PROGRESS, LOAD_MESSAGE
    with _lock:
        LOAD_PROGRESS = max(0, min(100, int(progress)))
        LOAD_MESSAGE = message

def _load_impl():
    global MODEL_LOADED, _tokenizer, _model
    try:
        _set(5, "Iniciando carga del modelo...")
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
            MODEL_ID, quantization_config=nf4_config, device_map="auto", trust_remote_code=True
        )
        _model.eval()
        MODEL_LOADED = True
        _set(100, "✅ Modelo cargado y listo")
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