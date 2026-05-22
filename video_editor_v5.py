# ╔══════════════════════════════════════════════════════════════════╗
# ║     EL MEJOR HUMOR ARGENTINO - VIDEO EDITOR  v5 (PORTABLE)       ║
# ║     Soporte Tesla P100 (CUDA 6.0) + NVENC & Windows Local        ║
# ╚══════════════════════════════════════════════════════════════════╝

import subprocess, sys, importlib, os, shutil, textwrap, math, requests, json, tempfile, platform
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
    """
    Tesla P100 = CUDA 6.0 (sm_60).
    PyTorch por defecto en algunos entornos modernos requiere sm_70+, lo que arroja error al usar CUDA.
    Verificamos si CUDA funciona realmente ejecutando una operación básica.
    Si falla, instalamos PyTorch compilado con CUDA 11.8 (cu118) que sí soporta sm_60
    y es totalmente compatible con Python 3.10/3.11+.
    """
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
            # Prueba real para verificar si el kernel es compatible con sm_60 (P100)
            try:
                # Una capa lineal con datos activa cuBLAS y operaciones complejas.
                # Si PyTorch carece de kernels para sm_60, esto fallará inmediatamente.
                test_model = torch.nn.Linear(4, 4).cuda()
                test_x = torch.randn(2, 4).cuda()
                _ = test_model(test_x)
                print("✅ PyTorch CUDA funciona correctamente con la GPU actual.")
                return torch
            except RuntimeError as e:
                print(f"⚠️  PyTorch actual no es compatible con la GPU (sm_60/P100): {e}")
                print("📦 Intentando instalar PyTorch compatible con CUDA 11.8 (cu118)...")
                
                # Desinstalar PyTorch actual
                subprocess.run(
                    [sys.executable, "-m", "pip", "uninstall", "-y", "torch", "torchvision", "torchaudio"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                
                # Instalar versión moderna compilada para CUDA 11.8 (soporta sm_60)
                # Esta versión tiene wheels para Python 3.10, 3.11, etc.
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", "-q", 
                     "torch", "torchvision", "torchaudio", 
                     "--index-url", "https://download.pytorch.org/whl/cu118"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                
                # Limpiar cache de módulos importados para recargar torch
                for k in list(sys.modules.keys()):
                    if "torch" in k:
                        del sys.modules[k]
                
                import torch
                # Verificar si ahora sí funciona
                try:
                    test_model = torch.nn.Linear(4, 4).cuda()
                    test_x = torch.randn(2, 4).cuda()
                    _ = test_model(test_x)
                    print("✅ PyTorch reinstalado con soporte CUDA 11.8 (sm_60) funcionando.")
                except Exception as e2:
                    print(f"⚠️  Incluso tras reinstalación, CUDA falló: {e2}. Se usará CPU para PyTorch.")
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

import numpy as np
from PIL import Image, ImageDraw, ImageFont

# Verificar ffmpeg de forma portable
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
        print("Por favor, instala FFmpeg y agrégalo a las variables de entorno de Windows.")
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
    "input_video":  "video.mp4",  # Ruta local por defecto
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
    "whisper_model":       "large",  # 'large' es muy preciso pero mas pesado

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

# Verificar GPU real (independiente de PyTorch)
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
        if capability[0] >= 6:  # P100 es 6.0, eso está bien para NVENC
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

# Verificar filtros CUDA en FFmpeg de forma dinámica
def check_ffmpeg_filter(filter_name):
    """Consulta a FFmpeg si un filtro específico está compilado y disponible."""
    try:
        r = subprocess.run(["ffmpeg", "-hide_banner", "-filters"], capture_output=True, text=True)
        return filter_name in r.stdout
    except Exception:
        return False

CUDA_FILTERS_AVAILABLE = check_ffmpeg_filter("scale_cuda") and check_ffmpeg_filter("overlay_cuda")
print(f"   scale_cuda/overlay_cuda en FFmpeg: {'✅' if CUDA_FILTERS_AVAILABLE else '❌ (Se usará CPU scaling + NVENC)'}")

# Configurar encoder y velocidad
if NVENC_H264 or NVENC_HEVC:
    ENC_CODER = "h264_nvenc" if NVENC_H264 else "hevc_nvenc"
    ENC_PRESET = "p2"  # p1=pico rápido, p7=mejor calidad
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
    """
    Desactivamos decodificación por hardware de entrada (hwaccel) para garantizar total 
    compatibilidad al mezclar overlays de CPU (PNGs, Subtítulos ASS) con el flujo de video.
    La codificación final sigue acelerada por hardware usando NVENC.
    """
    return []


def get_encoder_flags():
    """Retorna los flags de codificación adecuados según el encoder activo."""
    if "nvenc" in ENC_CODER:
        return ["-c:v", ENC_CODER, "-preset", ENC_PRESET, "-cq", ENC_CQ,
                "-rc", "vbr", "-b:v", "0", "-maxrate", "10M", "-bufsize", "20M"]
    else:
        return ["-c:v", ENC_CODER, "-preset", ENC_PRESET, "-crf", ENC_CRF]

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

# Deferimos la descarga/asignación de la fuente para evitar cuelgues al importar
FONT_PATH = None
def ensure_font():
    global FONT_PATH
    if FONT_PATH is None or not Path(FONT_PATH).exists():
        FONT_PATH = download_font()
    return FONT_PATH

def get_safe_ffmpeg_path(path_str):
    r"""
    Escapa y formatea las rutas de archivo de forma robusta para ser interpretadas
    por los filtros complexes de FFmpeg en Windows y Linux.
    Ejemplo Windows: C:\Users\... -> C\:/Users/...
    """
    abs_path = os.path.abspath(path_str)
    if platform.system() == "Windows":
        # Convertir todas las barras invertidas a barras normales
        abs_path = abs_path.replace('\\', '/')
        # Escapar el ':' de la unidad de disco con UN solo backslash para FFmpeg: 'C:/...' -> 'C\:/...'
        # Usamos chr(92) para producir literalmente un solo '\' sin ambiguedades de escape de Python
        if len(abs_path) >= 2 and abs_path[1] == ':':
            abs_path = abs_path[0] + chr(92) + ':' + abs_path[2:]
    return abs_path

def run_ffmpeg(cmd, desc="Procesando..."):
    print(f"\n🎬 {desc}")
    global_flags = get_ffmpeg_gpu_flags()
    full = ["ffmpeg", "-y"] + global_flags + cmd
    
    # Asegurar codificación UTF-8 en el entorno de ejecución
    env = os.environ.copy()
    env["LANG"] = "C.UTF-8"
    env["LC_ALL"] = "C.UTF-8"

    r = subprocess.run(full, capture_output=True, text=True, env=env)
    if r.returncode != 0:
        print("\n❌ " + "!"*50)
        print(f"❌ FFmpeg error detectado en: {desc}")
        print("!"*54)
        print(r.stderr)
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
    """Detecta dinámicamente la frecuencia de muestreo y número de canales del audio del video original."""
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

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BLOQUE 5 ▸ PASO 1 — CROP 1:1 (PORTABLE)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def step1_crop_1x1(src, dst=None):
    if dst is None:
        dst = os.path.join(TEMP_DIR, "s1_1x1.mp4")
    w, h, fps, dur = get_video_info(src)
    side = min(w,h)
    x, y = (w-side)//2, (h-side)//2
    
    run_ffmpeg(
        ["-i", src,
         "-vf", f"crop={side}:{side}:{x}:{y}",
         *get_encoder_flags(), "-c:a","copy", dst],
        "Paso 1: Crop 1:1")
    return dst

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BLOQUE 6 ▸ PASO 2 — LIENZO 4:5 (FALLBACK AUTOMÁTICO DE FILTROS CUDA)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def step2_canvas_4x5(src, dst=None):
    if dst is None:
        dst = os.path.join(TEMP_DIR, "s2_4x5.mp4")
    cw, ch = _CW, _CH
    vw, vh = VIDEO_W, VIDEO_H
    vx, vy = VIDEO_X, VIDEO_Y

    # Usamos boxblur para el fondo borroso (sigma o luma_radius = 30)
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
        "Paso 2: Canvas 4:5 (Fondo Blur)")
    return dst

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BLOQUE 7 ▸ PASO 3 — BANDERA ARGENTINA Y TÍTULO (PORTABLE)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def make_arg_flag(w, h):
    img  = Image.new("RGBA", (w, h), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    stripe = h // 3
    CELESTE = (116,172,223,255)
    BLANCO  = (255,255,255,255)
    draw.rectangle([0, 0, w, stripe], fill=CELESTE)
    draw.rectangle([0, stripe, w, stripe*2], fill=BLANCO)
    draw.rectangle([0, stripe*2, w, h], fill=CELESTE)
    
    cx, cy = w//2, h//2
    r_inner = int(h * 0.18)
    r_outer = int(h * 0.38)
    sun_color = (252,191,0,255)
    for i in range(16):
        angle = math.radians(i * 360 / 16)
        draw.line([(cx,cy), (cx+r_outer*math.cos(angle), cy+r_outer*math.sin(angle))], 
                  fill=sun_color, width=max(2,h//30))
    draw.ellipse([cx-r_inner, cy-r_inner, cx+r_inner, cy+r_inner], fill=sun_color)
    return img

def make_bottom_overlay(cfg):
    font_path = ensure_font()
    img  = Image.new("RGBA", (_CW, _CH), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    
    try:
        font = ImageFont.truetype(font_path, cfg["title_font_size"])
    except Exception:
        font = ImageFont.load_default()
        
    text = cfg["title_text"].upper()
    
    # Calcular dimensiones del texto
    bbox = draw.textbbox((0,0), text, font=font, stroke_width=cfg["title_stroke_w"])
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    
    # Padding de la caja blanca redondeada
    pad_x = 40
    pad_y = 20
    box_w = tw + pad_x * 2
    box_h = th + pad_y * 2
    
    # Centrado horizontal y solapando el borde inferior del video
    box_x = (_CW - box_w) // 2
    video_bottom = VIDEO_Y + VIDEO_H
    box_y = video_bottom - box_h // 2
    
    # Dibujar rectángulo blanco redondeado (cajita blanca)
    radius = 18
    draw.rounded_rectangle(
        [box_x, box_y, box_x + box_w, box_y + box_h],
        radius=radius,
        fill=(255, 255, 255, 255)
    )
    
    # Dibujar texto centrado dentro de la cajita blanca
    tx = box_x + pad_x - bbox[0]
    ty = box_y + pad_y - bbox[1]
    
    draw.text(
        (tx, ty), text, font=font,
        fill=(*hex2rgb(cfg["title_color"]), 255),
        stroke_width=cfg["title_stroke_w"],
        stroke_fill=(*hex2rgb(cfg["title_stroke"]), 255)
    )
    return img

def step3_add_title(src, dst=None):
    if dst is None:
        dst = os.path.join(TEMP_DIR, "s3_title.mp4")
    overlay_img = make_bottom_overlay(CONFIG)
    png = os.path.join(TEMP_DIR, "bottom_overlay.png")
    overlay_img.save(png)

    # Pasamos el PNG de overlay como un archivo de entrada de stream (-i), 
    # evitando problemas de rutas en cadenas filter_complex
    run_ffmpeg(
        ["-i", src, "-i", png,
         "-filter_complex", "[0:v][1:v]overlay=0:0[out]",
         "-map", "[out]", "-map", "0:a?",
         *get_encoder_flags(), "-c:a","copy", dst],
        "Paso 3: Título + Bandera")
    return dst

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BLOQUE 8 ▸ PASO 4 — WHISPER + SUBTÍTULOS (ESCAPADO PORTABLE DE RUTAS)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def transcribe_video(path, cfg):
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
            try:
                del model
            except Exception:
                pass
        if torch is not None and torch.cuda.is_available():
            try:
                torch.cuda.empty_cache()
            except Exception:
                pass
        
        model = whisper.load_model(cfg["whisper_model"], device="cpu")
        result = model.transcribe(path, language="es", word_timestamps=True,
                                  verbose=False, fp16=use_fp16,
                                  beam_size=5, temperature=0.0)
    
    segs = [{"start":s["start"],"end":s["end"],"text":s["text"].strip()}
            for s in result["segments"]]
    try:
        del model
    except Exception:
        pass
    if device == "cuda" and torch is not None:
        try:
            torch.cuda.empty_cache()
        except Exception:
            pass
    print(f"   ✅ {len(segs)} segmentos transcritos")
    return segs

def make_ass(segs, cfg, path=None):
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

def step4_add_subtitles(src, dst=None):
    if dst is None:
        dst = os.path.join(TEMP_DIR, "s4_subs.mp4")
        
    cfg = CONFIG
    segs = transcribe_video(src, cfg)
    
    # Asegurar fuente y copiar al directorio de fuentes temporal para libass
    font_src = ensure_font()
    font_name = os.path.basename(font_src)
    font_dst = os.path.join(TEMP_DIR, font_name)
    if font_src != font_dst:
        shutil.copy(font_src, font_dst)
        
    ass = make_ass(segs, cfg)

    # Escapar las rutas absolutas para que sean procesables en Windows
    safe_ass = get_safe_ffmpeg_path(ass)
    safe_fontsdir = get_safe_ffmpeg_path(TEMP_DIR)

    run_ffmpeg(
        ["-i", src,
         "-vf", f"ass='{safe_ass}':fontsdir='{safe_fontsdir}'",
         *get_encoder_flags(), "-c:a","copy", dst],
        "Paso 4: Subtítulos")
    return dst, segs

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BLOQUE 9 ▸ PASO 5 — STICKER FINAL (RESOLVIENDO MISMATCHES DE CONCAT)
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

def step5_add_subscribe(src, dst):
    cfg = CONFIG
    w,h,fps,dur = get_video_info(src)
    dt  = cfg["subscribe_duration"]
    
    png = os.path.join(TEMP_DIR, "subscribe.png")
    make_subscribe_frame(cfg).save(png)

    # 1. Crear sticker de video. Forzamos format=yuv420p para evitar desajustes en el formato de pixel
    sticker = os.path.join(TEMP_DIR, "sticker.mp4")
    run_ffmpeg(["-loop","1","-i",png,"-t",str(dt),
                "-vf",f"scale={w}:{h},format=yuv420p","-r",str(int(fps)),
                *get_encoder_flags(),"-an", sticker],
               "Generando Sticker de Video")

    # 2. Obtener frecuencia y canales de audio del video original
    sample_rate, channels = get_audio_info(src)
    channel_layout = "stereo" if channels >= 2 else "mono"
    print(f"   🔊 Audio del video detectado: {sample_rate}Hz | canales: {channels} ({channel_layout})")

    # 3. Generar audio en silencio que coincida perfectamente
    silence = os.path.join(TEMP_DIR, "silence.aac")
    run_ffmpeg(["-f","lavfi","-i",f"anullsrc=r={sample_rate}:cl={channel_layout}",
                "-t",str(dt),"-c:a","aac","-b:a","192k", silence],
               "Generando Audio Silencio compatible")

    # 4. Unir el sticker de video con el audio en silencio
    sticker_av = os.path.join(TEMP_DIR, "sticker_av.mp4")
    run_ffmpeg(["-i",sticker,"-i",silence,
                "-c:v","copy","-c:a","copy","-shortest", sticker_av],
               "Uniendo Video de Sticker y Audio Silencio")

    # 5. Escribir lista de archivos para concatenación (escapando contrabarras en Windows)
    lst = os.path.join(TEMP_DIR, "concat.txt")
    safe_src_path = os.path.abspath(src).replace('\\', '/')
    safe_sticker_av_path = os.path.abspath(sticker_av).replace('\\', '/')
    
    Path(lst).write_text(
        f"file '{safe_src_path}'\nfile '{safe_sticker_av_path}'\n",
        encoding="utf-8")
    
    # 6. Concatenar usando el demuxer concat
    run_ffmpeg(["-f","concat","-safe","0","-i",lst,"-c","copy", dst],
               "Paso 5: Concatenar Sticker Final")
    return dst

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BLOQUE 10 ▸ PIPELINE DE PROCESAMIENTO
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def run_pipeline(input_video=None, output_video=None):
    try:
        src = input_video or CONFIG["input_video"]
        dst = output_video or CONFIG["output_video"]
        
        # Si el archivo por defecto no existe, intentamos buscar en rutas conocidas como Kaggle o relativas
        if src == "video.mp4" and not Path(src).exists():
            fallbacks = [
                "/kaggle/input/datasets/joelowtok/4333dkjs/videoplayback.mp4",
                "/kaggle/input/datasets/joelowtok/222323/videoplayback.mp4",
                "../video.mp4"
            ]
            for path in fallbacks:
                if Path(path).exists():
                    src = path
                    print(f"🔍 'video.mp4' no encontrado. Usando ruta detectada: {src}")
                    break

        if not Path(src).exists():
            raise FileNotFoundError(f"❌ El archivo de entrada no existe: {src}")

        # Asegurar que la carpeta de salida exista
        Path(dst).parent.mkdir(parents=True, exist_ok=True)

        print("\n" + "═"*60)
        print("  🚀  EL MEJOR HUMOR ARGENTINO  v5 (PORTABLE / OPTIMIZADO)")
        print(f"  📥  Origen:  {src}")
        print(f"  📤  Destino: {dst}")
        print("═"*60)

        s1 = step1_crop_1x1(src)
        s2 = step2_canvas_4x5(s1)
        s3 = step3_add_title(s2)
        s4, segs = step4_add_subtitles(s3)
        final = step5_add_subscribe(s4, dst)

        info = get_video_info(final)
        print("\n" + "═"*60)
        print(f"  ✅  EDICIÓN COMPLETADA EXITOSAMENTE → {final}")
        print(f"  📐  Resolución: {info[0]}×{info[1]} | FPS: {info[2]:.2f}fps | Duración: {info[3]:.1f}s")
        print(f"  🎙   Subtítulos grabados: {len(segs)}")
        print("═"*60)
        return final
    except Exception as e:
        print("\n" + "═"*60)
        print(f"  ❌  ERROR DETECTADO EN EL PIPELINE: {e}")
        print("═"*60)
        return None

if __name__ == "__main__":
    try:
        final = run_pipeline()
        print(f"\n🎉 Resultado guardado en: {final}")
    except Exception as e:
        print(f"\n❌ ERROR EN EL PIPELINE: {e}")
        import traceback
        traceback.print_exc()
