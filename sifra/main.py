# # print("Hello from app")
# # input("Press Enter to exit")
# import os
# import cv2
# import numpy as np
# import pyaudio
# import ollama
# import time
# import subprocess
# import sys
# import threading

# from openwakeword.model import Model
# from faster_whisper import WhisperModel
# from kokoro_onnx import Kokoro

# # --- NEW IMPORTS (TRAY UI) ---
# import pystray
# from pystray import MenuItem as item
# from PIL import Image, ImageDraw, ImageFont
# # import tkinter as tk
# # from tkinter import simpledialog

# # --- ENV FIXES ---
# os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'
# os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'

# # --- STATE MANAGEMENT ---
# class AppState:
#     def __init__(self):
#         self.text_model = "gemma3:1b"
#         self.vision_model = "gemma4:e2b"
#         self.system_prompt = ""
#         self.response_mode = "short"

# STATE = AppState()

# # --- PATH SETUP ---
# if getattr(sys, 'frozen', False):
#     BASE_DIR = os.path.dirname(sys.executable)
# else:
#     BASE_DIR = os.path.dirname(__file__)

# def resource_path(filename):
#     if getattr(sys, 'frozen', False):
#         base_path = os.path.abspath(os.path.join(os.path.dirname(sys.executable), "../Resources"))
#     else:
#         base_path = os.path.dirname(__file__)
#     return os.path.join(base_path, filename)

# # --- CONFIG ---
# WAKE_WORD_PATH = resource_path("sifra.onnx")
# SENSITIVITY = 0.55
# CHUNK = 1280

# VISION_TRIGGERS = [
#     "what is this", "what do you see", "can you see",
#     "what am i holding", "what is in my hand",
#     "what's here", "see", "look", "describe", "identify"
# ]

# # --- TRAY FUNCTIONS ---
# # def create_icon():
# #     img = Image.new('RGB', (64, 64), color=(30, 30, 30))
# #     d = ImageDraw.Draw(img)
# #     d.text((18, 18), "S", fill=(255, 255, 255))
# #     return img


# def create_icon():
#     img = Image.new('RGB', (64, 64), color=(20, 20, 20))
#     draw = ImageDraw.Draw(img)

#     # Draw circle
#     draw.ellipse((8, 8, 56, 56), fill=(0, 150, 255))

#     # Draw text
#     draw.text((22, 18), "S", fill="white")

#     return img

# def set_model(model_name):
#     def inner(icon, item):
#         STATE.text_model = model_name
#         STATE.vision_model = "gemma4:e2b"
#         print(f"🔁 Model switched to: {model_name}")
#     return inner

# def set_response_mode(mode):
#     def inner(icon, item):
#         STATE.response_mode = mode
#         print(f"📝 Mode: {mode}")
#     return inner

# def set_prompt_short(icon, item):
#     STATE.system_prompt = "Answer in one short natural sentence."

# def set_prompt_detailed(icon, item):
#     STATE.system_prompt = "Explain clearly with details."

# # def custom_prompt(icon, item):
# #     root = tk.Tk()
# #     root.withdraw()
# #     prompt = simpledialog.askstring("System Prompt", "Enter new system prompt:")
# #     if prompt:
# #         STATE.system_prompt = prompt
# #         print("✏️ Custom prompt updated")

# def quit_app(icon, item):
#     print("👋 Exiting Sifra...")
#     icon.stop()
#     os._exit(0)

# menu = pystray.Menu(
#     item("Model",
#         pystray.Menu(
#             item("Gemma", set_model("gemma4:e2b")),
#             item("Qwen", set_model("qwen2.5:1.5b")),
#         )
#     ),
#     item("Response Mode",
#         pystray.Menu(
#             item("Short", set_response_mode("short")),
#             item("Long", set_response_mode("long")),
#         )
#     ),
#     # item("System Prompt",
#     #     pystray.Menu(
#     #         item("Short Prompt", set_prompt_short),
#     #         item("Detailed Prompt", set_prompt_detailed),
#     #         item("Custom Prompt", custom_prompt),
#     #     )
#     # ),
#     item("System Prompt",
#     pystray.Menu(
#         item("Short Prompt", set_prompt_short),
#         item("Detailed Prompt", set_prompt_detailed),
#     )
# ),
#     item("Exit", quit_app)
# )

