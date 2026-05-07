 
from flask import Flask, render_template, jsonify, request, send_from_directory
import requests
import json
import markdown
import PyPDF2
import os
import wave
import threading
import time
from faster_whisper import WhisperModel
from docx import Document
import sounddevice as sd
import soundfile as sf
from faster_whisper.audio import decode_audio
sd.default.samplerate = 44100
print(sd.query_devices())
# ---------- Config ----------
app = Flask(__name__, static_folder="static", template_folder="templates")
DATA_FILE = "data2.txt"
UPLOAD_FOLDER = "uploads"
RECORD_PATH = "recorded.webm"  
chat_history = []
WAKE_WORDS = ["jaya", "zoya", "lily", "ravi","sifra"]
SELECTED_OLLAMA_MODEL = "gemma3:1b"
SELECTED_WAKE_WORD = "zoya"
# ---------- Globals ----------
whisper_model = None
AVAILABLE_VOICES = [
    "af_heart",
    "af_bella",
    "am_adam"
]

_TTS_THREAD = None
_TTS_STOP_FLAG = threading.Event()
_TTS_LOCK = threading.Lock()
_TTS_ENGINE = None


from silero_vad import SileroVAD

vad = SileroVAD("silero_vad.onnx")
from kokoro import KPipeline

pipeline = KPipeline(lang_code="b")
CURRENT_VOICE = "af_heart"
# --- Piper TTS config ---
_TTS_VOICE = None


# --- helper to choose a safe output device ---
def get_output_device():
    try:
        sd._terminate()
        sd._initialize()
    except:
        pass
    devices = sd.query_devices()

    # 1️⃣ Prefer Bluetooth / wired earphones (output-capable)
    for i, dev in enumerate(devices):
        name = dev['name'].lower()
        if (
            ("airdopes" in name or "airpods" in name or "headphone" in name)
            and dev['max_output_channels'] > 0
        ):
            return i

    # 2️⃣ Fallback to Mac speakers
    for i, dev in enumerate(devices):
        if "macbook air speakers" in dev['name'].lower():
            return i

    # 3️⃣ Absolute fallback: first output-capable device
    for i, dev in enumerate(devices):
        if dev['max_output_channels'] > 0:
            return i

    return None

import io
import wave
import sounddevice as sd
import soundfile as sf
import io
import numpy as np
import sounddevice as sd
import time

def _tts_worker(text: str, voice_name: str):
    try:
        audio_gen = pipeline(text, voice=voice_name)

        audio_chunks = []
        samplerate = 22050  # default, will override if available

        for result in audio_gen:
            audio = result.audio

            # ✅ Tensor → NumPy
            if hasattr(audio, "cpu"):
                audio = audio.cpu().numpy()

            audio_chunks.append(audio)

            # get samplerate if provided
            if hasattr(result, "sample_rate"):
                samplerate = result.sample_rate

        if not audio_chunks:
            return

        audio_data = np.concatenate(audio_chunks)

        if _TTS_STOP_FLAG.is_set():
            return

        # ✅ play
        sd.play(audio_data, samplerate)

        while sd.get_stream().active:
            if _TTS_STOP_FLAG.is_set():
                sd.stop()
                break
            time.sleep(0.05)

    except Exception as e:
        print(f"[Kokoro TTS] Error: {e}")
def start_tts(text: str, voice_name: str):
    """Stop previous TTS and start a new one (thread-safe)."""
    global _TTS_THREAD
    with _TTS_LOCK:
        # Stop previous generation (this sets flag and stops sd playback)
        stop_tts()
        # Clear stop flag and start thread
        _TTS_STOP_FLAG.clear()
        _TTS_THREAD = threading.Thread(
    target=_tts_worker,
    args=(text, voice_name),
    daemon=True
)
        _TTS_THREAD.start()


