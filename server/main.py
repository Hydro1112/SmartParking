import cv2
import numpy as np
import uuid
from datetime import datetime
from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

from server.database.database import init_db, seed_data
from server.utils.fasterRcnnCamera import PlateDetector
from server.database.database_manager import DatabaseManager, Ticket, History

# ==================== App init ====================
app = FastAPI(title="SmartParking Server", version="1.0.0")
db_manager = DatabaseManager("server/database/parking.db")
init_db()
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

    is_out_gate = (cam_id == 1)
    detector = PlateDetector(db_manager, event_label="out" if is_out_gate else "in")

    while True:
        try:
            frame_bytes = await ws.receive_bytes()
            arr = np.frombuffer(frame_bytes, dtype=np.uint8)
            frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)

            if frame is None: continue

            meta = detector.process(frame)
            await ws.send_json(meta)

            if is_out_gate and meta.get("plates"):
                for vehicle_data in meta["plates"]:
                    plate = vehicle_data.get("plate")
                    if not plate: continue
                    
                    active_ticket = db_manager.get_active_ticket_by_plate(plate)
                    
                    if active_ticket:
                        print(f"[SERVER] 🔎 Xe ra: {plate}, tìm thấy vé active: {active_ticket.id}")
                        now = datetime.now()
                        checkin_time = datetime.strptime(active_ticket.checkin_time, "%Y-%m-%d %H:%M:%S")
                        duration_minutes = int((now - checkin_time).total_seconds() / 60)
                        
                        active_ticket.checkout_time = now.strftime("%Y-%m-%d %H:%M:%S")
                        active_ticket.status = "closed"
                        active_ticket.duration = duration_minutes
                        
                        db_manager.update_ticket(active_ticket)
                        
                        history_out = History(
                            vehicle_id=active_ticket.vehicle_id, plate=plate,
                            gate=f"Gate Cam {cam_id}", camera_id=cam_id,
                            event_type="out", ticket_id=active_ticket.id
                        )
                        db_manager.create_history_event(history_out)
                        print(f"[SERVER] 📝 Cập nhật vé và ghi lịch sử ra cho xe {plate}")

        except Exception as e:
            print(f"[SERVER] ⚠️ Error cam {cam_id}: {e}")
            break

# ==================== REST API ====================
class TicketChoice(BaseModel):
    car_id: str; plate: str; vehicle_type: str | None = None; ticket_type: str

@app.post("/api/ticket/choose")
async def choose_ticket(data: TicketChoice):
    try:
        ticket_id = f"H{str(uuid.uuid4().hex[:5]).upper()}"
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        new_ticket = Ticket(
            id=ticket_id, vehicle_id=data.car_id, plate=data.plate,
            ticket_type=data.ticket_type, checkin_time=now_str, status="active"
        )
        created_id = db_manager.create_ticket(new_ticket)
        print(f"[SERVER] ✅ Created ticket {created_id} for plate {data.plate}")

        history_in = History(
            vehicle_id=data.car_id, plate=data.plate, gate="Gate Cam 0",
            camera_id=0, event_type="in", ticket_id=created_id
        )
        db_manager.create_history_event(history_in)
        print(f"[SERVER] 📝 Ghi lịch sử vào cho xe {data.plate}")

        return {"status": "success", "ticket_id": created_id}
    except Exception as e:
        print(f"[SERVER] ❌ DB insert error: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

# ✨ API MỚI ĐỂ LẤY THÔNG TIN HIỂN THỊ LÊN GIAO DIỆN ✨

@app.get("/api/history/latest")
async def get_latest_history():
    latest_in = db_manager.get_latest_history("in")
    latest_out = db_manager.get_latest_history("out")

    # 👇 THAY THẾ TOÀN BỘ HÀM enrich_history BẰNG ĐOẠN NÀY 👇
    def enrich_history(history: dict | None):
        if not history:
            return None
        
        plate = history.get("plate")
        vehicle = db_manager.get_vehicle_by_plate(plate) if plate else None
        
        # Lấy thêm thông tin vé để hiển thị ticket_type
        ticket = None
        ticket_id = history.get("ticket_id")
        if ticket_id:
            ticket = db_manager.get_ticket_by_id(ticket_id)

        # Gộp thông tin lại
        enriched_data = {
            "history": history,
            "vehicle": vehicle,
            "ticket": ticket
        }
        return enriched_data
    # 👆 KẾT THÚC PHẦN THAY THẾ 👆

    return {
        "latest_in": enrich_history(latest_in),
        "latest_out": enrich_history(latest_out)
    }