# def run_tray():
#     icon = pystray.Icon("Sifra", create_icon(), menu=menu)
#     icon.run()

# # --- UTIL FUNCTIONS ---
# def play_ting():
#     subprocess.Popen(["afplay", "/System/Library/Sounds/Tink.aiff"])

# def capture_image():
#     cap = cv2.VideoCapture(0)
#     if not cap.isOpened():
#         print("❌ Camera failed")
#         return None

#     for _ in range(10):
#         cap.read()

#     ret, frame = cap.read()
#     if not ret:
#         return None

#     img_path = os.path.join(BASE_DIR, "view.jpg")
#     cv2.imwrite(img_path, frame)
#     cap.release()

#     return img_path

# def speak_stable(text, kokoro):
#     print(f"🤖 Sifra: {text}")
#     try:
#         samples, sr = kokoro.create(
#             text, voice="af_bella", speed=0.95, lang="en-us"
#         )
#         import sounddevice as sd
#         padding = np.zeros(int(sr * 0.3), dtype=np.float32)
#         sd.play(np.concatenate([samples, padding]), sr)
#         sd.wait()
#     except Exception as e:
#         print("🔊 TTS error:", e)

# def is_speech(chunk, threshold=0.008):
#     rms = np.sqrt(np.mean(chunk**2))
#     return rms > threshold

# def record_until_silence(mic, timeout=10, silence_limit=1.5):
#     start_time = time.time()

#     while time.time() - start_time < timeout:
#         chunk = np.frombuffer(
#             mic.read(CHUNK, exception_on_overflow=False),
#             dtype=np.int16
#         ).astype(np.float32) / 32768.0

#         if is_speech(chunk):
#             break
#     else:
#         return None

#     frames = []
#     silence_start = None

#     while True:
#         chunk = np.frombuffer(
#             mic.read(CHUNK, exception_on_overflow=False),
#             dtype=np.int16
#         ).astype(np.float32) / 32768.0

#         frames.append(chunk)

#         if is_speech(chunk):
#             silence_start = None
#         else:
#             if silence_start is None:
#                 silence_start = time.time()
#             elif time.time() - silence_start > silence_limit:
#                 break

#     return np.concatenate(frames)

# def get_system_prompt():
#     if STATE.system_prompt:
#         return STATE.system_prompt
#     return "Answer in one short sentence." if STATE.response_mode == "short" \
#         else "Explain clearly in detail within 120 words."

# # --- MAIN ---
# def main():
#     print("🚀 Sifra Initializing...")

#     # START TRAY THREAD
#     threading.Thread(target=run_tray, daemon=True).start()

#     stt = WhisperModel("tiny.en", device="cpu", compute_type="int8")

#     kokoro = Kokoro(
#         resource_path("kokoro-v1.0.onnx"),
#         resource_path("voices-v1.0.bin")
#     )

#     oww_model = Model(
#         wakeword_models=[WAKE_WORD_PATH],
#         inference_framework="onnx"
#     )

#     audio = pyaudio.PyAudio()
#     mic = audio.open(
#         format=pyaudio.paInt16,
#         channels=1,
#         rate=16000,
#         input=True,
#         frames_per_buffer=CHUNK
#     )

#     print("✅ Ready")

#     active_until = 0

#     while True:
#         try:
#             data = np.frombuffer(
#                 mic.read(CHUNK, exception_on_overflow=False),
#                 dtype=np.int16
#             )

#             score = list(oww_model.predict(data).values())[0]
#             now = time.time()

#             if score > SENSITIVITY and now > active_until:
#                 play_ting()
#                 active_until = time.time() + 8

#             if now < active_until:
#                 audio_np = record_until_silence(mic)

#                 if audio_np is None:
#                     active_until = 0
#                     continue

#                 segments, _ = stt.transcribe(audio_np)
#                 user_input = " ".join([s.text for s in segments]).strip().lower()

#                 if not user_input:
#                     continue

#                 print("👤:", user_input)

#                 img_path = []
#                 if any(v in user_input for v in VISION_TRIGGERS):
#                     img = capture_image()
#                     if img:
#                         img_path = [img]

#                 response = ollama.generate(
#                     model=STATE.text_model,
#                     prompt=user_input,
#                     images=img_path if img_path else None,
#                     system=get_system_prompt(),
#                     options={"temperature": 0.3}
#                 )

