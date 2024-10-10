import cv2
import multiprocessing as multiprocessing
import numpy as np
import os
from openpyxl import Workbook
import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox

def analyzePhotoPart(arguments):
    imagePart, partIndex, imageName, offsetX, offsetY = arguments
    
    grayImage = cv2.cvtColor(imagePart, cv2.COLOR_BGR2GRAY)
    blurredImage = cv2.GaussianBlur(grayImage, (5, 5), 0)
    _, binaryImage = cv2.threshold(blurredImage, 180, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(binaryImage, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    objectsData = []
    contourCenters = []

    for contour in contours:
        contourArea = cv2.contourArea(contour)
        x, y, contourWidth, contourHeight = cv2.boundingRect(contour)
        centerX = x + contourWidth // 2 + offsetX
        centerY = y + contourHeight // 2 + offsetY
        
        brightness = np.sum(grayImage[y:y + contourHeight, x:x + contourWidth])
        objectType = classification(contourArea, brightness)
        
        if objectType != "-":
            objectsData.append({
                "image": imageName,
                "partIndex": partIndex + 1,
                "coordinates": (centerX, centerY),
                "brightness": brightness,
                "area": int(contourArea),
                "type": objectType
            })
            
            contourCenters.append((centerX - offsetX, centerY - offsetY, max(contourWidth, contourHeight) // 2, objectType))

    return objectsData, contourCenters

def classification(area, brightness):
    if area < 300 and brightness > 200:
        return "Star"
    elif area > 300 and brightness > 1000:
        return "A bright star"
    elif area > 300 and brightness < 200:
        return "Planet"
    else:
        return "Star"

def processAllImages(inputDirectory, outputXLSXPath, outputImageDir):
    allResults = []

    for imageName in os.listdir(inputDirectory):
        imagePath = os.path.join(inputDirectory, imageName)
        if imagePath.lower().endswith(('.png', '.jpg')):
            objectsData = processImage(imagePath, outputImageDir)
            allResults.extend(objectsData)

    save(allResults, outputXLSXPath)
    print(f"Analysis complete. Results saved to {outputXLSXPath}")

def save(data, outputXLSXPath):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Results"
    
    headers = ['Image', 'PartIndex', 'Coordinates', 'Brightness', 'Area', 'Type']
    sheet.append(headers)

    for objectData in data:
        sheet.append([ 
            objectData['image'],
            objectData['partIndex'],
            f"{objectData['coordinates'][0]}, {objectData['coordinates'][1]}",
            objectData['brightness'],
            objectData['area'],
            objectData['type']
        ])

    for column in sheet.columns:
        max_length = 0
        column = [cell for cell in column]
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = (max_length + 2)
        sheet.column_dimensions[column[0].column_letter].width = adjusted_width

    workbook.save(outputXLSXPath)

def processImage(imagePath, outputImageDir):
    image = cv2.imread(imagePath)
    imageName = os.path.basename(imagePath)
    
    imageOutputDir = os.path.join(outputImageDir, os.path.splitext(imageName)[0])
    os.makedirs(imageOutputDir, exist_ok=True)
    
    imageParts = splitImage(image, 1000)

    arguments = [(part, partIndex, imageName, offsetX, offsetY) 
                 for part, offsetX, offsetY, partIndex in imageParts]
    
    with multiprocessing.Pool(processes=16) as processPool:
        results = processPool.map(analyzePhotoPart, arguments)

    allObjectsData = []
    for objectData, contourCenters in results:  # Теперь возвращаются и данные объектов, и контуры
        allObjectsData.extend(objectData)

    for (part, offsetX, offsetY, partIndex), (_, contourCenters) in zip(imageParts, results):
        saveImagePart(part, partIndex, imageName, imageOutputDir, contourCenters)

    return allObjectsData

def splitImage(image, partSize):
    imageHeight, imageWidth, _ = image.shape
    imageParts = []
    
    partIndex = 0
    for offsetY in range(0, imageHeight, partSize):
        for offsetX in range(0, imageWidth, partSize):
            part = image[offsetY:offsetY + partSize, offsetX:offsetX + partSize]
            if part.size > 0:
                imageParts.append((part, offsetX, offsetY, partIndex))
            partIndex += 1

    return imageParts

def saveImagePart(part, partIndex, imageName, outputDir, contourCenters):
    for (centerX, centerY, radius, objectType) in contourCenters:
        largerRadius = int(radius * 1.5)
        
        if objectType == "Star":
            color = (255, 0, 0)
        elif objectType == "Planet":
            color = (0, 0, 255)
        elif objectType == "A bright star":
            color = (0, 255, 0)

        cv2.circle(part, (centerX, centerY), largerRadius, color, 4)

    partImageName = f"{partIndex + 1}.png"
    partImagePath = os.path.join(outputDir, partImageName)
    cv2.imwrite(partImagePath, part)

def analyze():
    global inputDirectory, outputXLSXPath, outputImageDir
    if not inputDirectory:
        inputDirectory = 'photo'
    
    if not outputXLSXPath:
        outputXLSXPath = os.path.join(os.getcwd(), 'statistic.xlsx')

    outputImageDir = 'image_parts'
    os.makedirs(outputImageDir, exist_ok=True)

    processAllImages(inputDirectory, outputXLSXPath, outputImageDir)

    messagebox.showinfo("Анализ завершен", f"Результаты сохранены в {outputXLSXPath}")

def chooseImages():
    global inputDirectory
    inputDirectory = filedialog.askdirectory()
    if inputDirectory:
        label_selected_images.config(text=f"Выбраны изображения: {inputDirectory}")

def savePath():
    global outputXLSXPath
    output_directory = filedialog.askdirectory()
    if output_directory:
        outputXLSXPath = os.path.join(output_directory, 'statistic.xlsx')
        label_save_path.config(text=f"Сохранить в: {outputXLSXPath}")

def create_interface():
    global btn_analyze, label_selected_images, label_save_path
    
    root = tk.Tk()
    root.title("Анализ космических данных")

    window_width = 400
    window_height = 120
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width // 2) - (window_width // 2)
    y = (screen_height // 2) - (window_height // 2)
    root.geometry(f"{window_width}x{window_height}+{x}+{y}")

    label_selected_images = tk.Label(root, text="Выбраны изображения: None")
    label_selected_images.pack(pady=5)

    label_save_path = tk.Label(root, text="Сохранить в: None")
    label_save_path.pack(pady=5)

    button_frame = tk.Frame(root)
    button_frame.pack(pady=5)

    btn_choose_images = tk.Button(button_frame, text="Выбрать изображения", command=chooseImages)
    btn_choose_images.pack(side=tk.LEFT, padx=5)

    btn_save_path = tk.Button(button_frame, text="Сохранить путь", command=savePath)
    btn_save_path.pack(side=tk.LEFT, padx=5)

    btn_analyze = tk.Button(button_frame, text="Анализ", command=analyze)
    btn_analyze.pack(side=tk.LEFT, padx=5)

    return root

if __name__ == "__main__":
    inputDirectory = ''
    outputXLSXPath = ''
    outputImageDir = ''

    root = create_interface()
    root.mainloop()
