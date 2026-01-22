[app]
title = JarvisAI
package.name = jarvisai
package.domain = org.jarvis
source.dir = .
source.include_exts = py,kv,png,jpg,atlas,txt,json
version = 0.5

requirements = python3,kivy,requests,pyjnius
orientation = portrait
fullscreen = 0

android.permissions = INTERNET,RECORD_AUDIO,CAMERA,MODIFY_AUDIO_SETTINGS,WAKE_LOCK,FOREGROUND_SERVICE,POST_NOTIFICATIONS
services = jarvis_service:service.py:foreground

android.api = 34
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a
android.enable_androidx = True

[buildozer]
log_level = 2
warn_on_root = 1
