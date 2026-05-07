
# Sifra – Offline Voice Assistant

Sifra is an **on-device, offline voice assistant** that works hands-free and is activated using the wake word **"Sifra"**.

---

##  Features

* Fully **offline** system
* Wake-word detection
* Speech-to-Text using Whisper
* LLM responses via Ollama
* Text-to-Speech using Kokoro TTS
* Image-based query support 

---

##  Requirements

###  System

* macOS
* Python **3.10+**
* Microphone (required)
* Camera (for vision features)

---


##  Installation

###  Clone the repository

```bash
git clone https://github.com/mehakagrawal02/On-device-Privacy-Preserving-AI-Assistant.git
cd On-device-Privacy-Preserving-AI-Assistant/sifra
```

---

### Create virtual environment

```bash
python -m venv venv
source venv/bin/activate
```

---

### Install dependencies

```bash
pip install -r requirements.txt
```

---

### Install system dependencies

```bash
brew install portaudio
```

---

###  Install Ollama

Download from: https://ollama.com

Then pull required models:

```bash
ollama pull gemma3:1b
ollama pull gemma4:e2b
ollama pull qwen2.5:1.5b
ollama pull moondream:latest
```

Start Ollama:

```bash
ollama serve
```

---

##  Required Model Files (Manual Setup)

These files are **not included in the repository**.

Place them in the **project root directory** (same folder as `main.py`):

```
sifra/
│── main.py
│── sifra.onnx
│── kokoro-v1.0.onnx
│── voices-v1.0.bin
```

---

###  Wake Word Model

* File: `sifra.onnx`
* Train using OpenWakeWord OR use a pretrained model from https://github.com/dscripka/openWakeWord

---

###  Kokoro TTS Model

Download:

```
kokoro-v1.0.onnx
voices-v1.0.bin
```

From:
https://github.com/nazdridoy/kokoro-tts

---

## Running the Assistant

```bash
python main.py
```

---

##  How It Works

* Say **“Sifra”** → activates assistant
* A sound confirms activation
* You can speak multiple queries
* If silent for 10 seconds → system deactivates
* Say wake word again to reactivate

---



##  Packaging the Application (macOS)

###  Spec File

The build uses:

```
Sifra.spec
```

 Located in the **project root directory**

---

###  Install tools

```bash
pip install pyinstaller
brew install create-dmg
```

---

### Clean previous builds

```bash
rm -rf build dist
```

---

### Build app

```bash
pyinstaller Sifra.spec --clean
```

Output:

```
dist/Sifra.app
```

---

### Fix macOS security issue

```bash
xattr -cr dist/Sifra.app
```

---

### Create DMG installer

```bash
create-dmg \
  --volname "Sifra Installer" \
  --window-pos 200 120 \
  --window-size 800 400 \
  --icon-size 100 \
  --icon "Sifra.app" 200 190 \
  --hide-extension "Sifra.app" \
  --app-drop-link 600 185 \
  "Sifra.dmg" \
  "dist/Sifra.app"
```

---

### Install App

1. Open `Sifra.dmg`
2. Drag **Sifra.app** to Applications
3. Launch from Applications

---