def stop_tts():
    """Stop audio + signal worker to stop. Wait a short time for worker to finish."""
    global _TTS_THREAD
    _TTS_STOP_FLAG.set()
    try:
        sd.stop()
        sd.wait()
    except Exception:
        pass

    # Give the worker a moment to exit cleanly and join if it's running
    if _TTS_THREAD is not None and _TTS_THREAD.is_alive():
        _TTS_THREAD.join(timeout=0.5)
    _TTS_THREAD = None


@app.route("/")
def index():
    global whisper_model
    if whisper_model is None:
        try:
            # Use int8 for speed; adjust if you prefer a different size
            whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
            print("✅ Whisper model loaded.")
        except Exception as e:
            print(f"Error loading model: {e}")
            return "Error loading model. Check your setup.", 500
    return render_template("index.html")

SYSTEM_PROMPT = "You are a concise and helpful assistant. Limit your entire response to a maximum of 2 complete sentences or 40 words. If the given lines do not contain the answer use your own knowledge base to provide the answer."
@app.route("/get_prompt", methods=["GET"])
def get_prompt():
    return jsonify({"prompt": SYSTEM_PROMPT})
@app.route("/set_prompt", methods=["POST"])
def set_prompt():
    global SYSTEM_PROMPT
    data = request.json
    SYSTEM_PROMPT = data.get("prompt", SYSTEM_PROMPT)
    return jsonify({"status": "updated"})
