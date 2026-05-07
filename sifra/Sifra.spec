# -*- mode: python ; coding: utf-8 -*-

import os
import language_tags
import espeakng_loader
import openwakeword

block_cipher = None

language_tags_path = os.path.join(os.path.dirname(language_tags.__file__), "data")
espeak_data_path = os.path.join(os.path.dirname(espeakng_loader.__file__), "espeak-ng-data")
oww_resources_path = os.path.join(os.path.dirname(openwakeword.__file__), "resources")

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[
        ('/opt/homebrew/lib/libespeak-ng.dylib', 'espeakng_loader'),
    ],
    datas=[
        ('sifra.onnx', '.'),
        ('kokoro-v1.0.onnx', '.'),
        ('voices-v1.0.bin', '.'),
        (language_tags_path, 'language_tags/data'),
        (espeak_data_path, 'espeakng_loader/espeak-ng-data'),
        (oww_resources_path, 'openwakeword/resources'),
    ],
    hiddenimports=[
        'language_tags',
        'espeakng_loader',
        'openwakeword',
        'pyaudio',
        'sounddevice',
        'onnxruntime',
        'cv2',
        'faster_whisper',
        'kokoro_onnx',
        'ollama',
    ],
    noarchive=True,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Sifra',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name='Sifra',
)

app = BUNDLE(
    coll,
    name='Sifra.app',
    bundle_identifier='com.sifra.app',
    info_plist={
        'CFBundleName': 'Sifra',
        'CFBundleDisplayName': 'Sifra',
        'NSMicrophoneUsageDescription': 'Sifra needs microphone access to listen for voice commands.',
        'NSCameraUsageDescription': 'Sifra uses the camera for visual understanding.',
        'NSSpeechRecognitionUsageDescription': 'Sifra converts speech to text.',
    }
)