import cv2
import numpy as np
from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from server.database import init_db, insert_ticket_choice, seed_data
from server.utils.fasterRcnnCamera import PlateDetector

# ==================== App init ====================
app = FastAPI(title="SmartParking Server", version="1.0.0")
init_db()
seed_data()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# ==================== WebSocket camera ====================
@app.websocket("/ws/camera/{cam_id}")
async def camera_ws(ws: WebSocket, cam_id: int):
    await ws.accept()
    print(f"[SERVER] ✅ Client connected on cam {cam_id}")

    detector = PlateDetector(event_label="in" if cam_id == 0 else "out")

    while True:
        try:
            # Nhận frame từ client (raw bytes)
            frame_bytes = await ws.receive_bytes()
            arr = np.frombuffer(frame_bytes, dtype=np.uint8)
            frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)

            # Detect -> metadata
            meta = detector.process(frame)

            # Gửi metadata JSON cho client
            await ws.send_json(meta)

        except Exception as e:
            print(f"[SERVER] ⚠️ Error cam {cam_id}: {e}")
            break

# ==================== REST API chọn vé ====================
class TicketChoice(BaseModel):
    car_id: int
    plate: str
    vehicle_type: str
    ticket_type: str   # "visitor", "registered", "monthly", ...

@app.post("/api/ticket/choose")
async def choose_ticket(data: TicketChoice):
    try:
        insert_ticket_choice(
            car_id=data.car_id,
            plate=data.plate,
            vehicle_type=data.vehicle_type,
            ticket_type=data.ticket_type
        )
        return {"status": "success", "message": "Ticket choice saved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
