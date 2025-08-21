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

    event_label = "in" if cam_id == 0 else "out"
    detector = PlateDetector(event_label=event_label)

    while True:
        try:
            # Nhận frame từ client (raw bytes)
            frame_bytes = await ws.receive_bytes()
            arr = np.frombuffer(frame_bytes, dtype=np.uint8)
            frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)

            # Detect (frame để bỏ, chỉ lấy meta)
            meta = detector.process(frame)

            # Gửi metadata JSON cho client
            await ws.send_json(meta)

        except Exception as e:
            print(f"[SERVER] ⚠️ Error cam {cam_id}: {e}")
            break