@app.route("/uploads/<path:filename>")
def serve_upload(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/remember', methods=['POST'])
def remember():
    data = request.json.get('text', '').strip() if request.is_json else ''
    if not data:
        return jsonify({"error": "No text provided"}), 400
    try:
        with open(DATA_FILE, 'a', encoding='utf-8') as f:
            f.write(data + '\n')
        return jsonify({"message": "Text saved successfully!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/upload_document', methods=['POST'])
def upload_document():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    ext = file.filename.lower().split('.')[-1]
    if ext not in ['pdf', 'docx']:
        return jsonify({"error": "File type not supported"}), 400

    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    filename = file.filename
    save_path = os.path.join(UPLOAD_FOLDER, filename)

    try:
        file.save(save_path)
        if ext == 'pdf':
            read_pdf(save_path)
        elif ext == 'docx':
            read_docx(save_path)
        return jsonify({"message": "File uploaded and content saved!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/list_documents", methods=['GET'])
def list_documents():
    try:
        files = os.listdir(UPLOAD_FOLDER) if os.path.exists(UPLOAD_FOLDER) else []
        files = [f for f in files if f.lower().endswith(('.pdf', '.docx'))]
        return jsonify({"files": files})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/delete_document", methods=["POST"])
def delete_document():
    data = request.get_json()
    filename = data.get("filename")
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(filepath):
        os.remove(filepath)
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                skip = False
                for line in lines:
                    if line.strip() == f"###FILE:{filename}###":
                        skip = True
                        continue
                    if skip and line.startswith("###FILE:"):
                        skip = False
                    if not skip:
                        f.write(line)
            return jsonify({"message": f"{filename} deleted successfully (file + data)."})
        except Exception as e:
            return jsonify({"error": f"File deleted but failed to remove text: {str(e)}"}), 500
    else:
        return jsonify({"error": "File not found."}), 404
    
@app.route("/set_ollama_model", methods=["POST"])
def set_ollama_model():
    """
    Sets the global Ollama model to be used by the voice assistant
    (e.g., in the check_wake_word endpoint).
    """
    global SELECTED_OLLAMA_MODEL
    data = request.json
    chosen = data.get("model_name") 

    if not chosen:
        return jsonify({"error": "No model name provided"}), 400

    SELECTED_OLLAMA_MODEL = chosen
    print(f"✅ Ollama Model set to: {SELECTED_OLLAMA_MODEL}")
    return jsonify({"status": "ok", "selected_model": SELECTED_OLLAMA_MODEL})
import base64
@app.route("/set_wake_word", methods=["POST"])
def set_wake_word():
    global SELECTED_WAKE_WORD
    data = request.json
    chosen = data.get("wake_word")

    if chosen not in WAKE_WORDS:
        return jsonify({"error": "Invalid wake word"}), 400

    SELECTED_WAKE_WORD = chosen.lower()
    return jsonify({"status": "ok", "selected": SELECTED_WAKE_WORD})

@app.route("/get_wake_words", methods=["GET"])
def get_wake_words():
    return jsonify({
        "available": WAKE_WORDS,
        "selected": SELECTED_WAKE_WORD
    })
@app.route("/check_wake_word", methods=["POST"])
def check_wake_word():
    
    if 'audio_file' not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    audio_file = request.files['audio_file']
    audio_file.save(RECORD_PATH)
    if os.path.getsize(RECORD_PATH) < 1000: 
        return jsonify({
            "transcription": "",
            "response": "",
            "response_delay": 0,
            "wake_word_detected": False
        })
    audio = decode_audio(RECORD_PATH)
    audio = audio[:16000*5]
    
    speech_prob = vad.is_speech(audio)

    print("Speech probability:", speech_prob)

    if speech_prob < 0.7:
        return jsonify({
            "transcription": "",
            "wake_word_detected": False
        })
    

    transcribed_text, info = transcribe_audio(RECORD_PATH)
    text_norm = transcribed_text.strip().lower() if transcribed_text else ""
    
    # Empty transcription
    if not text_norm:
        return jsonify({
            "transcription": "",
            "response": "",
            "response_delay": 0,
            "wake_word_detected": False
        })

    # 🛑 Stop word interrupt: stop any currently speaking TTS
    if "stop" in text_norm:
        stop_tts()
        print("🛑 'stop' detected while speaking")
        return jsonify({
            "transcription": transcribed_text,
            "response": "🛑 Stopped.",
            "stop_detected": True,
            "wake_word_detected": False
        })

    # No wake word -> just echo info
    if SELECTED_WAKE_WORD not in text_norm:
        return jsonify({
            "wake_word_detected": False,
            "transcription": transcribed_text,
            "response": "❌ Wake word not detected."
        })

    # Wake word present -> handle query
    try:
        wake_index = text_norm.find(SELECTED_WAKE_WORD)

        if wake_index == -1:
            return jsonify({
                "wake_word_detected": False,
                "transcription": transcribed_text
            })

        # Keep only words AFTER wake word
        # query_text = text_norm[wake_index + len(SELECTED_WAKE_WORD):].strip()
        query_text = text_norm[wake_index + len(SELECTED_WAKE_WORD):].lstrip(", ").strip()

        # Remove filler phrases
        query_text = query_text.replace("tell me about", "")
        query_text = query_text.replace("can you explain", "")
        query_text = query_text.strip()
        if not query_text:
            return jsonify({
                "transcription": query_text,
                "response": "Yes?",
                "wake_word_detected": True
            })
        

        existing_knowledge = read_data_file()
        full_prompt = existing_knowledge + "\n\n" + query_text
        model_response = chat_with_ollama(full_prompt,model= SELECTED_OLLAMA_MODEL)  # You can change model as needed

        # 🔊 Start speaking in the background (can be interrupted by "stop")
        
        start_tts(model_response, CURRENT_VOICE)
        word_count = len(model_response.split()) 
        response_delay = max(2, max(5, word_count * 0.5))
        return jsonify({
            "transcription": query_text,
            "response": model_response,
            "response_delay":response_delay ,  
            "wake_word_detected": True
        })

    except Exception as e:
        print(f"Error in processing query: {e}")
        return jsonify({"transcription": transcribed_text, "response": "Error processing your query."})
@app.route("/get_tts_voices")
def get_tts_voices():
    return jsonify({
        "available": AVAILABLE_VOICES,
        "selected": CURRENT_VOICE
    })

@app.route("/set_tts_voice", methods=["POST"])
def set_tts_voice():
    global CURRENT_VOICE
    data = request.json
    CURRENT_VOICE = data.get("voice", CURRENT_VOICE)

    return jsonify({"status": "success", "voice": CURRENT_VOICE})

def truncate_to_40_words_complete_sentences(text, max_words=30):
    # Join lines first
    text = re.sub(r'\n+', ' ', text).strip()

    # Fix colon-ended sentence issue
    text = re.sub(r':\s+', ': ', text)

    sentences = re.split(r'(?<=[.!?])\s+', text)

    result = []
    word_count = 0

    for s in sentences:
        words = s.split()
        if word_count + len(words) <= max_words:
            result.append(s)
            word_count += len(words)
        else:
            break

    final = " ".join(result).strip()

    # Remove dangling colon
    if final.endswith(":"):
        final = final[:-1]

    return final


    
import re
def chat_with_ollama(prompt: str, model: str = "") -> str:
    """Chats with Ollama using only a text prompt."""
    url = "http://localhost:11434/api/chat"
    MAX_TOKENS = 700
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        "options": {
            "num_predict": MAX_TOKENS, 
            # "stop": [ "\n\n"] 
        }
    }
    try:
        response = requests.post(url, json=payload, stream=True, timeout=300)
        if response.status_code == 200:
            final_response = ""
            for line in response.iter_lines(decode_unicode=True):
                if line:
                    try:
                        json_data = json.loads(line)
                        if "message" in json_data and "content" in json_data["message"]:
                            final_response += json_data["message"]["content"]
                            if json_data.get("done"): # Stop once the 'done' flag is received
                                break
                    except json.JSONDecodeError:
                        continue
            # return final_response.strip()
            raw_text = final_response.strip()
            MAX_SENTENCES = 3
            sentence_split_pattern = r'(?<=[.?!])\s+(?=[A-Z])'
            
            # Temporarily replace common, problematic abbreviations to prevent premature splitting
            raw_text = re.sub(r'Mr\.', 'Mr·', raw_text)
            raw_text = re.sub(r'Ms\.', 'Ms·', raw_text)
            raw_text = re.sub(r'Dr\.', 'Dr·', raw_text)
            raw_text = re.sub(r'i\.e\.', 'i·e·', raw_text)
            raw_text = re.sub(r'e\.g\.', 'e·g·', raw_text)

            # Split the text into sentence candidates
            sentences = re.split(sentence_split_pattern, raw_text)
            
            # Rejoin the temporary abbreviation markers
            sentences = [s.replace('·', '.') for s in sentences]
            
            # Truncate the list of sentences to the maximum allowed 
            truncated_sentences = sentences[:MAX_SENTENCES]
            
            # Rejoin the truncated sentences
            final_response = ' '.join(truncated_sentences).strip()
            
            # --- POST-PROCESSING LOGIC ENDS HERE ---
            
            return final_response.strip()
        else:
            return f"Error: {response.status_code} - {response.text}"
    except requests.RequestException as e:
        return f"Request failed: {str(e)}"

@app.route('/askmodel', methods=['GET'])
def ask_model():
    user_input = request.args.get('text', '')
    selected_model = request.args.get('model', 'SELECTED_OLLAMA_MODEL')
    language = request.args.get('lang', 'en')
    if not user_input:
        return jsonify({'error': 'No input provided'}), 400
    language_map = {"en": "English", "hi": "Hindi", "es": "Spanish", "fr": "French", "de": "German"}
    language_name = language_map.get(language, "English")
    existing_knowledge = read_data_file()
    prompt = existing_knowledge + "\n\n" + user_input
    model_response = chat_with_ollama(prompt,model= selected_model)#, language=language_name
    chat_history.append({"role": "user", "text": user_input})
    chat_history.append({"role": "assistant", "text": model_response})
    html_content = markdown.markdown(model_response)
    # Speak in text mode too (optional). Comment out to disable.
    # start_tts(model_response)
    return jsonify({'response': html_content})
from flask import Flask, jsonify, request
import subprocess
import os

import time 
# @app.route("/system_usage", methods=["GET"])
# def system_usage():
   
#     process = psutil.Process(os.getpid())

#     cpu_percent = process.cpu_percent(interval=0.5)
#     ram_mb = process.memory_info().rss / (1024 ** 2)
#     system_ram_percent = psutil.virtual_memory().percent

#     return jsonify({
#         "process_cpu_percent": round(cpu_percent, 2),
#         "process_ram_mb": round(ram_mb, 2),
#         "system_ram_percent": round(system_ram_percent, 2)
#     })
# # --- Ollama Control Endpoints ---

@app.route('/ollama_status', methods=['GET'])
def ollama_status():
    """Checks the status of the Ollama service."""
    try:
        # NOTE: The exact command depends on your OS and how Ollama is running.
        # This is a common command for checking if the Ollama API is reachable.
        result = subprocess.run(['curl', '-s', 'http://localhost:11434'], capture_output=True, text=True, timeout=2)
        if "Ollama is running" in result.stdout or result.returncode == 0:
             return jsonify({'status': 'running'})
        else:
             return jsonify({'status': 'stopped', 'output': result.stdout})
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        # If curl isn't found, or connection times out, assume stopped or error
        return jsonify({'status': 'stopped', 'error': 'Connection refused or process check failed'})
    except Exception as e:
        return jsonify({'status': 'unknown', 'error': str(e)})

@app.route('/ollama_control', methods=['POST'])
def ollama_control():
    """Starts or stops the Ollama service."""
    action = request.args.get('action') # 'start' or 'stop'

    if action == 'start':
        command = ['ollama', 'serve'] 
    elif action == 'stop':
        command = ['pkill', 'ollama'] 
    else:
        return jsonify({'status': 'error', 'message': 'Invalid action'}), 400

    try:
        if action == 'start':
            subprocess.Popen(command, start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            # Give it a moment to start
            time.sleep(1) 
            return jsonify({'status': 'success', 'message': 'Ollama start command sent.'})
        else: # Stop or other action
            subprocess.run(command, check=True)
            return jsonify({'status': 'success', 'message': f'Ollama {action} command executed.'})
            
    except subprocess.CalledProcessError as e:
        return jsonify({'status': 'error', 'error': f'Command failed: {e.stderr}', 'details': str(e)})
    except Exception as e:
        return jsonify({'status': 'error', 'error': f'Failed to execute command: {str(e)}'})
@app.route("/stop_tts", methods=["POST"])
def api_stop_tts():
    stop_tts()
    return jsonify({"message": "TTS stopped."})
@app.route("/get_chat_history")
def get_chat_history():
    return jsonify({"chats": chat_history})



@app.route('/describe_image', methods=['POST'])
def describe_image():
    if 'image' not in request.files:
        return jsonify({"error": "No image file part"}), 400

    image_file = request.files['image']
    if image_file.filename == '':
        return jsonify({"error": "No image selected"}), 400

    # Optional: Get a text prompt from the frontend (e.g., "What is this?")
    # prompt = request.form.get('prompt', 'Describe this image in detail.')
    base_prompt = request.form.get('prompt', 'What is in this image?')
    
    # We instruct the model to analyze everything but summarize the output
    summary_prompt = (
        f"Analyze this image based on the request: '{base_prompt}'. "
        "Summarize the entire description into atmost 40 words "
        "Focus only on the most important details."
        "Do not say 'here is the concise response' or similar - just give the concise summary directly."
    )
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
        
    # Use a unique name to avoid conflicts, or a simple one for temporary use
    filename = "temp_image.jpg" # Consider using image_file.filename or a UUID
    save_path = os.path.join(UPLOAD_FOLDER, filename)
    
    try:
        image_file.save(save_path)
        # NOTE: Ensure you have a multimodal model like 'gemma3:4b' installed in Ollama
        model_response = chat_with_ollama_multimodal(summary_prompt, save_path, model="ngo-model:latest")  # Adjust model name as needed

        # Cleanup the saved image file after processing
        os.remove(save_path)
        summary_lines = [line.strip() for line in model_response.split('\n') if line.strip()]
        # Format response as markdown for display
        final_summary = '\n'.join(summary_lines[:4])
        html_content = markdown.markdown(final_summary)
        
        # Optional: Start TTS for the response
        # start_tts(model_response)
        
        return jsonify({'response': html_content})
    except Exception as e:
        # Clean up if an error occurred after saving
        if os.path.exists(save_path):
            os.remove(save_path)
        print(f"Image description error: {e}")
        return jsonify({"error": str(e)}), 500
def chat_with_ollama_multimodal(prompt: str, image_path: None, model: str = "ngo-model:latest") -> str:
    """Chats with Ollama, including an image."""
    url = "http://localhost:11434/api/chat"

    # 1. Read image and encode to base64
    try:
        with open(image_path, "rb") as f:
            image_data_base64 = base64.b64encode(f.read()).decode("utf-8")
        
    except FileNotFoundError:
        return "Error: Image file not found for processing."

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user", 
                "content": prompt, 
                "images": [image_data_base64]
            }
        ],
        "options": {
            "temperature": 0.3,   # Lower = more focused on instructions
            "num_predict": 150    # Enough room for 4 meaningful lines but prevents rambling
        },
        "stream": False
    }

    try:
        response = requests.post(url, json=payload, stream=True, timeout=300)
        if response.status_code == 200:
            final_response = ""
            for line in response.iter_lines(decode_unicode=True):
                if line:
                    try:
                        json_data = json.loads(line)
                       
                        if "message" in json_data and "content" in json_data["message"]:
                            final_response += json_data["message"]["content"]
                    except json.JSONDecodeError:
                        continue
            return final_response.strip()
        else:
            return f"Error: {response.status_code} - {response.text}"
    except requests.RequestException as e:
        return f"Request failed: {str(e)}"

def read_data_file(filename="data2.txt") -> str:
    try:
        with open(filename, "r", encoding="utf-8") as file:
            return file.read().strip()
    except FileNotFoundError:
        return "Error: data2.txt not found!"
    except Exception as e:
        return f"Error reading file: {str(e)}"

def read_pdf(pdf_path, txt_file='data2.txt'):
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            pdf_text = ''
            for page_num in range(len(reader.pages)):
                page = reader.pages[page_num]
                pdf_text += page.extract_text() or ''
        with open(txt_file, 'a', encoding='utf-8') as f:
            f.write(f"\n###FILE:{os.path.basename(pdf_path)}###\n")
            f.write(pdf_text + '\n')
        print(f"PDF content successfully appended to {txt_file}.")
    except Exception as e:
        print(f"An error occurred: {e}")

def read_docx(docx_path, txt_file='data2.txt'):
    try:
        doc = Document(docx_path)
        full_text = '\n'.join([para.text for para in doc.paragraphs])
        with open(txt_file, 'a', encoding='utf-8') as f:
            f.write(f"\n###FILE:{os.path.basename(docx_path)}###\n")
            f.write(full_text + '\n')
        print(f"DOCX content successfully appended to {txt_file}.")
    except Exception as e:
        print(f"An error occurred while reading DOCX: {e}")

def transcribe_audio(filename):
    # faster-whisper will decode via ffmpeg if needed; the frontend sends webm
    try:
        segments, info = whisper_model.transcribe(
            filename,
            vad_filter=True
        )
        text = " ".join([s.text.strip().lower() for s in segments])
        return text, info
    except Exception as e:
        print(f"⚠️ Whisper failed to decode audio: {e}")
        return "", None
# ---------- Main ----------
if __name__ == '__main__':
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(debug=False)


