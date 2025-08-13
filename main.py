import tkinter as tk
from threading import Thread
import queue
from PIL import Image, ImageTk
import cv2
from models.faster_rcnn.fasterRcnnCamera import fasterRcnnRealTimeDetectIn, fasterRcnnRealTimeDetectOut

# Queue để nhận frame từ thread camera
queue_in = queue.Queue(maxsize=1)
queue_out = queue.Queue(maxsize=1)

app = tk.Tk()
app.title("Car Plate Recognition - Dual Camera")
app.geometry("1400x700")
app.configure(bg="white")

# Layout
left_frame = tk.Frame(app, bg="white")
left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
right_frame = tk.Frame(app, bg="white")
right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

# Tiêu đề
tk.Label(left_frame, text="Camera Vào", font=("Helvetica", 20), bg="white").pack()
tk.Label(right_frame, text="Camera Ra", font=("Helvetica", 20), bg="white").pack()

# Label hiển thị video
video_label_in = tk.Label(left_frame, bg="black")
video_label_in.pack(fill=tk.BOTH, expand=True)
video_label_out = tk.Label(right_frame, bg="black")
video_label_out.pack(fill=tk.BOTH, expand=True)

def update_label_from_queue(label, frame_queue):
    try:
        frame = frame_queue.get_nowait()
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        imgtk = ImageTk.PhotoImage(image=Image.fromarray(frame_rgb))
        label.imgtk = imgtk
        label.configure(image=imgtk)
    except queue.Empty:
        pass
    label.after(20, update_label_from_queue, label, frame_queue)  # gọi lại sau 20ms

# Bắt đầu luồng camera
Thread(target=fasterRcnnRealTimeDetectIn, args=(queue_in,), daemon=True).start()
Thread(target=fasterRcnnRealTimeDetectOut, args=(queue_out,), daemon=True).start()

# Bắt đầu cập nhật label
update_label_from_queue(video_label_in, queue_in)
update_label_from_queue(video_label_out, queue_out)

app.mainloop()