#                 ai_text = response.get("response", "").strip()
#                 speak_stable(ai_text, kokoro)

#                 active_until = time.time() + 8

#         except KeyboardInterrupt:
#             break
#         except Exception as e:
#             print("🔥 Error:", e)
#             time.sleep(1)

# # --- ENTRY ---
# # if __name__ == "__main__":
# #     import multiprocessing
# #     multiprocessing.freeze_support()
# #     main()
# if __name__ == "__main__":
#     import multiprocessing
#     multiprocessing.freeze_support()
    
#     # 1. Start the heavy logic in the background
#     threading.Thread(target=main, daemon=True).start()
    
#     # 2. Run the tray icon on the MAIN thread (required for macOS)
#     icon = pystray.Icon("Sifra", create_icon(), menu=menu)
#     icon.run()

# import os
# import cv2
# import numpy as np
# import pyaudio
# import ollama
# import time
# import gc
# import subprocess # Ensure this is imported
# import sounddevice as sd

# from openwakeword.model import Model
# from faster_whisper import WhisperModel
# import re
# # --- MAC SYSTEM OPTIMIZATIONS ---
# os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'
# os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'

# # --- CONFIGURATION ---
# import sys
# import os

# import multiprocessing
# multiprocessing.freeze_support()

# if getattr(sys, 'frozen', False):
#     BASE_DIR = os.path.dirname(sys.executable)
# else:
#     BASE_DIR = os.path.dirname(__file__)

# VLM_PATH = BASE_DIR
# if getattr(sys, 'frozen', False):
#     base_path = os.path.join(os.path.dirname(sys.executable), "../Resources")

#     # Fix language_tags
#     os.environ["LANGUAGE_TAGS_DATA_PATH"] = os.path.join(
#         base_path, "language_tags", "data"
#     )

#     # ✅ Fix espeak-ng
#     os.environ["ESPEAKNG_DATA_PATH"] = os.path.join(
#         base_path, "espeakng_loader", "espeak-ng-data"
#     )

#     os.environ["PHONEMIZER_ESPEAK_LIBRARY"] = os.path.join(
#         base_path, "espeakng_loader", "libespeak-ng.dylib"
#     )


# def resource_path(filename):
#     if getattr(sys, 'frozen', False):
#         # Inside .app bundle
#         base_path = os.path.abspath(os.path.join(os.path.dirname(sys.executable), "../Resources"))
#     else:
#         # Normal Python run
#         base_path = os.path.dirname(__file__)

#     return os.path.join(base_path, filename)
# # WAKE_WORD_PATH = os.path.join(VLM_PATH, "sifra.onnx")

# WAKE_WORD_PATH = resource_path("sifra.onnx")
# SENSITIVITY = 0.55 # Slightly increased to prevent false triggers
# CHUNK = 1280
# TEXT_MODEL = "gemma3:1b"     # or mistral, phi, etc.
# VISION_MODEL = "moondream:latest"   # keep this for image tasks
# VISION_TRIGGERS = ["what is this", "what do you see","can you see", "what am I holding", "what is in my hand", "Can you see whats here", "what's here", "see", "look", "describe", "identify","What is in this image","what's in this image"]

# print("🚀 Sifra: Restoring Stable ONNX Voice Engine...")
# from kokoro_onnx import Kokoro
# try:
#     stt = WhisperModel("tiny.en", device="cpu", compute_type="int8")
#     # kokoro = Kokoro("kokoro-v1.0.onnx", "voices-v1.0.bin")
#     kokoro = Kokoro(
#     resource_path("kokoro-v1.0.onnx"),
#     resource_path("voices-v1.0.bin")
# )

#     oww_model = Model(wakeword_models=[WAKE_WORD_PATH], inference_framework="onnx")
#     print("✅ All Engines Loaded Successfully.")
# except Exception as e:
#     print(f"❌ Init Error: {e}")
#     sys.exit(1)

# audio = pyaudio.PyAudio()
# mic = audio.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=CHUNK)

# def play_ting():
#     """Plays a built-in macOS system sound to indicate listening."""
#     # 'Tink' is the classic subtle Apple 'ting' sound
#     subprocess.Popen(["afplay", "/System/Library/Sounds/Tink.aiff"])

