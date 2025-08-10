import tkinter as tk
from tkinter import ttk
from tkinter import Label
from tkinter import filedialog
from PIL import Image, ImageTk
from models.faster_rcnn.fasterRcnnPhoto import fasterRcnnDetectPhoto
from models.faster_rcnn.fasterRcnnCamera import fasterRcnnRealTimeDetect
import os

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
        
def fasterRcnnRealTimeDetection():
    fasterRcnnRealTimeDetect(image_label_faster_rcnn_live, app)

def clear_displayed_content():
    image_label_faster_rcnn.config(image=empty_photo)
    image_label_faster_rcnn_live.config(image=empty_photo)
    detection_text_faster_rcnn.config(text="")

if __name__ == "__main__":
    app = tk.Tk()
    app.title("Car Plate Number Recognition System")
    app.geometry("1200x900")

    app.option_add("*Label*Background", "white")
    app.option_add("*Button*Background", "lightgreen")

    notebook = ttk.Notebook(app)


    fasterRcnn_frame = ttk.Frame(notebook)
    fasterRcnnLive_frame = ttk.Frame(notebook)

    notebook.add(fasterRcnn_frame, text="Faster Rcnn Photo")
    notebook.add(fasterRcnnLive_frame, text="Faster Rcnn Live")

    notebook.bind("<<NotebookTabChanged>>", lambda event: clear_displayed_content())

    style = ttk.Style()
    style.configure("TNotebook.Tab", font=("Helvetica", 14), padding=[20, 10])

    instruction_text_faster = tk.Label(fasterRcnnLive_frame, text="Click on the button to open Camera", font=("Helvetica", 16))
    instruction_text_faster.place(relx=0.5, rely=0.07, anchor=tk.CENTER)

    instruction_text_faster1 = tk.Label(fasterRcnn_frame, text="Click on the button to upload image", font=("Helvetica", 16))
    instruction_text_faster1.place(relx=0.5, rely=0.07, anchor=tk.CENTER)

    fasterRcnn_button1 = tk.Button(fasterRcnn_frame, text="Detect Image (FasterRCNN)", command=fasterRcnnPhotoDetection, font=("Helvetica", 16), width=25, height=2)
    fasterRcnn_button1.place(relx=0.5, rely=0.15, anchor=tk.CENTER)

    fasterRcnn_button2 = tk.Button(fasterRcnnLive_frame, text="Live Detect (FasterRCNN)", command=fasterRcnnRealTimeDetection, font=("Helvetica", 16), width=25, height=2)
    fasterRcnn_button2.place(relx=0.5, rely=0.15, anchor=tk.CENTER)

    image_label_faster_rcnn = tk.Label(fasterRcnn_frame)
    image_label_faster_rcnn.place(relx=0.5, rely=0.55, anchor=tk.CENTER)

    image_label_faster_rcnn_live = tk.Label(fasterRcnnLive_frame)
    image_label_faster_rcnn_live.place(relx=0.5, rely=0.55, anchor=tk.CENTER)
    
    detection_text_faster_rcnn = tk.Label(fasterRcnn_frame, font=("Helvetica", 16))
    detection_text_faster_rcnn.place(relx=0.5, rely=0.88, anchor=tk.CENTER)

    empty_photo = ImageTk.PhotoImage(Image.new('RGB', (1, 1)))

    notebook.pack(fill="both", expand=True)

    app.mainloop()