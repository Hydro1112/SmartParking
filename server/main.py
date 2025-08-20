# server/main.py
import cv2
import numpy as np
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from server.database import init_db, get_all_history
from server.utils.fasterRcnnCamera import PlateDetector  # <-- thêm import

app = FastAPI(title="SmartParking Server", version="1.0.0")
init_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.websocket("/ws/camera/{cam_id}")
async def camera_ws(ws: WebSocket, cam_id: int):
    await ws.accept()
    print(f"[SERVER] ✅ Client connected on cam {cam_id}")

    # gán nhãn sự kiện theo cam_id (tùy bạn map thế nào)
    event_label = "in" if cam_id == 0 else "out"
    detector = PlateDetector(event_label=event_label)

    while True:
        try:
            # Nhận frame từ client (hex JPG)
            msg = await ws.receive_text()
            frame_bytes = bytes.fromhex(msg)
            arr = np.frombuffer(frame_bytes, dtype=np.uint8)
            frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)

            # Detect + vẽ
            processed, meta = detector.process(frame)

            ok, buf = cv2.imencode(".jpg", processed)
            if not ok:
                # Nếu có lỗi encode, gửi lại frame gốc
                ok, buf = cv2.imencode(".jpg", frame)

            await ws.send_json({
                "frame": buf.tobytes().hex(),
                "meta": meta
            })

        except Exception as e:
            # log nếu cần
            break