# def capture_image():
#     cap = cv2.VideoCapture(0)
#     for _ in range(10): cap.read() 
#     ret, frame = cap.read()
#     if ret:
#         cv2.imwrite("view.jpg", frame)
#     cap.release()
#     return "view.jpg"

# def speak_stable(text):
#     print(f"🤖 Sifra: {text}")
#     try:
#         samples, sample_rate = kokoro.create(text, voice="af_bella", speed=0.95, lang="en-us")
#         padding = np.zeros(int(sample_rate * 0.3), dtype=np.float32)
#         smooth_samples = np.concatenate([samples, padding])
#         sd.play(smooth_samples, sample_rate)
#         sd.wait() 
#         time.sleep(0.3)
#     except Exception as e:
#         print(f"🔊 Audio Playback Error: {e}")

# def is_speech(audio_chunk, threshold=0.008):
#     rms = np.sqrt(np.mean(audio_chunk**2))
#     return rms > threshold

# def record_until_silence(timeout=8, silence_limit=1.5):
#     """Wait for speech, then record until silence"""
#     print("🎙️ Waiting for speech...")

#     start_time = time.time()

#     # Wait for speech start
#     while time.time() - start_time < timeout:
#         chunk = np.frombuffer(mic.read(CHUNK, exception_on_overflow=False), dtype=np.int16).astype(np.float32) / 32768.0
#         if is_speech(chunk):
#             print("🗣️ Speech started")
#             break
#     else:
#         return None  # timeout, no speech

#     frames = []
#     silence_start = None

#     while True:
#         chunk = np.frombuffer(mic.read(CHUNK, exception_on_overflow=False), dtype=np.int16).astype(np.float32) / 32768.0
#         frames.append(chunk)

#         if is_speech(chunk):
#             silence_start = None
#         else:
#             if silence_start is None:
#                 silence_start = time.time()
#             elif time.time() - silence_start > silence_limit:
#                 print("🤫 Speech ended")
#                 break

#     return np.concatenate(frames)
# # def main():
# #     print(f"\n✨ Sifra is active. Sensitivity: {SENSITIVITY}")

# #     active_until = 0  # timer for 10 sec window

# #     while True:
# #         try:
# #             data = np.frombuffer(mic.read(CHUNK, exception_on_overflow=False), dtype=np.int16)
# #             prediction = oww_model.predict(data)
# #             score = list(prediction.values())[0]

# #             current_time = time.time()

# #             # 🔹 Wake word triggers only if not already active
# #             if score > SENSITIVITY and current_time > active_until:
# #                 play_ting()
# #                 time.sleep(0.6)
# #                 print("\n✨ Yes?")
# #                 active_until = time.time() + 8  # 10 sec window

# #             # 🔹 If within active window → listen for command
# #             if current_time < active_until:
# #                 audio_np = record_until_silence(timeout=8)

# #                 if audio_np is None:
# #                     print("⌛ Timeout: No speech detected")
# #                     active_until = 0
# #                     silence_chunk = np.zeros(1280, dtype="int16")
# #                     for _ in range(20):
# #                         oww_model.predict(silence_chunk)
# #                     continue

# #                 segments, _ = stt.transcribe(audio_np)
# #                 user_input = " ".join([s.text for s in segments]).strip().lower()

# #                 if not user_input:
# #                     continue

# #                 print(f"👤 You: {user_input}")

# #                 img_path = [capture_image()] if any(v in user_input for v in VISION_TRIGGERS) else []

# #                 # response = ollama.generate(
# #                 #     model=UNIFIED_MODEL,
# #                 #     prompt=user_input,
# #                 #     images=img_path,
# #                 #     system="You are Sifra. You are a concise assistant. Answer in 1 natural sentence. Do not use markdown, emojis, or lists. Respond naturally and in a few words.",
# #                 #     options={"num_predict": 40, "temperature": 0.3}
# #                 # )
# #                 if img_path:
# #                     # 👁️ Vision model (Gemma)
# #                     response = ollama.generate(
# #                         model=VISION_MODEL,
# #                         prompt=user_input,
# #                         images=img_path,
# #                         # system="You are Sifra.Do not cut the response in between. Provide a concise response. Answer in one short natural sentence. ",
# #                         system="You are Sifra. Speak naturally and concisely. Finish your thought in exactly one sentence.",
# #                         options={"num_predict": 80, "temperature": 0.2,"stop": ["."]}
# #                     )
# #                 else:
# #                     # 🧠 Text-only model
# #                     response = ollama.generate(
# #                         model=TEXT_MODEL,
# #                         prompt=user_input,
# #                         system = "You are Sifra. Answer in one short natural sentence. ",
# #                         options={"num_predict": 40, "temperature": 0.3}
# #                     )
# #                 ai_text = response['response'].strip()
# #                 speak_stable(ai_text)

