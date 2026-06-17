import cv2
import time
import os
from datetime import datetime
from flask import Flask, Response
from ultralytics import YOLO

# =========================
# Config
# =========================

MODEL_PATH = "yolov8n.pt"
CONFIDENCE_THRESHOLD = 0.5

# =========================
# Init
# =========================

app = Flask(__name__)
model = YOLO(MODEL_PATH)

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

os.makedirs("snapshots", exist_ok=True)

print("Server starting...")

# =========================
# Frame generator
# =========================

def generate_frames():
    last_alert_time = 0
    ALERT_INTERVAL = 10

    while True:
        success, frame = cap.read()
        if not success:
            break

        results = model(frame, verbose=False)

        person_count = 0

        for box in results[0].boxes:
            cls = int(box.cls[0])
            conf = float(box.conf[0])
            name = model.names[cls]

            if name == "person" and conf > CONFIDENCE_THRESHOLD:
                person_count += 1

        annotated = results[0].plot()

        status = "SAFE"
        if person_count > 0:
            status = "ALERT"

        cv2.putText(annotated, f"Persons: {person_count}", (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)

        cv2.putText(annotated, f"Status: {status}", (20, 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 2)

        # snapshot
        now = time.time()
        if person_count > 0 and now - last_alert_time > ALERT_INTERVAL:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = f"snapshots/alert_{ts}.jpg"
            cv2.imwrite(path, annotated)
            print("Saved:", path)
            last_alert_time = now

        # encode frame
        ret, buffer = cv2.imencode('.jpg', annotated)
        frame = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

# =========================
# Routes
# =========================

@app.route('/')
def index():
    return """
    <html>
    <head>
        <title>AI Security Guard</title>
    </head>
    <body>
        <h1>RK3576 AI Security Guard</h1>
        <img src="/video" width="800"/>
    </body>
    </html>
    """

@app.route('/video')
def video():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

# =========================
# Run
# =========================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)