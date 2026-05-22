# ╔══════════════════════════════════════════════════════════════════╗
# ║     VIDEO PROCESSOR - Modo Dual (Manual / URL)                   ║
# ║     • Manual: Detecta mejores partes → Corta → Título + Subs    ║
# ║     • URL:    Descarga → Edición completa + Cortes + Subs       ║
# ║     Basado en video_editor_v5.py + main.py — NO los modifica     ║
# ╚══════════════════════════════════════════════════════════════════╝

import subprocess, sys, importlib, os, shutil, textwrap, math, requests, json, tempfile, platform, re, argparse, time
from pathlib import Path

# Reconfigurar la salida estándar para soportar emojis en consolas Windows
if platform.system() == "Windows":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

# Directorio temporal portable
TEMP_DIR = tempfile.gettempdir()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BLOQUE 0 ▸ FIX PYTORCH PARA P100 (CUDA 6.0) EN LINUX / COLAB
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def check_and_fix_pytorch():
    if platform.system() != "Linux":
        print("🔍 OS no es Linux. Omitiendo fix de PyTorch.")
        try:
            import torch
            return torch
        except ImportError:
            print("⚠️  PyTorch no está instalado localmente.")
            return None

    try:
        import torch
        if torch.cuda.is_available():
            try:
                test_model = torch.nn.Linear(4, 4).cuda()
                test_x = torch.randn(2, 4).cuda()
                _ = test_model(test_x)
                print("✅ PyTorch CUDA funciona correctamente con la GPU actual.")
                return torch
            except RuntimeError as e:
                print(f"⚠️  PyTorch actual no es compatible con la GPU (sm_60/P100): {e}")
                print("📦 Intentando instalar PyTorch compatible con CUDA 11.8 (cu118)...")
                subprocess.run(
                    [sys.executable, "-m", "pip", "uninstall", "-y", "torch", "torchvision", "torchaudio"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", "-q",
                     "torch", "torchvision", "torchaudio",
                     "--index-url", "https://download.pytorch.org/whl/cu118"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                for k in list(sys.modules.keys()):
                    if "torch" in k:
                        del sys.modules[k]
                import torch
                try:
                    test_model = torch.nn.Linear(4, 4).cuda()
                    test_x = torch.randn(2, 4).cuda()
                    _ = test_model(test_x)
                    print("✅ PyTorch reinstalado con soporte CUDA 11.8 (sm_60) funcionando.")
                except Exception as e2:
                    print(f"⚠️  Incluso tras reinstalación, CUDA falló: {e2}. Se usará CPU.")
                return torch
        else:
            print("⚠️  No hay GPU disponible en PyTorch.")
            return torch
    except Exception as e:
        print(f"⚠️  Error verificando/reparando PyTorch: {e}")
        try:
            import torch
            return torch
        except ImportError:
            return None

torch = check_and_fix_pytorch()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BLOQUE 1 ▸ INSTALACIÓN DE DEPENDENCIAS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _install(pkg, import_as=None):
    name = import_as or pkg.split("==")[0].replace("-","_")
    try:
        importlib.import_module(name)
    except ImportError:
        print(f"📦 Instalando {pkg}...")
        subprocess.check_call(
            [sys.executable,"-m","pip","install","-q","--upgrade","--force-reinstall",pkg],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for mod in list(sys.modules):
            if name in mod: del sys.modules[mod]

_install("openai-whisper", import_as="whisper")
_install("Pillow",         import_as="PIL")
_install("numpy",          import_as="numpy")
_install("requests",       import_as="requests")
_install("yt-dlp",         import_as="yt_dlp")
_install("google-genai",   import_as="google.genai")
_install("python-dotenv",  import_as="dotenv")
_install("faster-whisper", import_as="faster_whisper")

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv

# Cargar variables de entorno (.env)
load_dotenv()

# Verificar ffmpeg
ffmpeg_path = shutil.which("ffmpeg")
if not ffmpeg_path:
    if platform.system() == "Linux":
        print("📦 Instalando ffmpeg...")
        try:
            subprocess.check_call(["apt-get", "update", "-q"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.check_call(["apt-get", "install", "-y", "-q", "ffmpeg"],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print("✅ ffmpeg instalado correctamente via apt-get")
        except Exception as e:
            print(f"⚠️  Error al intentar instalar ffmpeg: {e}")
    else:
        print("❌ ERROR: FFmpeg no está instalado o no se encuentra en el PATH del sistema.")
else:
    print("✅ FFmpeg encontrado en el sistema")

# Whisper robusto
try:
    import whisper
    assert hasattr(whisper,"load_model")
except (ImportError, AssertionError):
    subprocess.check_call([sys.executable,"-m","pip","install","-q",
                           "--force-reinstall","openai-whisper"],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for k in [k for k in sys.modules if "whisper" in k]: del sys.modules[k]
    import whisper

print("✅ Dependencias verificadas correctamente")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BLOQUE 2 ▸ CONFIGURACIÓN
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CONFIG = {
    "input_video":  "video.mp4",
    "output_video": "output_final.mp4",

    "canvas_w": 1080,
    "canvas_h": 1350,
    "video_pct":    0.90,
    "video_top_margin": 30,

    "title_text":       "El Mejor Humor Argentino",
    "title_font_size":  68,
    "title_color":      "#FFDD00",
    "title_stroke":     "#000000",
    "title_stroke_w":   4,
    "bottom_bg":        "#FFFFFF",

    "subtitle_font_size":  58,
    "subtitle_color":      "#FFDD00",
    "subtitle_stroke_w":   4,
    "subtitle_stroke":     "#000000",
    "subtitle_shadow":     "#CC0000",
    "subtitle_shadow_off": 5,
    "subtitle_max_chars":  30,
    "whisper_model":       "large",

    "subscribe_duration": 3.0,
    "subscribe_text":     "¡SUSCRIBITE! 🔔",
    "subscribe_bg":       "#FF0000",
    "subscribe_font_size": 80,
}

# ── Medidas derivadas ───────────────────────────────────────────────
_CW   = CONFIG["canvas_w"]
_CH   = CONFIG["canvas_h"]
_VP   = CONFIG["video_pct"]

VIDEO_W  = int(_CW * _VP)
VIDEO_H  = VIDEO_W
VIDEO_X  = (_CW - VIDEO_W) // 2
VIDEO_Y  = (_CH - VIDEO_H) // 2
BOTTOM_Y = VIDEO_Y + VIDEO_H
VIDEO_CENTER_Y = VIDEO_Y + VIDEO_H // 2

print(f"📐 Layout: Video {VIDEO_W}x{VIDEO_H} en Canvas {_CW}x{_CH}")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BLOQUE 3 ▸ DETECCIÓN GPU, NVENC & FILTROS CUDA
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

os.environ["CUDA_VISIBLE_DEVICES"] = "0"

GPU_AVAILABLE = False
CUDA_CAPABLE = False

if torch is not None:
    try:
        GPU_AVAILABLE = torch.cuda.is_available()
    except Exception:
        pass

if GPU_AVAILABLE:
    try:
        capability = torch.cuda.get_device_capability(0)
        if capability[0] >= 6:
            CUDA_CAPABLE = True
        name = torch.cuda.get_device_name(0)
        vram = torch.cuda.get_device_properties(0).total_memory / 1e9
        print(f"\n🚀 GPU: {name} ({vram:.1f} GB) | CUDA {capability[0]}.{capability[1]}")
    except Exception:
        print(f"\n⚠️  GPU detectada pero no se pudo obtener información detallada.")
else:
    print("\n❌ Sin GPU (Usando CPU)")

# Verificar encoders en FFmpeg
_enc = ""
try:
    _enc = subprocess.run(["ffmpeg","-hide_banner","-encoders"],
                          capture_output=True,text=True).stdout
except Exception:
    pass

NVENC_H264 = "h264_nvenc" in _enc
NVENC_HEVC = "hevc_nvenc" in _enc

print(f"   h264_nvenc encoder: {'✅' if NVENC_H264 else '❌'}")
print(f"   hevc_nvenc encoder: {'✅' if NVENC_HEVC else '❌'}")

def check_ffmpeg_filter(filter_name):
    try:
        r = subprocess.run(["ffmpeg", "-hide_banner", "-filters"], capture_output=True, text=True)
        return filter_name in r.stdout
    except Exception:
        return False

CUDA_FILTERS_AVAILABLE = check_ffmpeg_filter("scale_cuda") and check_ffmpeg_filter("overlay_cuda")
print(f"   scale_cuda/overlay_cuda en FFmpeg: {'✅' if CUDA_FILTERS_AVAILABLE else '❌ (CPU scaling + NVENC)'}")

if NVENC_H264 or NVENC_HEVC:
    ENC_CODER = "h264_nvenc" if NVENC_H264 else "hevc_nvenc"
    ENC_PRESET = "p2"
    ENC_CQ = "23"
    print(f"✅ Encoder NVENC activo: {ENC_CODER}")
    WHISPER_DEVICE = "cuda" if CUDA_CAPABLE else "cpu"
else:
    ENC_CODER = "libx264"
    ENC_PRESET = "fast"
    ENC_CRF = "23"
    WHISPER_DEVICE = "cpu"
    print("⚠️  Sin NVENC, usando codificación de CPU (libx264)")

def get_ffmpeg_gpu_flags():
    return []

def get_encoder_flags():
    if "nvenc" in ENC_CODER:
        return ["-c:v", ENC_CODER, "-preset", ENC_PRESET, "-cq", ENC_CQ,
                "-rc", "vbr", "-b:v", "0", "-maxrate", "10M", "-bufsize", "20M"]
    else:
        return ["-c:v", ENC_CODER, "-preset", ENC_PRESET, "-crf", ENC_CRF]

def get_best_encoder():
    """Detecta soporte NVENC y retorna (vcodec, encode_opts) para alta calidad."""
    try:
        enc_check = subprocess.run(['ffmpeg', '-encoders'], capture_output=True, text=True, check=True)
        if 'h264_nvenc' in enc_check.stdout:
            return 'h264_nvenc', ['-preset', 'p7', '-cq', '18']
    except Exception:
        pass
    return 'libx264', ['-preset', 'medium', '-crf', '18']

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BLOQUE 4 ▸ FUENTE, ESCAPADO & HELPERS PORTABLES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def download_font(path=None):
    if path is None:
        path = os.path.join(TEMP_DIR, "Staatliches-Regular.ttf")
    if Path(path).exists(): return path
    url = "https://github.com/google/fonts/raw/main/ofl/staatliches/Staatliches-Regular.ttf"
    print("⬇️  Descargando fuente Staatliches...")
    try:
        r = requests.get(url, timeout=30)
        Path(path).write_bytes(r.content)
    except Exception as e:
        print(f"⚠️ Error descargando la fuente: {e}. Se buscará una fuente del sistema.")
    return path

FONT_PATH = None
def ensure_font():
    global FONT_PATH
    if FONT_PATH is None or not Path(FONT_PATH).exists():
        FONT_PATH = download_font()
    return FONT_PATH

def get_safe_ffmpeg_path(path_str):
    r"""Escapa rutas de archivo para FFmpeg en Windows y Linux."""
    abs_path = os.path.abspath(path_str)
    if platform.system() == "Windows":
        abs_path = abs_path.replace('\\', '/')
        if len(abs_path) >= 2 and abs_path[1] == ':':
            abs_path = abs_path[0] + chr(92) + ':' + abs_path[2:]
    return abs_path

def run_ffmpeg(cmd, desc="Procesando..."):
    print(f"\n🎬 {desc}")
    global_flags = get_ffmpeg_gpu_flags()
    full = ["ffmpeg", "-y"] + global_flags + cmd

    env = os.environ.copy()
    env["LANG"] = "C.UTF-8"
    env["LC_ALL"] = "C.UTF-8"

    r = subprocess.run(full, capture_output=True, text=True, env=env)
    if r.returncode != 0:
        print("\n❌ " + "!"*50)
        print(f"❌ FFmpeg error detectado en: {desc}")
        print("!"*54)
        print(r.stderr[-1000:] if len(r.stderr) > 1000 else r.stderr)
        print("!"*54 + "\n")
        raise RuntimeError(f"FFmpeg falló en el paso: {desc}")
    return r

def get_video_info(path):
    r = subprocess.run(
        ["ffprobe","-v","quiet","-print_format","json","-show_streams",path],
        capture_output=True, text=True)
    for s in json.loads(r.stdout)["streams"]:
        if s.get("codec_type") == "video":
            w, h = int(s["width"]), int(s["height"])
            n, d = map(int, s.get("r_frame_rate","30/1").split("/"))
            return w, h, n/d, float(s.get("duration",0))
    raise ValueError("No video stream")

def get_audio_info(path):
    try:
        r = subprocess.run(
            ["ffprobe","-v","quiet","-print_format","json","-show_streams",path],
            capture_output=True, text=True)
        data = json.loads(r.stdout)
        for s in data.get("streams", []):
            if s.get("codec_type") == "audio":
                sample_rate = int(s.get("sample_rate", 44100))
                channels = int(s.get("channels", 2))
                return sample_rate, channels
    except Exception as e:
        print(f"⚠️ Error obteniendo información de audio: {e}")
    return 44100, 2

def hex2rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2],16) for i in (0,2,4))

def sanitize_filename(filename):
    """Elimina caracteres inválidos de un nombre de archivo."""
    filename = re.sub(r'[<>:"/\\|?*#]', '', filename)
    filename = filename.replace(' ', '_')
    return filename[:100]

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BLOQUE 5 ▸ DESCARGA DE VIDEO POR URL (yt-dlp)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def is_url(text):
    """Detecta si el input es una URL de video."""
    url_patterns = [
        r'https?://(www\.)?(youtube\.com|youtu\.be)',
        r'https?://(www\.)?(tiktok\.com)',
        r'https?://(www\.)?(instagram\.com)',
        r'https?://(www\.)?(twitter\.com|x\.com)',
        r'https?://(www\.)?(facebook\.com|fb\.watch)',
        r'https?://',
    ]
    for pattern in url_patterns:
        if re.match(pattern, text.strip()):
            return True
    return False

def download_video_from_url(url, output_dir=None):
    """Descarga un video desde una URL usando yt-dlp con la mejor calidad."""
    if output_dir is None:
        output_dir = TEMP_DIR
    
    print(f"\n⬇️  Descargando video desde URL...")
    print(f"   🔗 {url}")
    
    # Buscar cookies.txt en el directorio del script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cookies_file = os.path.join(script_dir, "cookies.txt")
    
    # Primero obtener info para el nombre del archivo
    ydl_info_opts = {
        'quiet': True,
        'no_warnings': True,
    }
    if Path(cookies_file).exists():
        ydl_info_opts['cookiefile'] = cookies_file
        print(f"   🍪 Usando cookies de: {cookies_file}")
    
    try:
        import yt_dlp
        with yt_dlp.YoutubeDL(ydl_info_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            video_title = info.get('title', 'downloaded_video')
            sanitized_title = sanitize_filename(video_title)
    except Exception:
        sanitized_title = "downloaded_video"
        video_title = sanitized_title
    
    output_path = os.path.join(output_dir, f"{sanitized_title}.mp4")
    
    ydl_opts = {
        'format': 'bestvideo[vcodec^=avc1][ext=mp4]+bestaudio[ext=m4a]/bestvideo[vcodec^=avc1]+bestaudio/best[ext=mp4]/best',
        'outtmpl': output_path,
        'merge_output_format': 'mp4',
        'overwrites': True,
        'quiet': False,
        'no_warnings': False,
        'no_playlist': True,
    }
    if Path(cookies_file).exists():
        ydl_opts['cookiefile'] = cookies_file
    
    try:
        import yt_dlp
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        if Path(output_path).exists():
            size_mb = Path(output_path).stat().st_size / (1024*1024)
            print(f"   ✅ Video descargado: {output_path} ({size_mb:.1f} MB)")
            return output_path, sanitized_title
        else:
            raise FileNotFoundError("yt-dlp no generó archivo de salida")
    except Exception as e:
        print(f"❌ Error descargando video: {e}")
        raise

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BLOQUE 6 ▸ TRANSCRIPCIÓN (faster-whisper para detección de clips)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def transcribe_for_clips(video_path):
    """
    Transcribe el video con faster-whisper para obtener timestamps por palabra.
    Usado para enviar a Gemini y detectar momentos virales.
    """
    from faster_whisper import WhisperModel

    if torch is not None and torch.cuda.is_available():
        device = "cuda"
        compute_type = "float16"
        model_size = "large-v3"
        print(f"\n🎙️  Transcribiendo con Faster-Whisper GPU ({torch.cuda.get_device_name(0)})")
        print(f"   Modelo: {model_size} | Device: {device} | Compute: {compute_type}")
    else:
        device = "cpu"
        compute_type = "int8"
        model_size = "base"
        print(f"\n🎙️  Transcribiendo con Faster-Whisper CPU (modelo: {model_size})")

    model = WhisperModel(model_size, device=device, compute_type=compute_type)
    segments, info = model.transcribe(video_path, word_timestamps=True)

    print(f"   Idioma detectado: '{info.language}' (prob: {info.language_probability:.2f})")

    transcript_segments = []
    full_text = ""

    for segment in segments:
        print(f"   [{segment.start:.2f}s -> {segment.end:.2f}s] {segment.text}")
        seg_dict = {
            'text': segment.text,
            'start': segment.start,
            'end': segment.end,
            'words': []
        }
        if segment.words:
            for word in segment.words:
                seg_dict['words'].append({
                    'word': word.word,
                    'start': word.start,
                    'end': word.end,
                    'probability': word.probability
                })
        transcript_segments.append(seg_dict)
        full_text += segment.text + " "

    del model
    if torch is not None and torch.cuda.is_available():
        torch.cuda.empty_cache()

    return {
        'text': full_text.strip(),
        'segments': transcript_segments,
        'language': info.language
    }

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BLOQUE 7 ▸ DETECCIÓN DE CLIPS VIRALES CON GEMINI
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

GEMINI_PROMPT_TEMPLATE = """
You are a senior short-form video editor. Read the ENTIRE transcript and word-level timestamps to choose the 3–15 MOST VIRAL moments for TikTok/IG Reels/YouTube Shorts. Each clip must be between 15 and 60 seconds long.

⚠️ FFMPEG TIME CONTRACT — STRICT REQUIREMENTS:
- Return timestamps in ABSOLUTE SECONDS from the start of the video (usable in: ffmpeg -ss <start> -to <end> -i <input> ...).
- Only NUMBERS with decimal point, up to 3 decimals (examples: 0, 1.250, 17.350).
- Ensure 0 ≤ start < end ≤ VIDEO_DURATION_SECONDS.
- Each clip between 15 and 60 s (inclusive).
- Prefer starting 0.2–0.4 s BEFORE the hook and ending 0.2–0.4 s AFTER the payoff.
- Use silence moments for natural cuts; never cut in the middle of a word or phrase.
- STRICTLY FORBIDDEN to use time formats other than absolute seconds.

VIDEO_DURATION_SECONDS: {video_duration}

TRANSCRIPT_TEXT (raw):
{transcript_text}

WORDS_JSON (array of {{w, s, e}} where s/e are seconds):
{words_json}

STRICT EXCLUSIONS:
- No generic intros/outros or purely sponsorship segments unless they contain the hook.
- No clips < 15 s or > 60 s.

OUTPUT — RETURN ONLY VALID JSON (no markdown, no comments). Order clips by predicted performance (best to worst). In the descriptions, ALWAYS include a CTA like "Follow me and comment X and I'll send you the workflow" (especially if discussing an n8n workflow):
{{
  "shorts": [
    {{
      "start": <number in seconds, e.g., 12.340>,
      "end": <number in seconds, e.g., 37.900>,
      "video_description_for_tiktok": "<description for TikTok oriented to get views>",
      "video_description_for_instagram": "<description for Instagram oriented to get views>",
      "video_title_for_youtube_short": "<title for YouTube Short oriented to get views 100 chars max>",
      "viral_hook_text": "<SHORT punchy text overlay (max 10 words). MUST BE IN THE SAME LANGUAGE AS THE VIDEO TRANSCRIPT. Examples: 'POV: You realized...', 'Did you know?', 'Stop doing this!'>"
    }}
  ]
}}
"""

def get_viral_clips(transcript_result, video_duration, gemini_api_key=None):
    """Usa Gemini AI para detectar los momentos más virales del video."""
    print("\n🤖  Analizando con Gemini para detectar mejores partes...")

    api_key = gemini_api_key or os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ Error: GEMINI_API_KEY no encontrada.")
        print("   Configurala con: export GEMINI_API_KEY=tu_clave")
        print("   O en archivo .env: GEMINI_API_KEY=tu_clave")
        return None

    from google import genai
    client = genai.Client(api_key=api_key)
    model_name = 'gemini-2.5-flash'

    print(f"   Modelo: {model_name}")

    # Extraer palabras con timestamps
    words = []
    for segment in transcript_result['segments']:
        for word in segment.get('words', []):
            words.append({
                'w': word['word'],
                's': word['start'],
                'e': word['end']
            })

    prompt = GEMINI_PROMPT_TEMPLATE.format(
        video_duration=video_duration,
        transcript_text=json.dumps(transcript_result['text']),
        words_json=json.dumps(words)
    )

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt
        )

        # Log de tokens y costo
        try:
            usage = response.usage_metadata
            if usage:
                input_cost = (usage.prompt_token_count / 1_000_000) * 0.10
                output_cost = (usage.candidates_token_count / 1_000_000) * 0.40
                total_cost = input_cost + output_cost
                print(f"   💰 Tokens: {usage.prompt_token_count} in + {usage.candidates_token_count} out = ${total_cost:.6f}")
        except Exception:
            pass

        # Limpiar respuesta
        text = response.text
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        result_json = json.loads(text)
        return result_json
    except Exception as e:
        print(f"❌ Error de Gemini: {e}")
        return None

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BLOQUE 8 ▸ CORTE DE CLIPS CON FFMPEG
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def cut_clips(input_video, clips_data, output_dir):
    """
    Corta los clips detectados por Gemini del video original.
    Guarda cada clip como archivo independiente en output_dir.
    Retorna lista de rutas a los clips cortados.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    clip_paths = []
    vcodec, encode_opts = get_best_encoder()
    
    for i, clip in enumerate(clips_data['shorts']):
        start = clip['start']
        end = clip['end']
        title = clip.get('video_title_for_youtube_short', f'clip_{i+1}')
        
        clip_filename = f"clip_{i+1:02d}.mp4"
        clip_path = os.path.join(output_dir, clip_filename)
        
        print(f"\n   ✂️  Cortando Clip {i+1}/{len(clips_data['shorts'])}: {start:.1f}s - {end:.1f}s ({end-start:.1f}s)")
        print(f"   📌 {title}")
        
        # Corte preciso con re-encoding
        cut_cmd = [
            'ffmpeg', '-y',
            '-ss', str(start),
            '-to', str(end),
            '-i', input_video,
            '-c:v', vcodec, *encode_opts,
            '-c:a', 'aac',
            clip_path
        ]
        
        result = subprocess.run(cut_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"   ⚠️  Error cortando clip {i+1}: {result.stderr[-300:]}")
            continue
        
        if Path(clip_path).exists():
            size_mb = Path(clip_path).stat().st_size / (1024*1024)
            print(f"   ✅ Clip {i+1} guardado: {clip_filename} ({size_mb:.1f} MB)")
            clip_paths.append(clip_path)
        else:
            print(f"   ❌ Clip {i+1} no se generó")
    
    return clip_paths

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BLOQUE 9 ▸ PASOS DE EDICIÓN (crop, canvas, título, subtítulos)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def step_crop_1x1(src, dst=None):
    """Recorta el video a formato cuadrado 1:1"""
    if dst is None:
        dst = os.path.join(TEMP_DIR, "s1_1x1.mp4")
    w, h, fps, dur = get_video_info(src)
    side = min(w,h)
    x, y = (w-side)//2, (h-side)//2

    run_ffmpeg(
        ["-i", src,
         "-vf", f"crop={side}:{side}:{x}:{y}",
         *get_encoder_flags(), "-c:a","copy", dst],
        "Crop 1:1")
    return dst

def step_canvas_4x5(src, dst=None):
    """Coloca el video cuadrado en un lienzo 4:5 con fondo blur"""
    if dst is None:
        dst = os.path.join(TEMP_DIR, "s2_4x5.mp4")
    cw, ch = _CW, _CH
    vw, vh = VIDEO_W, VIDEO_H
    vx, vy = VIDEO_X, VIDEO_Y

    vf = (
        f"[0:v]scale={cw}:{ch}:force_original_aspect_ratio=increase,crop={cw}:{ch},boxblur=30:5[bg];"
        f"[0:v]scale={vw}:{vh}[fg];"
        f"[bg][fg]overlay={vx}:{vy}[out]"
    )

    run_ffmpeg(
        ["-i", src,
         "-filter_complex", vf,
         "-map", "[out]", "-map", "0:a?",
         *get_encoder_flags(),
         "-c:a","aac","-b:a","192k", dst],
        "Canvas 4:5 (Fondo Blur)")
    return dst

def make_bottom_overlay(cfg):
    """Crea el overlay del título con cajita blanca redondeada"""
    font_path = ensure_font()
    img  = Image.new("RGBA", (_CW, _CH), (0,0,0,0))
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype(font_path, cfg["title_font_size"])
    except Exception:
        font = ImageFont.load_default()

    text = cfg["title_text"].upper()

    bbox = draw.textbbox((0,0), text, font=font, stroke_width=cfg["title_stroke_w"])
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    pad_x = 40
    pad_y = 20
    box_w = tw + pad_x * 2
    box_h = th + pad_y * 2

    box_x = (_CW - box_w) // 2
    video_bottom = VIDEO_Y + VIDEO_H
    box_y = video_bottom - box_h // 2

    radius = 18
    draw.rounded_rectangle(
        [box_x, box_y, box_x + box_w, box_y + box_h],
        radius=radius,
        fill=(255, 255, 255, 255)
    )

    tx = box_x + pad_x - bbox[0]
    ty = box_y + pad_y - bbox[1]

    draw.text(
        (tx, ty), text, font=font,
        fill=(*hex2rgb(cfg["title_color"]), 255),
        stroke_width=cfg["title_stroke_w"],
        stroke_fill=(*hex2rgb(cfg["title_stroke"]), 255)
    )
    return img

def step_add_title(src, dst=None):
    """Agrega el título con cajita blanca sobre el video"""
    if dst is None:
        dst = os.path.join(TEMP_DIR, "s_title.mp4")
    overlay_img = make_bottom_overlay(CONFIG)
    png = os.path.join(TEMP_DIR, "bottom_overlay.png")
    overlay_img.save(png)

    run_ffmpeg(
        ["-i", src, "-i", png,
         "-filter_complex", "[0:v][1:v]overlay=0:0[out]",
         "-map", "[out]", "-map", "0:a?",
         *get_encoder_flags(), "-c:a","copy", dst],
        "Título + Overlay")
    return dst

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BLOQUE 10 ▸ WHISPER + SUBTÍTULOS (quemado en cada clip)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def transcribe_video_whisper(path, cfg):
    """Transcribe el audio del video usando openai-whisper para generar subtítulos."""
    device = WHISPER_DEVICE
    use_fp16 = (device == "cuda")

    print(f"\n🎙️  Whisper '{cfg['whisper_model']}' en {device.upper()} (FP16={use_fp16})")
    if device == "cuda" and torch is not None:
        torch.cuda.empty_cache()

    try:
        model = whisper.load_model(cfg["whisper_model"], device=device)
        result = model.transcribe(path, language="es", word_timestamps=True,
                                  verbose=False, fp16=use_fp16,
                                  beam_size=5, temperature=0.0)
    except Exception as e:
        print(f"⚠️  Error ejecutando Whisper en {device}: {e}")
        print("🔄 Haciendo fallback a CPU...")
        device = "cpu"
        use_fp16 = False
        if 'model' in locals():
            try: del model
            except: pass
        if torch is not None and torch.cuda.is_available():
            try: torch.cuda.empty_cache()
            except: pass

        model = whisper.load_model(cfg["whisper_model"], device="cpu")
        result = model.transcribe(path, language="es", word_timestamps=True,
                                  verbose=False, fp16=use_fp16,
                                  beam_size=5, temperature=0.0)

    segs = [{"start":s["start"],"end":s["end"],"text":s["text"].strip()}
            for s in result["segments"]]
    try: del model
    except: pass
    if device == "cuda" and torch is not None:
        try: torch.cuda.empty_cache()
        except: pass
    print(f"   ✅ {len(segs)} segmentos transcritos")
    return segs

def make_ass(segs, cfg, path=None):
    """Genera archivo de subtítulos .ASS"""
    if path is None:
        path = os.path.join(TEMP_DIR, "subs.ass")

    def rgb2ass(hex_color, alpha=0):
        r,g,b = hex2rgb(hex_color)
        return f"&H{alpha:02X}{b:02X}{g:02X}{r:02X}"

    fs = cfg["subtitle_font_size"]
    sw = cfg["subtitle_stroke_w"]
    shoff = cfg["subtitle_shadow_off"]

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {_CW}
PlayResY: {_CH}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Sub,Staatliches,{fs},{rgb2ass(cfg['subtitle_color'])},{rgb2ass('#000000')},{rgb2ass(cfg['subtitle_stroke'])},{rgb2ass(cfg['subtitle_shadow'],alpha=80)},0,0,0,0,100,100,0,0,1,{sw},{shoff},5,0,0,0,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""
    def ft(t):
        h=int(t//3600); m=int((t%3600)//60); s=t%60
        return f"{h:01d}:{m:02d}:{s:05.2f}"

    lines = [header]
    for seg in segs:
        txt = seg["text"].replace("\n","\\N")
        if len(txt) > cfg["subtitle_max_chars"]:
            txt = textwrap.fill(txt, cfg["subtitle_max_chars"]).replace("\n","\\N")
        lines.append(
            f"Dialogue: 0,{ft(seg['start'])},{ft(seg['end'])},"
            f"Sub,,0,0,0,,{{\\pos({_CW//2},{VIDEO_Y + int(VIDEO_H * 0.75)})}}{txt}")

    Path(path).write_text("\n".join(lines), encoding="utf-8")
    return path

def step_add_subtitles(src, dst=None):
    """Transcribe y quema subtítulos en el video"""
    if dst is None:
        dst = os.path.join(TEMP_DIR, "s_subs.mp4")

    cfg = CONFIG
    segs = transcribe_video_whisper(src, cfg)

    font_src = ensure_font()
    font_name = os.path.basename(font_src)
    font_dst = os.path.join(TEMP_DIR, font_name)
    if font_src != font_dst:
        shutil.copy(font_src, font_dst)

    ass = make_ass(segs, cfg)

    safe_ass = get_safe_ffmpeg_path(ass)
    safe_fontsdir = get_safe_ffmpeg_path(TEMP_DIR)

    run_ffmpeg(
        ["-i", src,
         "-vf", f"ass='{safe_ass}':fontsdir='{safe_fontsdir}'",
         *get_encoder_flags(), "-c:a","copy", dst],
        "Subtítulos (Whisper)")
    return dst, segs

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BLOQUE 11 ▸ STICKER FINAL (solo modo URL / edición completa)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def make_subscribe_frame(cfg):
    font_path = ensure_font()
    w, h = _CW, _CH
    img  = Image.new("RGB",(w,h), hex2rgb(cfg["subscribe_bg"]))
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype(font_path, cfg["subscribe_font_size"])
    except Exception:
        font = ImageFont.load_default()

    text = cfg["subscribe_text"]
    bbox = draw.textbbox((0,0),text,font=font)
    tw,th = bbox[2]-bbox[0], bbox[3]-bbox[1]
    x = (w-tw)//2 - bbox[0]
    y = (h-th)//2 - bbox[1]
    draw.text((x+4,y+4),text,font=font,fill=(100,0,0))
    draw.text((x,y),text,font=font,fill=(255,255,255))
    for m in [20,30]:
        draw.rectangle([m,m,w-m,h-m],outline=(255,255,255),width=4)
    return img

def step_add_subscribe(src, dst):
    """Agrega el sticker de suscripción al final del video"""
    cfg = CONFIG
    w,h,fps,dur = get_video_info(src)
    dt  = cfg["subscribe_duration"]

    png = os.path.join(TEMP_DIR, "subscribe.png")
    make_subscribe_frame(cfg).save(png)

    sticker = os.path.join(TEMP_DIR, "sticker.mp4")
    run_ffmpeg(["-loop","1","-i",png,"-t",str(dt),
                "-vf",f"scale={w}:{h},format=yuv420p","-r",str(int(fps)),
                *get_encoder_flags(),"-an", sticker],
               "Generando Sticker")

    sample_rate, channels = get_audio_info(src)
    channel_layout = "stereo" if channels >= 2 else "mono"

    silence = os.path.join(TEMP_DIR, "silence.aac")
    run_ffmpeg(["-f","lavfi","-i",f"anullsrc=r={sample_rate}:cl={channel_layout}",
                "-t",str(dt),"-c:a","aac","-b:a","192k", silence],
               "Audio Silencio")

    sticker_av = os.path.join(TEMP_DIR, "sticker_av.mp4")
    run_ffmpeg(["-i",sticker,"-i",silence,
                "-c:v","copy","-c:a","copy","-shortest", sticker_av],
               "Uniendo Sticker + Silencio")

    lst = os.path.join(TEMP_DIR, "concat.txt")
    safe_src_path = os.path.abspath(src).replace('\\', '/')
    safe_sticker_av_path = os.path.abspath(sticker_av).replace('\\', '/')

    Path(lst).write_text(
        f"file '{safe_src_path}'\nfile '{safe_sticker_av_path}'\n",
        encoding="utf-8")

    run_ffmpeg(["-f","concat","-safe","0","-i",lst,"-c","copy", dst],
               "Concatenar Sticker Final")
    return dst

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BLOQUE 12 ▸ PROCESO POR CLIP (título + subtítulos sobre cada clip)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def process_single_clip(clip_path, output_path, clip_num, total_clips, do_full_edit=False):
    """
    Procesa un clip individual:
    - do_full_edit=False (manual): Solo título + subtítulos
    - do_full_edit=True (URL):     Crop → Canvas → Título → Subtítulos → Sticker
    """
    print(f"\n{'━'*60}")
    print(f"  🎬 Procesando Clip {clip_num}/{total_clips}")
    print(f"  📁 {os.path.basename(clip_path)}")
    print(f"{'━'*60}")

    try:
        if do_full_edit:
            # MODO URL: Edición completa
            s1 = step_crop_1x1(clip_path)
            s2 = step_canvas_4x5(s1)
            s3 = step_add_title(s2)
            s4, segs = step_add_subtitles(s3)
            final = step_add_subscribe(s4, output_path)
        else:
            # MODO MANUAL: Solo título + subtítulos
            s1 = step_add_title(clip_path)
            final, segs = step_add_subtitles(s1, output_path)

        info = get_video_info(output_path)
        print(f"\n  ✅ Clip {clip_num} listo: {os.path.basename(output_path)}")
        print(f"  📐 {info[0]}×{info[1]} | {info[2]:.0f}fps | {info[3]:.1f}s | 🎙 {len(segs)} subs")
        return True
    except Exception as e:
        print(f"\n  ❌ Error procesando clip {clip_num}: {e}")
        import traceback
        traceback.print_exc()
        return False

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BLOQUE 13 ▸ PIPELINES PRINCIPALES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def run_manual_pipeline(input_video, output_dir=None, gemini_api_key=None):
    """
    MODO MANUAL — Video ya editado (cargado localmente).
    1. Transcribe el video completo (faster-whisper)
    2. Gemini detecta las mejores partes virales
    3. Corta los clips y los guarda en una carpeta
    4. A cada clip le pone Título + Subtítulos
    """
    try:
        start_time = time.time()
        src = input_video

        if not Path(src).exists():
            raise FileNotFoundError(f"❌ El archivo de entrada no existe: {src}")

        video_name = Path(src).stem
        if output_dir is None:
            output_dir = os.path.join(os.path.dirname(os.path.abspath(src)), f"{video_name}_clips")
        
        os.makedirs(output_dir, exist_ok=True)

        w, h, fps, dur = get_video_info(src)

        print("\n" + "═"*60)
        print("  🎬  VIDEO PROCESSOR — MODO MANUAL")
        print("  📋  Detectar mejores partes → Cortar → Título + Subtítulos")
        print(f"  📥  Origen:  {src}")
        print(f"  📂  Carpeta: {output_dir}")
        print(f"  📐  Video:   {w}×{h} | {fps:.2f}fps | {dur:.1f}s")
        print("═"*60)

        # Paso 1: Transcribir video completo
        print("\n📍 PASO 1/4: Transcripción del video completo")
        transcript = transcribe_for_clips(src)

        # Paso 2: Detectar clips virales con Gemini
        print("\n📍 PASO 2/4: Detección de mejores momentos (Gemini AI)")
        clips_data = get_viral_clips(transcript, dur, gemini_api_key)

        if not clips_data or 'shorts' not in clips_data:
            print("❌ No se pudieron detectar clips. Procesando video completo como un solo clip...")
            # Fallback: procesar video entero
            output_path = os.path.join(output_dir, f"{video_name}_final.mp4")
            s1 = step_add_title(src)
            step_add_subtitles(s1, output_path)
            print(f"\n✅ Video procesado como clip único: {output_path}")
            return output_dir

        num_clips = len(clips_data['shorts'])
        print(f"\n🔥 {num_clips} momentos virales detectados!")

        # Guardar metadata
        metadata_file = os.path.join(output_dir, "metadata.json")
        clips_data['transcript'] = transcript
        clips_data['source_video'] = os.path.abspath(src)
        clips_data['mode'] = 'manual'
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(clips_data, f, indent=2, ensure_ascii=False)
        print(f"   📄 Metadata guardada: {metadata_file}")

        # Paso 3: Cortar clips del video original
        print(f"\n📍 PASO 3/4: Cortando {num_clips} clips del video")
        raw_clips_dir = os.path.join(output_dir, "raw_clips")
        clip_paths = cut_clips(src, clips_data, raw_clips_dir)

        if not clip_paths:
            print("❌ No se pudo cortar ningún clip.")
            return output_dir

        # Paso 4: Procesar cada clip (título + subtítulos)
        print(f"\n📍 PASO 4/4: Aplicando Título + Subtítulos a {len(clip_paths)} clips")
        processed_count = 0
        for i, clip_path in enumerate(clip_paths):
            output_clip = os.path.join(output_dir, f"clip_{i+1:02d}_final.mp4")
            success = process_single_clip(clip_path, output_clip, i+1, len(clip_paths), do_full_edit=False)
            if success:
                processed_count += 1

        elapsed = time.time() - start_time
        print("\n" + "═"*60)
        print(f"  ✅  PROCESAMIENTO COMPLETADO")
        print(f"  📂  Carpeta: {output_dir}")
        print(f"  🎬  Clips procesados: {processed_count}/{num_clips}")
        print(f"  ⏱️   Tiempo total: {elapsed:.1f}s")
        print("═"*60)

        # Listar archivos finales
        print(f"\n📁 Contenido de {output_dir}:")
        for f in sorted(os.listdir(output_dir)):
            fpath = os.path.join(output_dir, f)
            if os.path.isfile(fpath):
                size_mb = os.path.getsize(fpath) / (1024*1024)
                print(f"   📄 {f} ({size_mb:.1f} MB)")
            elif os.path.isdir(fpath):
                count = len(os.listdir(fpath))
                print(f"   📂 {f}/ ({count} archivos)")

        return output_dir
    except Exception as e:
        print("\n" + "═"*60)
        print(f"  ❌  ERROR: {e}")
        print("═"*60)
        import traceback
        traceback.print_exc()
        return None


def run_url_pipeline(url, output_dir=None, gemini_api_key=None):
    """
    MODO URL — Edición completa.
    1. Descarga el video
    2. Transcribe (faster-whisper)
    3. Gemini detecta mejores partes
    4. Corta clips
    5. A cada clip: Crop → Canvas → Título → Subtítulos → Sticker
    """
    try:
        start_time = time.time()

        if output_dir is None:
            output_dir = os.path.join(os.getcwd(), "clips_output")
        os.makedirs(output_dir, exist_ok=True)

        print("\n" + "═"*60)
        print("  🌐  VIDEO PROCESSOR — MODO URL (EDICIÓN COMPLETA)")
        print(f"  🔗  URL: {url}")
        print(f"  📂  Carpeta: {output_dir}")
        print("═"*60)

        # Paso 0: Descargar video
        print("\n📍 PASO 0/5: Descargando video")
        src, video_title = download_video_from_url(url, output_dir)

        w, h, fps, dur = get_video_info(src)
        print(f"  📐 Video: {w}×{h} | {fps:.2f}fps | {dur:.1f}s")

        # Paso 1: Transcribir
        print("\n📍 PASO 1/5: Transcripción del video completo")
        transcript = transcribe_for_clips(src)

        # Paso 2: Detectar clips con Gemini
        print("\n📍 PASO 2/5: Detección de mejores momentos (Gemini AI)")
        clips_data = get_viral_clips(transcript, dur, gemini_api_key)

        if not clips_data or 'shorts' not in clips_data:
            print("❌ No se pudieron detectar clips. Procesando video completo...")
            output_path = os.path.join(output_dir, f"{video_title}_final.mp4")
            s1 = step_crop_1x1(src)
            s2 = step_canvas_4x5(s1)
            s3 = step_add_title(s2)
            s4, _ = step_add_subtitles(s3)
            step_add_subscribe(s4, output_path)
            return output_dir

        num_clips = len(clips_data['shorts'])
        print(f"\n🔥 {num_clips} momentos virales detectados!")

        # Guardar metadata
        metadata_file = os.path.join(output_dir, "metadata.json")
        clips_data['transcript'] = transcript
        clips_data['source_url'] = url
        clips_data['mode'] = 'url'
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(clips_data, f, indent=2, ensure_ascii=False)

        # Paso 3: Cortar clips
        print(f"\n📍 PASO 3/5: Cortando {num_clips} clips")
        raw_clips_dir = os.path.join(output_dir, "raw_clips")
        clip_paths = cut_clips(src, clips_data, raw_clips_dir)

        if not clip_paths:
            print("❌ No se pudo cortar ningún clip.")
            return output_dir

        # Paso 4: Procesar cada clip (edición completa)
        print(f"\n📍 PASO 4/5: Edición completa de {len(clip_paths)} clips")
        processed_count = 0
        for i, clip_path in enumerate(clip_paths):
            output_clip = os.path.join(output_dir, f"clip_{i+1:02d}_final.mp4")
            success = process_single_clip(clip_path, output_clip, i+1, len(clip_paths), do_full_edit=True)
            if success:
                processed_count += 1

        # Paso 5: Limpiar video original descargado (opcional)
        elapsed = time.time() - start_time
        print("\n" + "═"*60)
        print(f"  ✅  EDICIÓN COMPLETA FINALIZADA")
        print(f"  📂  Carpeta: {output_dir}")
        print(f"  🎬  Clips procesados: {processed_count}/{num_clips}")
        print(f"  ⏱️   Tiempo total: {elapsed:.1f}s")
        print("═"*60)

        # Listar archivos finales
        print(f"\n📁 Contenido de {output_dir}:")
        for f in sorted(os.listdir(output_dir)):
            fpath = os.path.join(output_dir, f)
            if os.path.isfile(fpath):
                size_mb = os.path.getsize(fpath) / (1024*1024)
                print(f"   📄 {f} ({size_mb:.1f} MB)")
            elif os.path.isdir(fpath):
                count = len(os.listdir(fpath))
                print(f"   📂 {f}/ ({count} archivos)")

        return output_dir
    except Exception as e:
        print("\n" + "═"*60)
        print(f"  ❌  ERROR: {e}")
        print("═"*60)
        import traceback
        traceback.print_exc()
        return None


def run_auto(input_source, output_dir=None, gemini_api_key=None):
    """
    MODO AUTOMÁTICO — Detecta si es URL o archivo local.
    • URL → Pipeline completo (descarga + edición + cortes + subs)
    • Archivo local → Solo detectar partes + cortar + título + subs
    """
    input_source = input_source.strip()

    if is_url(input_source):
        print("\n🌐 Detectado: URL de video → Edición completa")
        return run_url_pipeline(input_source, output_dir, gemini_api_key)
    else:
        print("\n📁 Detectado: Archivo local → Detectar mejores partes + Título + Subtítulos")
        return run_manual_pipeline(input_source, output_dir, gemini_api_key)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BLOQUE 14 ▸ CLI
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Video Processor — Detecta mejores partes, corta clips y aplica edición",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
        ╔══════════════════════════════════════════════════════════╗
        ║                    MODOS DE USO                         ║
        ╠══════════════════════════════════════════════════════════╣
        ║                                                         ║
        ║  📁 MODO MANUAL (video local ya editado):               ║
        ║     → Detecta mejores partes (Gemini)                   ║
        ║     → Corta los clips                                   ║
        ║     → Les pone Título + Subtítulos                      ║
        ║                                                         ║
        ║  🌐 MODO URL (video de internet):                       ║
        ║     → Descarga + Edición completa                       ║
        ║     → Crop 1:1, Canvas 4:5, Blur                       ║
        ║     → Título + Subtítulos + Sticker                     ║
        ║                                                         ║
        ╚══════════════════════════════════════════════════════════╝

        Ejemplos:
        
          # Modo manual (detecta automáticamente):
          python video_processor.py mi_video.mp4
          python video_processor.py mi_video.mp4 -o carpeta_salida
          
          # Modo URL (detecta automáticamente):
          python video_processor.py "https://www.youtube.com/watch?v=XXXXX"
          
          # Forzar modo:
          python video_processor.py mi_video.mp4 --mode manual
          python video_processor.py "https://..." --mode url
          
          # Cambiar título:
          python video_processor.py mi_video.mp4 --title "Mi Canal"
          
          # Cambiar modelo de Whisper:
          python video_processor.py mi_video.mp4 --whisper-model medium
          
          # Pasar API key de Gemini directamente:
          python video_processor.py mi_video.mp4 --gemini-key "AIza..."
        """)
    )

    parser.add_argument("input", help="Archivo de video local O URL (YouTube, TikTok, etc.)")
    parser.add_argument("-o", "--output", default=None, help="Carpeta de salida para los clips")
    parser.add_argument("--mode", choices=["auto", "manual", "url"], default="auto",
                        help="Forzar modo: 'manual' (solo título+subs), 'url' (edición completa), 'auto' (detecta)")
    parser.add_argument("--title", default=None, help="Texto del título (default: 'El Mejor Humor Argentino')")
    parser.add_argument("--whisper-model", default=None, choices=["tiny","base","small","medium","large"],
                        help="Modelo de Whisper para subtítulos (default: large)")
    parser.add_argument("--gemini-key", default=None, help="API Key de Gemini (sino usa .env o env var)")

    args = parser.parse_args()

    # Aplicar opciones de configuración
    if args.title:
        CONFIG["title_text"] = args.title
    if args.whisper_model:
        CONFIG["whisper_model"] = args.whisper_model

    # Ejecutar según modo
    if args.mode == "manual":
        result = run_manual_pipeline(args.input, args.output, args.gemini_key)
    elif args.mode == "url":
        result = run_url_pipeline(args.input, args.output, args.gemini_key)
    else:
        result = run_auto(args.input, args.output, args.gemini_key)

    if result:
        print(f"\n🎉 Clips guardados en: {result}")
    else:
        print("\n❌ El procesamiento falló.")
        sys.exit(1)