# #                 # 🔁 Restart 10 sec window after response
# #                 active_until = time.time() + 8

# #         except KeyboardInterrupt:
# #             break
# #         except Exception as e:
# #             print("Error:", e)
# #             continue


# def main():
#     print(f"\n✨ Sifra is active. Sensitivity: {SENSITIVITY}")

#     active_until = 0
#     error_count = 0
#     MAX_ERRORS = 5

#     while True:
#         try:
#             # 🔹 Read audio safely
#             try:
#                 data = np.frombuffer(
#                     mic.read(CHUNK, exception_on_overflow=False),
#                     dtype=np.int16
#                 )
#             except Exception as e:
#                 print("🎤 Mic read error:", e)
#                 time.sleep(1)
#                 continue

#             # 🔹 Wake word detection
#             prediction = oww_model.predict(data)
#             score = list(prediction.values())[0]
#             current_time = time.time()

#             # 🔹 Wake trigger
#             if score > SENSITIVITY and current_time > active_until:
#                 play_ting()
#                 time.sleep(0.6)
#                 print("\n✨ Yes?")
#                 active_until = time.time() + 8

#             # 🔹 Active listening window
#             if current_time < active_until:
#                 audio_np = record_until_silence(timeout=8)

#                 if audio_np is None:
#                     print("⌛ Timeout: No speech detected")
#                     active_until = 0

#                     # reset wake model buffer
#                     silence_chunk = np.zeros(1280, dtype="int16")
#                     for _ in range(10):
#                         oww_model.predict(silence_chunk)

#                     continue

#                 # 🔹 STT
#                 try:
#                     segments, _ = stt.transcribe(audio_np)
#                     user_input = " ".join([s.text for s in segments]).strip().lower()
#                 except Exception as e:
#                     print("🧠 STT error:", e)
#                     continue

#                 if not user_input:
#                     continue

#                 print(f"👤 You: {user_input}")

#                 # 🔹 Vision trigger
#                 img_path = []
#                 if any(v in user_input for v in VISION_TRIGGERS):
#                     try:
#                         img_path = [capture_image()]
#                     except Exception as e:
#                         print("📷 Camera error:", e)

#                 # 🔹 LLM response
#                 try:
#                     if img_path:
#                         response = ollama.generate(
#                             model=VISION_MODEL,
#                             prompt=user_input,
#                             images=img_path,
#                             system="You are Sifra. Speak naturally and concisely in exactly one sentence.",
#                             options={"num_predict": 80, "temperature": 0.2,"stop": ["."]}
#                         )
#                     else:
#                         response = ollama.generate(
#                             model=TEXT_MODEL,
#                             prompt=user_input,
#                             system="You are Sifra. Answer in one short natural sentence.",
#                             options={"num_predict": 40, "temperature": 0.3}
#                         )

#                     ai_text = response.get('response', '').strip()

#                 except Exception as e:
#                     print("🤖 LLM error:", e)
#                     continue

#                 # 🔹 TTS
#                 try:
#                     speak_stable(ai_text)
#                 except Exception as e:
#                     print("🔊 TTS error:", e)

#                 # 🔁 reset window
#                 active_until = time.time() + 8
#                 error_count = 0  # reset after success

#         except KeyboardInterrupt:
#             print("\n👋 Exiting Sifra...")
#             break

#         except Exception as e:
#             print("🔥 Critical Error:", e)
#             error_count += 1

#             if error_count >= MAX_ERRORS:
#                 print("❌ Too many errors. Shutting down.")
#                 break

#             time.sleep(1)  # prevent rapid loop

# if __name__ == "__main__":
#     import multiprocessing
#     multiprocessing.freeze_support()

#     try:
#         main()
#     except Exception as e:
#         import traceback
#         print("🔥 Fatal error:", e)
#         traceback.print_exc()
#         input("Press Enter to exit...")

import os
import cv2
import numpy as np
import pyaudio
import ollama
import time
import subprocess
import sys
import threading
import pystray
from pystray import MenuItem as item
from PIL import Image, ImageDraw

