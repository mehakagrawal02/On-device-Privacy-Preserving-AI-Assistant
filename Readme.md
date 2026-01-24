# ALOPA: An AI-Powered Lightweight On-Device Private Assistant

## Overview
The proposed system is a completely offline and on-device, AI-based personal assistant. It ensures data privacy since it does not send user data to any external server. 

<!-- ## System Architecure
This system takes in voice input from the user. Only when the wake-word is detected, the query along with the context is sent to the LLM for generating a response to user query. The response is converted to speech to provided a voice output to the user. -->

## Features
1. Fully offline and on-device functionality.
2. Offline Speech-To-Text conversion using faster-whisper.
3. Offline Text-To-Speech conversion using Piper TTS.
4. Complete Hands-free functionality.
5. Wake-word based interaction.
6. Document-based query support.
7. Image-based query input.


## System Requirements
1. macOS 
2. **Headphones are highly recommended to prevent self-interruption.**
3. Python3.10+ 
4. Ollama: Required for running local LLMs
5. ffmpeg: Required for audio decoding
6. PortAudio: Required for audio playback

## Setup Instructions
1. Clone the repository install all required dependencies: 
    ```
    brew install ffmpeg portaudio
    ```
2. Download ollama from: https://ollama.com
3. Start Ollama

    ```
    ollama serve
    ```
3. Pull required models, for example: Gemma3 1b, Qwen2.5 1.5B etc.
    ```
    ollama pull gemma3:1b
    ollama pull qwen2.5:1.5b
    ```
4. Create and activate a virtual environment: 
    ```
    python -m venv venv
    source venv/bin/activate
    ```

5. Install all requirements:
    ```
    pip install -r requirements.txt 
    ```
6. Download Piper voices(.onnx and .onnx.json) from https://github.com/OHF-Voice/piper1-gpl
7. Place both the .onnx and .onnx.json files in a single directory. Update the directory path in main.py.
8. Run the system : 
    ```
    python main.py
    ```

