# Beyond the Cloud: Offline Secure Voice Assistance

## Overview

The proposed system is a fully offline, on-device AI voice assistant designed for **privacy-first interaction**. It supports wake-word activation, speech to text conversion, local LLM responses via Ollama, and natural-sounding TTS using Kokoro.


---

##  Features

* Fully offline & private 
*  Wake-word based activation 
*  Local LLM responses using Ollama
*  Speech-to-Text using Faster-Whisper
*  Text-to-Speech using Kokoro TTS
*  Document-based querying (PDF & DOCX)
*  Image-based query support

##  System Requirements

* macOS 
* Python 3.10+
* Headphones (strongly recommended)

### Dependencies (System-level)

```bash
brew install ffmpeg portaudio
```

### Install Ollama from: 
https://ollama.com

---

##  Setup Instructions

### 1. Clone Repository

```bash
git clone https://github.com/mehakagrawal02/On-device-Privacy-Preserving-AI-Assistant.git
cd On-device-Privacy-Preserving-AI-Assistant
```

---

### 2. Start Ollama

```bash
ollama serve
```

---

### 3. Pull Required Models

```bash
ollama pull gemma3:1b
ollama pull qwen2.5:1.5b
ollama pull gemma3:4b
ollama pull gemma4:e2b
```
---

### 4. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate
```

---

### 5. Install Python Dependencies

```bash
pip install -r requirements.txt
```

---

### 6. Download Required Models

####  Silero VAD

Download `silero_vad.onnx` from https://github.com/snakers4/silero-vad and place it in the root directory.

####  Kokoro TTS

Download:

```
kokoro-v1.0.onnx
voices-v1.0.bin
```

From:
https://github.com/nazdridoy/kokoro-tts

Place both files in the root project directory (same folder as main.py).
---

### 7. Run the Application

```bash
python main.py
```

---


##  File Structure

```
├── main.py
├── data2.txt             
├── uploads/               
├── templates/
├── static/
├── silero_vad.onnx
└── requirements.txt
```

---


### How to Interact with the System
1. Voice Queries: Speak the wake word along with the query to interact hands-free with the assistant.
2. Text-Based Queries: Queries can also be entered directly through text input.
3. Document Queries: Upload a PDF or DOCX file and ask questions related to the document using either voice or text.
4. Image-Based Queries: Provide a question related to the image and capture an image for visual query processing.
5. Settings: The system allows users to customise the wake word, select different local LLMs, and change the response voice. 
6. Custom Prompt: Allows to modify the system's responses as per user preference.