from openwakeword.model import Model
from faster_whisper import WhisperModel
from kokoro_onnx import Kokoro

# --- ENV FIXES ---
os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'
os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'

# --- PATH SETUP ---
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(__file__)

def resource_path(filename):
    if getattr(sys, 'frozen', False):
        base_path = os.path.abspath(os.path.join(os.path.dirname(sys.executable), "../Resources"))
    else:
        base_path = os.path.dirname(__file__)
    return os.path.join(base_path, filename)

# --- CONFIG ---
WAKE_WORD_PATH = resource_path("sifra.onnx")
SENSITIVITY = 0.55
CHUNK = 1280

TEXT_MODEL = "gemma3:1b"
VISION_MODEL = "moondream:latest"
RUNNING = True
VISION_TRIGGERS = [
    "what is this", "what do you see", "can you see",
    "what am i holding", "what is in my hand",
    "what's here", "see", "look", "describe", "identify"
]
class AppState:
    def __init__(self):
        self.text_model = TEXT_MODEL
        self.vision_model = VISION_MODEL
        self.response_mode = "short"  # short / long

STATE = AppState()
# --- UTIL FUNCTIONS ---

def play_ting():
    subprocess.Popen(["afplay", "/System/Library/Sounds/Tink.aiff"])

# def capture_image():
#     cap = cv2.VideoCapture(0)
#     for _ in range(10):
#         cap.read()
#     ret, frame = cap.read()
#     if ret:
#         cv2.imwrite("view.jpg", frame)
#     cap.release()
#     return "view.jpg"
def capture_image():
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("❌ Camera failed to open")
        return None

    for _ in range(10):
        cap.read()

    ret, frame = cap.read()

    if not ret:
        print("❌ Failed to capture image")
        return None

    img_path = os.path.join(BASE_DIR, "view.jpg")
    cv2.imwrite(img_path, frame)

    cap.release()

    print(f"📷 Image saved at: {img_path}")
    return img_path

def speak_stable(text, kokoro):
    print(f"🤖 Sifra: {text}")
    try:
        samples, sample_rate = kokoro.create(
            text, voice="af_bella", speed=0.95, lang="en-us"
        )
        import sounddevice as sd
        padding = np.zeros(int(sample_rate * 0.3), dtype=np.float32)
        smooth_samples = np.concatenate([samples, padding])
        sd.play(smooth_samples, sample_rate)
        sd.wait()
    except Exception as e:
        print("🔊 TTS error:", e)

def is_speech(audio_chunk, threshold=0.03):
    rms = np.sqrt(np.mean(audio_chunk**2))
    return rms > threshold

def record_until_silence(mic, timeout=10, silence_limit=1.5):
    print("🎙️ Waiting for speech...")
    start_time = time.time()

    while time.time() - start_time < timeout:
        chunk = np.frombuffer(
            mic.read(CHUNK, exception_on_overflow=False),
            dtype=np.int16
        ).astype(np.float32) / 32768.0

        if is_speech(chunk):
            print("🗣️ Speech started")
            break
    else:
        return None

    frames = []
    silence_start = None

    while True:
        chunk = np.frombuffer(
            mic.read(CHUNK, exception_on_overflow=False),
            dtype=np.int16
        ).astype(np.float32) / 32768.0

        frames.append(chunk)

        if is_speech(chunk):
            silence_start = None
        else:
            if silence_start is None:
                silence_start = time.time()
            elif time.time() - silence_start > silence_limit:
                print("🤫 Speech ended")
                break

    return np.concatenate(frames)

