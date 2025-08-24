# FILE: main.py (FINAL VERSION - CORRECTED MONTHLY TICKET LOGIC)
# ----------------------------------------------------------------------
import cv2
import numpy as np
import uuid
from datetime import datetime
from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import torch
import traceback
import sqlite3

from server.database.database import init_db
from server.utils.fasterRcnnCamera import PlateDetector, _init_models, CAM_W, CAM_H
from server.utils.readLicensePlate import get_ocr
from server.database.database_manager import DatabaseManager, Vehicle, Ticket, History, Payment
from server.utils.pricing import calculate_price, MONTHLY_RATE

# ==================== App init ====================
app = FastAPI(title="SmartParking Server", version="1.0.0")
db_manager = DatabaseManager("server/database/parking.db")
init_db()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"]
)

# ==================== Helper Function (Tái sử dụng) ====================
def _enrich_history(history_event: dict | None):
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
        PlateDetector._shared_models = _init_models(); get_ocr()
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
                    active_ticket_obj = db_manager.get_active_ticket_by_plate(plate)
                    if active_ticket_obj:
                        print(f"[SERVER] 🔎 Xe ra: {plate}, tìm thấy vé active. Gửi yêu cầu xác nhận về client.")
                        vehicle_info_obj = db_manager.get_vehicle_by_plate(plate)
                        now = datetime.now(); cost = calculate_price(active_ticket_obj, now)
                        ticket_data = vars(active_ticket_obj); ticket_data["cost"] = cost
                        checkout_data = {"event": "checkout_request", "ticket_data": {**ticket_data, "vehicle": vars(vehicle_info_obj) if vehicle_info_obj else None}}
                        await ws.send_json(checkout_data); break
            await ws.send_json(meta)
        except Exception as e:
            print(f"[SERVER] ⚠️ Lỗi trên cam {cam_id}: {e}"); traceback.print_exc(); break

# ==================== REST API ====================

@app.get("/api/vehicle/status/{plate}")
async def get_vehicle_status(plate: str):
    monthly_ticket = db_manager.get_active_monthly_ticket_by_plate(plate)
    return {"is_monthly_active": monthly_ticket is not None}

class PlateRequest(BaseModel):
    plate: str

@app.post("/api/ticket/log_entry")
async def log_monthly_entry(data: PlateRequest):
    monthly_ticket = db_manager.get_active_monthly_ticket_by_plate(data.plate)
    if not monthly_ticket:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy vé tháng đang hoạt động cho biển số {data.plate}")
    
    history_in = History(vehicle_id=monthly_ticket.vehicle_id, plate=monthly_ticket.plate, gate="Gate Cam 0", camera_id=0, event_type="in", ticket_id=monthly_ticket.id)
    db_manager.create_history_event(history_in)
    print(f"[SERVER] ✅ Đã ghi nhận lịch sử vào cho xe vé tháng {data.plate}")
    return {"status": "success", "detail": f"Đã ghi nhận xe {data.plate} vào."}

class TicketChoice(BaseModel):
    car_id: str; plate: str; vehicle_type: Optional[str] = None; ticket_type: str; vehicle_image_b64: str

@app.post("/api/ticket/choose")
async def choose_ticket(data: TicketChoice):
    try:
        existing_vehicle = db_manager.get_vehicle_by_plate(data.plate)
        if existing_vehicle: vehicle_id = existing_vehicle.id
        else:
            new_vehicle = Vehicle(id=str(uuid.uuid4()), plate=data.plate, vehicle_type=data.vehicle_type, license_plate_image=data.vehicle_image_b64)
            vehicle_id = db_manager.create_vehicle(new_vehicle)
        
        ticket_id = f"T{str(uuid.uuid4().hex[:5]).upper()}"; now_str = datetime.now().isoformat()
        new_ticket = Ticket(id=ticket_id, vehicle_id=vehicle_id, plate=data.plate, ticket_type=data.ticket_type, checkin_time=now_str, status="active")
        created_id = db_manager.create_ticket(new_ticket)

        if data.ticket_type == "monthly":
            payment = Payment(ticket_id=created_id, amount=MONTHLY_RATE)
            db_manager.create_payment(payment)
            print(f"[SERVER] 💳 Đã ghi nhận thanh toán {MONTHLY_RATE}đ cho vé tháng {created_id}")

        history_in = History(vehicle_id=vehicle_id, plate=data.plate, gate="Gate Cam 0", camera_id=0, event_type="in", ticket_id=created_id)
        db_manager.create_history_event(history_in); print(f"[SERVER] ✅ Đã tạo vé {created_id} và lịch sử vào cho xe {data.plate}")
        return {"status": "success", "ticket_id": created_id}
    except Exception as e:
        print(f"[SERVER] ❌ Lỗi khi tạo vé: {e}"); traceback.print_exc(); raise HTTPException(status_code=500, detail=f"Database error: {e}")

