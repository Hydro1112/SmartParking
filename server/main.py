# FILE: main.py (FINAL VERSION)
# ----------------------------------------------------------------------
import cv2
import numpy as np
import uuid
from datetime import datetime
from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import torch
import traceback
from pathlib import Path
from fastapi import status

from server.database.database import init_db
from server.utils.fasterRcnnCamera import PlateDetector, _init_models, CAM_W, CAM_H
from server.utils.readLicensePlate import get_ocr
from server.database.database_manager import DatabaseManager, Vehicle, Ticket, History
from server.ticketing import (
    VALID_TICKET_TYPES,
    closes_on_checkout,
    is_monthly_ticket_valid,
    ticket_prefix,
)

# ==================== App init ====================
app = FastAPI(title="SmartParking Server", version="1.0.0")
PROJECT_ROOT = Path(__file__).resolve().parents[1]
db_manager = DatabaseManager(str(PROJECT_ROOT / "server/database/parking.db"))
init_db()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=False, allow_methods=["*"], allow_headers=["*"]
)

# ==================== Helper Function (Tái sử dụng) ====================
def _enrich_history(history_event: dict | None):
    """Lấy thông tin vehicle và ticket để bổ sung cho một sự kiện lịch sử."""
    if not history_event: return None
    plate = history_event.get("plate")
    vehicle_obj = db_manager.get_vehicle_by_plate(plate) if plate else None
    ticket_obj = db_manager.get_ticket_by_id(history_event.get("ticket_id")) if history_event.get("ticket_id") else None
    
    vehicle = vars(vehicle_obj) if vehicle_obj else None
    ticket = vars(ticket_obj) if ticket_obj else None
    
    return {"history": history_event, "vehicle": vehicle, "ticket": ticket}

# ==================== Pre-load AI Models ====================
@app.on_event("startup")
async def startup_event():
    print("[SERVER] 🚀 Đang khởi động, bắt đầu tải trước các mô hình AI...")
    try:
        PlateDetector._shared_models = _init_models()
        get_ocr()
        print("[SERVER] ✅ Tải file mô hình thành công. Bắt đầu làm nóng (warm-up)...")
        dummy_image = np.zeros((CAM_H, CAM_W, 3), dtype=np.uint8)
        yolo_model = PlateDetector._shared_models[1]
        with torch.no_grad():
            yolo_model.predict(dummy_image, verbose=False, imgsz=(CAM_H, CAM_W))
        print("[SERVER] 🔥 Tải và khởi động mô hình AI hoàn chỉnh! Máy chủ đã sẵn sàng.")
    except Exception as e:
        print(f"[SERVER] ❌ Lỗi nghiêm trọng khi tải hoặc làm nóng mô hình: {e}"); traceback.print_exc(); raise

# ==================== WebSocket camera ====================
@app.websocket("/ws/camera/{cam_id}")
async def camera_ws(ws: WebSocket, cam_id: int):
    if cam_id not in (0, 1):
        await ws.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    await ws.accept(); print(f"[SERVER] ✅ Client đã kết nối vào cam {cam_id}")
    is_out_gate = (cam_id == 1)
    detector = PlateDetector(db_manager, event_label="out" if is_out_gate else "in")
    while True:
        try:
            frame_bytes = await ws.receive_bytes(); arr = np.frombuffer(frame_bytes, dtype=np.uint8); frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if frame is None: continue
            meta = detector.process(frame)
            if is_out_gate and meta.get("plates"):
                for vehicle_data in meta["plates"]:
                    plate = vehicle_data.get("plate")
                    if not plate: continue
                    active_ticket = db_manager.get_active_ticket_by_plate(plate)
                    if active_ticket:
                        print(f"[SERVER] 🔎 Xe ra: {plate}, tìm thấy vé active. Gửi yêu cầu xác nhận về client.")
                        vehicle_info_obj = db_manager.get_vehicle_by_plate(plate)
                        meta.update({
                            "event": "checkout_request",
                            "ticket_data": {
                                **vars(active_ticket),
                                "vehicle": vars(vehicle_info_obj) if vehicle_info_obj else None,
                            },
                        })
                        break
            await ws.send_json(meta)
        except Exception as e:
            print(f"[SERVER] ⚠️ Lỗi trên cam {cam_id}: {e}"); traceback.print_exc(); break

# ==================== REST API ====================
class TicketChoice(BaseModel):
    car_id: str; plate: str; vehicle_type: str | None = None; ticket_type: str; vehicle_image_b64: str