# def create_icon():
#     return Image.new("RGB", (64, 64), (50, 50, 50))
def create_icon():
    size = 64

    # Create black background
    img = Image.new("RGB", (size, size), (0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Circle properties
    margin = 12  # space from edges
    bbox = [margin, margin, size - margin, size - margin]

    # Light blue color (adjust if needed)
    circle_color = (100, 180, 255)

    # Draw circle
    draw.ellipse(bbox, fill=circle_color)

    return img
# --- MODEL SWITCHING ---
def set_text_model(name):
    def inner(icon, item):
        STATE.text_model = name
        print(f"🔤 Text model: {name}")
    return inner

def set_vision_model(name):
    def inner(icon, item):
        STATE.vision_model = name
        print(f"👁️ Vision model: {name}")
    return inner

# --- RESPONSE MODE ---
def set_response_mode(mode):
    def inner(icon, item):
        STATE.response_mode = mode
        print(f"📝 Mode: {mode}")
    return inner

# --- EXIT ---
def quit_app(icon, item):
    global RUNNING
    print("👋 Exiting...")
    RUNNING = False  
    icon.stop()
    os._exit(0)

# --- MENU ---
menu = pystray.Menu(
    item("Text Model",
        pystray.Menu(
            item("Gemma3", set_text_model("gemma3:1b")),
            item("Gemma4", set_text_model("gemma4:e2b")),
            item("Qwen", set_text_model("qwen2.5:1.5b")), 
        )
    ),
    item("Vision Model",
        pystray.Menu(
            item("Gemma4", set_vision_model("gemma4:e2b")),
            item("Moondream(faster)", set_vision_model("moondream:latest")),
            item("Gemma3", set_vision_model("gemma3:4b"))
        )
    ),
    item("Response",
        pystray.Menu(
            item("Short", set_response_mode("short")),
            item("Long", set_response_mode("long")),
        )
    ),
    item("Exit", quit_app)
)

# def run_tray():
#     icon = pystray.Icon("Sifra", create_icon(), menu=menu)
#     icon.run()
def run_tray():
    icon = pystray.Icon(
        "Sifra",
        create_icon(),
        menu=menu
    )
    icon.run()
# --- MAIN APP ---

def main():
    
    print("🚀 Sifra: Initializing...")

    # 🔹 INIT ALL HEAVY OBJECTS HERE
    stt = WhisperModel("tiny.en", device="cpu", compute_type="int8")

    kokoro = Kokoro(
        resource_path("kokoro-v1.0.onnx"),
        resource_path("voices-v1.0.bin")
    )

    oww_model = Model(
        wakeword_models=[WAKE_WORD_PATH],
        inference_framework="onnx"
    )

    audio = pyaudio.PyAudio()
    mic = audio.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=16000,
        input=True,
        frames_per_buffer=CHUNK
    )

    print("✅ All Engines Loaded Successfully.")
    print(f"✨ Sifra is active. Sensitivity: {SENSITIVITY}")

    active_until = 0

    while RUNNING:
        try:
            data = np.frombuffer(
                mic.read(CHUNK, exception_on_overflow=False),
                dtype=np.int16
            )

            prediction = oww_model.predict(data)
            score = list(prediction.values())[0]
            current_time = time.time()

            if score > SENSITIVITY and current_time > active_until:
                play_ting()
                time.sleep(0.5)
                print("✨ Yes?")
                active_until = time.time() + 8

            if current_time < active_until:
                audio_np = record_until_silence(mic)

                if audio_np is None:
                    active_until = 0
                    continue

                segments, _ = stt.transcribe(audio_np)
                user_input = " ".join([s.text for s in segments]).strip().lower()

                if not user_input:
                    continue

                print("👤 You:", user_input)

                img_path = []
                if any(v in user_input for v in VISION_TRIGGERS):
                    img = capture_image()
                    if img:
                        img_path = [img]

                if img_path:
                    response = ollama.generate(
                        STATE.vision_model,
                        prompt=user_input,
                        images=img_path,
                        system="You are Sifra. A helpful and concise assistant. Answer in one natural sentence. Do not use special characters.",
                        options={"temperature": 0.2}
                    )
                else:
                    response = ollama.generate(
                        model=STATE.text_model,
                        prompt=user_input,
                        # system="Answer in one short natural sentence.",
                        system = "You are Sifra. A helpful and concise assistant. Answer in one short sentence." if STATE.response_mode == "short" \
                            else "You are Sifra. A helpful assistant.Explain clearly in detail. Answer within 80 words",
                        options={"temperature": 0.3}
                    )

                ai_text = response.get("response", "").strip()
                speak_stable(ai_text, kokoro)

                active_until = time.time() + 8

        except KeyboardInterrupt:
            break
        except Exception as e:
            print("🔥 Error:", e)
            time.sleep(1)

# --- ENTRY POINT (CRITICAL) ---

import threading

if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()

    # Run assistant in background
    threading.Thread(target=main, daemon=True).start()

    # Run tray in MAIN thread (MANDATORY)
    run_tray()