class CheckoutRequest(BaseModel):
    plate: str

@app.post("/api/ticket/checkout")
async def confirm_checkout(data: CheckoutRequest):
    try:
        active_ticket_obj = db_manager.get_active_ticket_by_plate(data.plate)
        if not active_ticket_obj:
            raise HTTPException(status_code=404, detail=f"Không tìm thấy vé đang hoạt động cho biển số {data.plate}")

        # ✨ SỬA LỖI LOGIC VÉ THÁNG: Phân luồng xử lý tại đây
        # --------------------------------------------------------------------
        # Trường hợp 1: Đây là xe vé tháng
        if active_ticket_obj.ticket_type == 'monthly':
            # Chỉ cần ghi nhận lịch sử ra, KHÔNG thay đổi status của vé tháng
            history_out = History(
                vehicle_id=active_ticket_obj.vehicle_id,
                plate=data.plate,
                gate="Gate Cam 1",
                camera_id=1,
                event_type="out",
                ticket_id=active_ticket_obj.id
            )
            db_manager.create_history_event(history_out)
            print(f"[SERVER] 📝 Đã ghi nhận lịch sử ra cho xe vé tháng {data.plate}. Vé tháng vẫn active.")
            return {"status": "success", "detail": f"Xe vé tháng {data.plate} đã được xác nhận ra."}
        
        # --------------------------------------------------------------------
        # Trường hợp 2: Đây là xe vé lượt (hourly, daily, etc.)
        else:
            now = datetime.now()
            final_cost = calculate_price(active_ticket_obj, now)
            if active_ticket_obj.ticket_type == "hourly" and final_cost > 0:
                payment = Payment(ticket_id=active_ticket_obj.id, amount=final_cost)
                db_manager.create_payment(payment)
                print(f"[SERVER] 💳 Đã ghi nhận thanh toán {final_cost}đ cho vé lượt {active_ticket_obj.id}")

            # Đóng vé lượt này lại
            active_ticket = vars(active_ticket_obj)
            checkin_time = datetime.fromisoformat(active_ticket['checkin_time'])
            active_ticket['duration'] = int((now - checkin_time).total_seconds() / 60)
            active_ticket['checkout_time'] = now.isoformat()
            active_ticket['status'] = 'closed' # << Quan trọng: Chỉ đóng vé lượt
            
            ticket_to_update = Ticket(**active_ticket)
            db_manager.update_ticket(ticket_to_update)
            
            # Ghi lịch sử ra
            history_out = History(
                vehicle_id=active_ticket['vehicle_id'],
                plate=data.plate,
                gate="Gate Cam 1",
                camera_id=1,
                event_type="out",
                ticket_id=active_ticket['id']
            )
            db_manager.create_history_event(history_out)
            print(f"[SERVER] 📝 Đã đóng vé lượt và ghi lịch sử ra cho xe {data.plate}")
            
            return {"status": "success", "detail": f"Xe {data.plate} đã được xác nhận ra."}
        # --------------------------------------------------------------------

    except Exception as e:
        print(f"[SERVER] ❌ Lỗi khi xác nhận xe ra: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Server error: {e}")

@app.get("/api/history/latest")
async def get_latest_history():
    latest_in = db_manager.get_latest_history("in"); latest_out = db_manager.get_latest_history("out")
    return {"latest_in": _enrich_history(latest_in), "latest_out": _enrich_history(latest_out)}

@app.get("/api/history/recent")
async def get_recent_history(limit: int = 10):
    recent_history_events = db_manager.get_recent_history(limit=limit)
    enriched_results = [_enrich_history(event) for event in recent_history_events]
    return enriched_results