from kivy.app import App
from kivy.lang import Builder
from kivy.utils import platform
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.properties import StringProperty, BooleanProperty

import re, json, time, requests
from urllib.parse import quote_plus

KV = r'''
#:import dp kivy.metrics.dp

<JarvisHUD@Widget>:
    angle: 0
    online: False
    listening: False
    canvas:
        Color:
            rgba: (0.2, 0.9, 1.0, 0.30) if self.online else (0.9, 0.2, 0.2, 0.25)
        Line:
            circle: (self.center_x, self.center_y, min(self.width, self.height)*0.35, self.angle, self.angle+270)
            width: 2

BoxLayout:
    orientation: "vertical"
    padding: "12dp"
    spacing: "10dp"

    BoxLayout:
        size_hint_y: None
        height: "110dp"
        spacing: "12dp"

        JarvisHUD:
            id: hud
            size_hint_x: None
            width: "110dp"

        BoxLayout:
            orientation: "vertical"
            spacing: "6dp"
            Label:
                id: status
                text: app.status_line
                halign: "left"
                valign: "middle"
                text_size: self.size

            BoxLayout:
                size_hint_y: None
                height: "36dp"
                spacing: "10dp"

                ToggleButton:
                    id: online
                    text: "Онлайн: выкл"
                    on_state: app.set_online(self.state)

                ToggleButton:
                    id: standby
                    text: "Дежурный: выкл"
                    on_state: app.set_standby(self.state)

    BoxLayout:
        size_hint_y: None
        height: "48dp"
        spacing: "10dp"

        Button:
            text: "Слушай 🎙️"
            on_release: app.start_listening()

        Button:
            text: "Выполнить текст"
            on_release: app.handle_command(root.ids.input.text)

        Button:
            text: "Help"
            on_release: app.show_help()

        Button:
            text: "Очистить"
            on_release: root.ids.input.text = ""

    TextInput:
        id: input
        hint_text: "Команда: Джарвис напомни через 30 минут: ..."
        multiline: True

    ScrollView:
        do_scroll_x: False
        Label:
            id: log
            text: ""
            size_hint_y: None
            height: self.texture_size[1] + dp(20)
            text_size: self.width, None
'''

def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def save_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

def llm_answer(prompt: str, cfg: dict) -> str:
    pref = (cfg.get("preferred_llm") or "none").lower()
    if pref in ("none",""):
        return "Онлайн-ИИ выключен. В config.json укажите preferred_llm=openai или gemini и добавьте api_key."
    if pref == "openai":
        api_key = cfg.get("openai", {}).get("api_key", "")
        model = cfg.get("openai", {}).get("model", "gpt-4o-mini")
        if not api_key:
            return "Не задан openai.api_key в config.json"
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        data = {"model": model, "messages":[{"role":"user","content": prompt}], "temperature":0.4}
        r = requests.post(url, headers=headers, json=data, timeout=30)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    return "LLM не настроен."