@app.post("/api/ticket/choose")
async def choose_ticket(data: TicketChoice):
    try:
        if data.ticket_type not in VALID_TICKET_TYPES:
            raise HTTPException(status_code=422, detail="Loại vé không hợp lệ")
        active_ticket = db_manager.get_active_ticket_by_plate(data.plate)
        if active_ticket:
            if active_ticket.ticket_type == "monthly" and not is_monthly_ticket_valid(active_ticket.checkin_time):
                active_ticket.status = "expired"
                db_manager.update_ticket(active_ticket)
                active_ticket = None
            elif active_ticket.ticket_type == "monthly" and data.ticket_type == "monthly":
                history_in = History(
                    vehicle_id=active_ticket.vehicle_id,
                    plate=data.plate,
                    gate="Gate Cam 0",
                    event_type="in",
                    ticket_id=active_ticket.id,
                )
                db_manager.create_history_event(history_in)
                return {"status": "success", "ticket_id": active_ticket.id, "reused_monthly_ticket": True}
            else:
                raise HTTPException(status_code=409, detail=f"Xe {data.plate} đã có vé đang hoạt động")
        existing_vehicle_obj = db_manager.get_vehicle_by_plate(data.plate)
        if existing_vehicle_obj:
            vehicle_id = vars(existing_vehicle_obj).get('id')
        else:
            new_vehicle = Vehicle(id=str(uuid.uuid4()), plate=data.plate, vehicle_type=data.vehicle_type, license_plate_image=data.vehicle_image_b64)
            vehicle_id = db_manager.create_vehicle(new_vehicle)
        
        ticket_id = f"{ticket_prefix(data.ticket_type)}{uuid.uuid4().hex[:5].upper()}"; now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_ticket = Ticket(id=ticket_id, vehicle_id=vehicle_id, plate=data.plate, ticket_type=data.ticket_type, checkin_time=now_str, status="active")
        created_id = db_manager.create_ticket(new_ticket)
        history_in = History(vehicle_id=vehicle_id, plate=data.plate, gate="Gate Cam 0", event_type="in", ticket_id=created_id)
        db_manager.create_history_event(history_in); print(f"[SERVER] ✅ Đã tạo vé {created_id} và lịch sử vào cho xe {data.plate}")
        return {"status": "success", "ticket_id": created_id}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[SERVER] ❌ Lỗi khi tạo vé: {e}"); traceback.print_exc(); raise HTTPException(status_code=500, detail=f"Database error: {e}")

class CheckoutRequest(BaseModel):
    plate: str

@app.post("/api/ticket/checkout")
async def confirm_checkout(data: CheckoutRequest):
    try:
        active_ticket_obj = db_manager.get_active_ticket_by_plate(data.plate)
        if not active_ticket_obj: raise HTTPException(status_code=404, detail=f"Không tìm thấy vé đang hoạt động cho biển số {data.plate}")
        active_ticket = vars(active_ticket_obj); now = datetime.now()
        checkin_time = datetime.fromisoformat(active_ticket['checkin_time'])
        if active_ticket['ticket_type'] == 'monthly' and not is_monthly_ticket_valid(active_ticket['checkin_time'], now):
            active_ticket['status'] = 'expired'
            db_manager.update_ticket(Ticket(**active_ticket))
            raise HTTPException(status_code=410, detail=f"Vé tháng của xe {data.plate} đã hết hạn")
        if closes_on_checkout(active_ticket['ticket_type']):
            active_ticket['duration'] = max(0, int((now - checkin_time).total_seconds() / 60))
            active_ticket['checkout_time'] = now.strftime("%Y-%m-%d %H:%M:%S")
            active_ticket['status'] = 'closed'
            db_manager.update_ticket(Ticket(**active_ticket))
        history_out = History(vehicle_id=active_ticket['vehicle_id'], plate=data.plate, gate="Gate Cam 1", event_type="out", ticket_id=active_ticket['id'])
        db_manager.create_history_event(history_out)
        print(f"[SERVER] 📝 Đã ghi lịch sử ra cho xe {data.plate}")
        return {"status": "success", "detail": f"Xe {data.plate} đã được xác nhận ra.", "ticket_type": active_ticket['ticket_type']}
    except HTTPException:
        raise
    except (TypeError, ValueError) as e:
        print(f"[SERVER] ❌ Dữ liệu thời gian của vé không hợp lệ: {e}")
        raise HTTPException(status_code=500, detail="Dữ liệu thời gian của vé không hợp lệ") from e
    except Exception as e:
        print(f"[SERVER] ❌ Lỗi khi xác nhận xe ra: {e}"); traceback.print_exc(); raise HTTPException(status_code=500, detail=f"Server error: {e}")

@app.get("/api/history/latest")
async def get_latest_history():
    latest_in = db_manager.get_latest_history("in"); latest_out = db_manager.get_latest_history("out")
    return {"latest_in": _enrich_history(latest_in), "latest_out": _enrich_history(latest_out)}

@app.get("/api/history/recent")
async def get_recent_history(limit: int = 10):
    """Lấy về một danh sách các sự kiện lịch sử gần đây nhất."""
    recent_history_events = db_manager.get_recent_history(limit=limit)
    enriched_results = [_enrich_history(event) for event in recent_history_events]
    return enriched_results
