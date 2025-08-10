import tkinter as tk
from tkinter import ttk
from tkinter import Label
from tkinter import filedialog
from PIL import Image, ImageTk
from models.yolo.yoloPhoto import yoloDetectPhoto
from models.yolo.yoloRealTimeDetection import yoloRealTimeModelDetect, stopCamera
from models.faster_rcnn.fasterRcnnPhoto import fasterRcnnDetectPhoto
from models.faster_rcnn.fasterRcnnCamera import fasterRcnnRealTimeDetect
import os

def yoloPhotoDetection():
    fileTypes = [("Image files", "*.png;*.jpg;*.jpeg")]
    path = tk.filedialog.askopenfilename(filetypes=fileTypes)

    if len(path):
        detectionResult = yoloDetectPhoto(path)
        if detectionResult is None:
            image_label_yolo.config(image=empty_photo)
            detection_text_yolo.config(text="No car plate detected...", foreground="red")
            return
        img = Image.open(detectionResult[1])
        img = img.resize((460, 460), Image.LANCZOS)
        photo = ImageTk.PhotoImage(img)
        image_label_yolo.config(image=photo)
        image_label_yolo.image = photo
        detection_text_yolo.config(text=f"YOLO: {detectionResult[0]}")
    else:
        print("No file is chosen !! Please choose a file.")

def fasterRcnnPhotoDetection():
    fileTypes = [("Image files", "*.png;*.jpg;*.jpeg")]
    path = tk.filedialog.askopenfilename(filetypes=fileTypes)

    if len(path):
        detectionResult = fasterRcnnDetectPhoto(path)
        if detectionResult is None:
            image_label_faster_rcnn.config(image=empty_photo)
            detection_text_faster_rcnn.config(text="No car plate detected...", foreground="red")
            return
        img = Image.open(detectionResult[1])
        img = img.resize((460, 460), Image.LANCZOS)
        photo = ImageTk.PhotoImage(img)
        image_label_faster_rcnn.config(image=photo)
        image_label_faster_rcnn.image = photo
        detection_text_faster_rcnn.config(text=f"Faster R-CNN: {detectionResult[0]}")
    else:
        print("No file is chosen !! Please choose a file.")

def yoloRealTimeDetection():
    yoloRealTimeModelDetect(image_label_yolo_live, app, source=0)

def yoloVideoStreamDetection():
    fileTypes = [("Video files", "*.mp4;*.avi;*.mov")]
    path = tk.filedialog.askopenfilename(filetypes=fileTypes)
    if path:
        yoloRealTimeModelDetect(image_label_yolo_live, app, source=path)

def fasterRcnnRealTimeDetection():
    fasterRcnnRealTimeDetect(image_label_faster_rcnn_live, app)

def clear_displayed_content():
    image_label_yolo.config(image=empty_photo)
    image_label_faster_rcnn.config(image=empty_photo)
    image_label_yolo_live.config(image=empty_photo)
    image_label_faster_rcnn_live.config(image=empty_photo)
    detection_text_yolo.config(text="")
    detection_text_faster_rcnn.config(text="")

