import time, json, os
from jnius import autoclass, cast

PythonService = autoclass('org.kivy.android.PythonService')
Context = autoclass('android.content.Context')
Intent = autoclass('android.content.Intent')
Build = autoclass('android.os.Build')

NotificationManager = autoclass('android.app.NotificationManager')
NotificationChannel = autoclass('android.app.NotificationChannel')
PendingIntent = autoclass('android.app.PendingIntent')
NotificationCompat = autoclass('androidx.core.app.NotificationCompat')

CHANNEL_ID = "jarvis_channel"
CHANNEL_NAME = "JarvisAI"
SERVICE_NOTIF_ID = 1337
REMINDER_NOTIF_ID_BASE = 2000

def ensure_channel():
    if Build.VERSION.SDK_INT >= 26:
        mgr = cast('android.app.NotificationManager', PythonService.mService.getSystemService(Context.NOTIFICATION_SERVICE))
        channel = NotificationChannel(CHANNEL_ID, CHANNEL_NAME, NotificationManager.IMPORTANCE_LOW)
        channel.setDescription("JarvisAI foreground service")
        mgr.createNotificationChannel(channel)

def get_launch_pending_intent(start_listening: bool):
    pkg = PythonService.mService.getPackageName()
    pm = PythonService.mService.getPackageManager()
    launch_intent = pm.getLaunchIntentForPackage(pkg)
    launch_intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_SINGLE_TOP)
    launch_intent.putExtra("jarvis_start_listening", bool(start_listening))

    flags = PendingIntent.FLAG_UPDATE_CURRENT
    if Build.VERSION.SDK_INT >= 23:
        flags |= PendingIntent.FLAG_IMMUTABLE
    return PendingIntent.getActivity(PythonService.mService, 0, launch_intent, flags)

def build_service_notification():
    pi = get_launch_pending_intent(True)
    builder = NotificationCompat.Builder(PythonService.mService, CHANNEL_ID)
    builder.setContentTitle("JARVIS дежурит")
    builder.setContentText("Нажмите «Слушай» и скажите: «Джарвис ...»")
    builder.setSmallIcon(PythonService.mService.getApplicationInfo().icon)
    builder.setOngoing(True)
    builder.setContentIntent(pi)
    builder.addAction(0, "Слушай", pi)
    return builder.build()

def notify_reminder(text: str, notif_id: int):
    pi = get_launch_pending_intent(False)
    builder = NotificationCompat.Builder(PythonService.mService, CHANNEL_ID)
    builder.setContentTitle("Напоминание")
    builder.setContentText(text)
    builder.setSmallIcon(PythonService.mService.getApplicationInfo().icon)
    builder.setAutoCancel(True)
    builder.setContentIntent(pi)
    mgr = cast('android.app.NotificationManager', PythonService.mService.getSystemService(Context.NOTIFICATION_SERVICE))
    mgr.notify(notif_id, builder.build())

def start_foreground():
    ensure_channel()
    PythonService.mService.startForeground(SERVICE_NOTIF_ID, build_service_notification())

def load_reminders(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"reminders":[]}

def save_reminders(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def main():
    start_foreground()
    reminders_path = os.path.join(os.getcwd(), "reminders.json")
    fired = set()
    while True:
        data = load_reminders(reminders_path)
        now = int(time.time())
        changed = False
        for r in data.get("reminders", []):
            rid = r.get("id")
            due = int(r.get("due", 0))
            done = bool(r.get("done", False))
            if done:
                continue
            if due <= now and rid not in fired:
                text = r.get("text", "")
                notify_reminder(text, REMINDER_NOTIF_ID_BASE + (int(rid) % 5000 if rid else 1))
                fired.add(rid)
                r["done"] = True
                changed = True
        if changed:
            save_reminders(reminders_path, data)
        time.sleep(2)

if __name__ == "__main__":
    main()
