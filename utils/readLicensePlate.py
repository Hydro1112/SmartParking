import easyocr
import cv2

reader = easyocr.Reader(['en'], gpu=True)

def readLicensePlate (img,x1,y1,x2,y2) :

    img.shape[0]

    # crop license plate
    if (x1 - 3) >= 0:
        newx1 = int(x1 - 3)
    else:
        newx1 = 0

    if (y1 - 3) >= 0:
        newy1 = int(y1 - 3)
    else:
        newy1 = 0

    if (x2 + 3) <= img.shape[1]:
        newx2 = int(x2 + 3)
    else:
        newx2 = img.shape[1]

    if (y2 + 3) <= img.shape[0]:
        newy2 = int(y2 + 3)
    else:
        newy2 = img.shape[0]

    # crop out the license plate
    license_plate_crop = img[newy1:newy2, newx1: newx2]
    # process license plate
    license_plate_crop_gray = cv2.cvtColor(license_plate_crop, cv2.COLOR_BGR2GRAY)
    license_plate_inverted = cv2.bitwise_not(license_plate_crop_gray)
   # run easyocr
    license_plate_detections = reader.readtext(license_plate_inverted)
    license_plate_text = ' '
    totalScore = 0.0
    numOfDetection = 0
    confScore = 0.0
    if(len(license_plate_detections)>0):
        license_plate_text = ''
        textArray = []
        for detection in license_plate_detections:
            bbox, texts, score = detection
            texts = texts.upper().replace(' ', '')
            totalScore += score
            numOfDetection +=1
            print(texts)
            print(score)
            textArray.append(texts)

        while(len(textArray)!=0):
           for texts in textArray:
               if len(texts) > 0 and texts[0].isalpha():
                   for text in texts:
                       license_plate_text+=text
                   textArray.remove(texts)

           for texts in textArray:
                   for text in texts:
                       license_plate_text+=text
                   textArray.remove(texts)
        for text in license_plate_text:
            if (text.isdigit()==False and text.isalpha()==False):
                license_plate_text =""
                confScore = 0.0
                return [license_plate_text, confScore]

        if license_plate_text[0].isdigit():
            license_plate_text = ""
            confScore = 0.0
            return [license_plate_text, confScore]

        confScore = totalScore/numOfDetection

    return [license_plate_text,confScore]