if __name__ == "__main__":
    app = tk.Tk()
    app.title("Car Plate Number Recognition System")
    app.geometry("1200x900")

    app.option_add("*Label*Background", "white")
    app.option_add("*Button*Background", "lightgreen")

    notebook = ttk.Notebook(app)

    yolo_frame = ttk.Frame(notebook)
    fasterRcnn_frame = ttk.Frame(notebook)
    yoloLive_frame = ttk.Frame(notebook)
    fasterRcnnLive_frame = ttk.Frame(notebook)

    notebook.add(yolo_frame, text="YOLO Photo")
    notebook.add(fasterRcnn_frame, text="Faster Rcnn Photo")
    notebook.add(yoloLive_frame, text="YOLO Live")
    notebook.add(fasterRcnnLive_frame, text="Faster Rcnn Live")

    notebook.bind("<<NotebookTabChanged>>", lambda event: clear_displayed_content())

    style = ttk.Style()
    style.configure("TNotebook.Tab", font=("Helvetica", 14), padding=[20, 10])

    instruction_text_yolo = tk.Label(yoloLive_frame, text="Click buttons to open Camera or stream Video", font=("Helvetica", 16))
    instruction_text_yolo.place(relx=0.5, rely=0.07, anchor=tk.CENTER)

    instruction_text_yolo1 = tk.Label(yolo_frame, text="Click on the button to upload image", font=("Helvetica", 16))
    instruction_text_yolo1.place(relx=0.5, rely=0.07, anchor=tk.CENTER)

    instruction_text_faster = tk.Label(fasterRcnnLive_frame, text="Click on the button to open Camera", font=("Helvetica", 16))
    instruction_text_faster.place(relx=0.5, rely=0.07, anchor=tk.CENTER)

    instruction_text_faster1 = tk.Label(fasterRcnn_frame, text="Click on the button to upload image", font=("Helvetica", 16))
    instruction_text_faster1.place(relx=0.5, rely=0.07, anchor=tk.CENTER)

    yolo_button1 = tk.Button(yolo_frame, text="Detect Image (YOLO)", command=yoloPhotoDetection, font=("Helvetica", 16), width=25, height=2)
    yolo_button1.place(relx=0.5, rely=0.15, anchor=tk.CENTER)
    
    fasterRcnn_button1 = tk.Button(fasterRcnn_frame, text="Detect Image (FasterRCNN)", command=fasterRcnnPhotoDetection, font=("Helvetica", 16), width=25, height=2)
    fasterRcnn_button1.place(relx=0.5, rely=0.15, anchor=tk.CENTER)

    yolo_button2 = tk.Button(yoloLive_frame, text="Live Detect (YOLO)", command=yoloRealTimeDetection, font=("Helvetica", 16), width=25, height=2)
    yolo_button2.place(relx=0.35, rely=0.15, anchor=tk.CENTER)

    yolo_stop_button = tk.Button(yoloLive_frame, text="Stop Camera", command=lambda: stopCamera(image_label_yolo_live, app), font=("Helvetica", 16), width=25, height=2, bg="red")
    yolo_stop_button.place(relx=0.65, rely=0.15, anchor=tk.CENTER)

    yolo_video_button = tk.Button(yoloLive_frame, text="Stream Video (YOLO)", command=yoloVideoStreamDetection, font=("Helvetica", 16), width=25, height=2)
    yolo_video_button.place(relx=0.5, rely=0.25, anchor=tk.CENTER)
    
    fasterRcnn_button2 = tk.Button(fasterRcnnLive_frame, text="Live Detect (FasterRCNN)", command=fasterRcnnRealTimeDetection, font=("Helvetica", 16), width=25, height=2)
    fasterRcnn_button2.place(relx=0.5, rely=0.15, anchor=tk.CENTER)

    image_label_yolo = tk.Label(yolo_frame)
    image_label_yolo.place(relx=0.5, rely=0.55, anchor=tk.CENTER)

    image_label_faster_rcnn = tk.Label(fasterRcnn_frame)
    image_label_faster_rcnn.place(relx=0.5, rely=0.55, anchor=tk.CENTER)

    image_label_yolo_live = tk.Label(yoloLive_frame)
    image_label_yolo_live.place(relx=0.5, rely=0.55, anchor=tk.CENTER)

    image_label_faster_rcnn_live = tk.Label(fasterRcnnLive_frame)
    image_label_faster_rcnn_live.place(relx=0.5, rely=0.55, anchor=tk.CENTER)

    detection_text_yolo = tk.Label(yolo_frame, font=("Helvetica", 16))
    detection_text_yolo.place(relx=0.5, rely=0.88, anchor=tk.CENTER)
    
    detection_text_faster_rcnn = tk.Label(fasterRcnn_frame, font=("Helvetica", 16))
    detection_text_faster_rcnn.place(relx=0.5, rely=0.88, anchor=tk.CENTER)

    empty_photo = ImageTk.PhotoImage(Image.new('RGB', (1, 1)))

    notebook.pack(fill="both", expand=True)

    app.mainloop()