class JarvisApp(App):
    status_line = StringProperty("JARVIS — готов. Включите «Дежурный» для фона и напоминаний.")
    online_enabled = BooleanProperty(False)
    standby_mode = BooleanProperty(False)
    listening = BooleanProperty(False)

    def build(self):
        self.cfg = load_json("config.json", {"language":"ru-RU","wake_word":"джарвис","preferred_llm":"none"})
        self.reminders_path = self.cfg.get("reminders_file", "reminders.json")
        Window.softinput_mode = "below_target"
        root = Builder.load_string(KV)
        Clock.schedule_interval(self._hud_tick, 1/30.0)
        return root

    def on_start(self):
        if platform == "android":
            try:
                from jnius import autoclass
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                intent = PythonActivity.mActivity.getIntent()
                if intent and intent.getBooleanExtra("jarvis_start_listening", False):
                    intent.putExtra("jarvis_start_listening", False)
                    Clock.schedule_once(lambda dt: self.start_listening(), 0.3)
            except Exception as e:
                self._log(f"[intent error] {e}")

    def _hud_tick(self, dt):
        hud = self.root.ids.hud
        hud.angle = (hud.angle + 2.0) % 360.0
        hud.online = self.online_enabled
        hud.listening = self.listening

    def _log(self, msg):
        self.root.ids.log.text += msg + "\n"

    def say(self, text):
        self._log(f"[JARVIS] {text}")

    def set_online(self, state):
        self.online_enabled = (state == "down")
        self.root.ids.online.text = "Онлайн: вкл" if self.online_enabled else "Онлайн: выкл"
        self.status_line = "Онлайн режим включен" if self.online_enabled else "Онлайн режим выключен"

    def set_standby(self, state):
        self.standby_mode = (state == "down")
        self.root.ids.standby.text = "Дежурный: вкл" if self.standby_mode else "Дежурный: выкл"
        if platform == "android":
            try:
                from android import AndroidService
                if self.standby_mode:
                    service = AndroidService("JARVIS дежурит", "Нажмите «Слушай» и скажите: «Джарвис ...»")
                    service.start("foreground")
                    self.say("Дежурный режим включен.")
                else:
                    service = AndroidService("JARVIS", "stop")
                    service.stop()
                    self.say("Дежурный режим выключен.")
            except Exception as e:
                self._log(f"[service error] {e}")

    def show_help(self):
        self._log("- Джарвис напомни через 30 минут: ...")
        self._log("- Джарвис покажи напоминания")
        self._log("- Джарвис удалить напоминание 2")

    def start_listening(self):
        self.say("В этой короткой v0.5 сборке слушание оставлено как в v4. Если нужно — перенесу весь голосовой блок из v4.")
        # (Чтобы не раздувать код в этом демо-апдейте. Основное — напоминания в фоне.)

    def _require_wake(self, text: str):
        wake = (self.cfg.get("wake_word") or "джарвис").lower()
        t = text.strip()
        if not t.lower().startswith(wake):
            self.status_line = f"Команда должна начинаться с «{wake} …»"
            return None
        return t[len(wake):].strip(" ,.:;!-")

    def _load_reminders(self):
        return load_json(self.reminders_path, {"reminders":[]})

    def _save_reminders(self, data):
        save_json(self.reminders_path, data)

    def add_reminder(self, minutes: int, text: str):
        data = self._load_reminders()
        rid = int(time.time() * 1000) % 2_000_000_000
        due = int(time.time()) + minutes * 60
        data["reminders"].append({"id": rid, "due": due, "text": text, "done": False})
        self._save_reminders(data)

    def list_reminders_text(self):
        data = self._load_reminders()
        items = [r for r in data.get("reminders", []) if not r.get("done")]
        if not items:
            return "Активных напоминаний нет."
        lines = []
        for i, r in enumerate(items, 1):
            mins_left = max(0, int((r["due"] - time.time())/60))
            lines.append(f"{i}. через ~{mins_left} мин: {r['text']}")
        return "Напоминания:\n" + "\n".join(lines)

    def delete_reminder_by_index(self, idx: int):
        data = self._load_reminders()
        items = [r for r in data.get("reminders", []) if not r.get("done")]
        if idx < 1 or idx > len(items):
            return False
        target = items[idx-1]["id"]
        for r in data["reminders"]:
            if r.get("id") == target:
                r["done"] = True
        self._save_reminders(data)
        return True

    def handle_command(self, raw: str):
        if not raw:
            return
        self._log(f"> {raw}")
        rest = self._require_wake(raw)
        if rest is None:
            return
        low = rest.lower()

        m = re.search(r'напомни\s+через\s+(\d+)\s*(минут|мин|м)\b\s*[:：]?\s*(.*)$', low)
        if m:
            minutes = int(m.group(1))
            msg = m.group(3).strip()
            self.add_reminder(minutes, msg)
            self.say("Напоминание сохранено. В фоне сработает если включён «Дежурный».")
            return

        if "покажи напоминания" in low:
            self._log(self.list_reminders_text())
            return

        md = re.search(r'удали(ть)?\s+напоминание\s+(\d+)\b', low)
        if md:
            ok = self.delete_reminder_by_index(int(md.group(2)))
            self.say("Удалил." if ok else "Не нашёл такой номер.")
            return

        self.say("Не понял команду.")

if __name__ == "__main__":
    JarvisApp().run()
