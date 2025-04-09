import cv2
import numpy as np
import requests
import cloudinary.uploader
from .model_loader import model


def download_image(url, save_path="temp_pothole.jpg"):
    """Download an image from a URL and save it locally."""
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        with open(save_path, "wb") as f:
            for chunk in response.iter_content(1024):
                f.write(chunk)
        return save_path  # Return local file path
    else:
        print(f"Error: Unable to download image from {url}")
        return None


def predict_pothole(image_url):
    """
    Downloads an image from a URL, runs the YOLOv11 model,
    and uploads the processed image to Cloudinary.
    """
    # **Step 1: Download Image**
    local_image_path = download_image(image_url)
    if local_image_path is None:
        return {"error": "Failed to download image"}

    img = cv2.imread(local_image_path)
    if img is None:
        return {"error": "Failed to read image after download"}

    # **Step 2: Perform inference using YOLO model**
    results_list = model.predict(img)

    if not results_list or results_list[0].masks is None:  # No detections
        return {
            "pothole_detected": False,
            "severity": 0.0,
            "image_url": None,
            "detections": [],
        }

    results = results_list[0]  # Extract first result
    masks = results.masks.data.cpu().numpy()  # Get segmentation masks
    confidences = results.boxes.conf.cpu().numpy()  # Get confidence scores

    # **Step 3: Compute Image Area**
    image_height, image_width, _ = img.shape
    image_area = image_height * image_width

    # **Step 4: Initialize mask and area storage**
    total_pothole_area = 0
    pothole_areas = []
    combined_mask = np.zeros((image_height, image_width), dtype=np.uint8)  # Accumulate all pothole masks
    pothole_detections = []

    for i, (mask, confidence) in enumerate(zip(masks, confidences)):
        pothole_number = i + 1  # Assign a unique number to each pothole
        binary_mask = (mask > 0).astype(np.uint8) * 255  # Convert mask to binary
        combined_mask = cv2.bitwise_or(combined_mask, binary_mask)  # Merge masks

        contours, _ = cv2.findContours(
            binary_mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
        )

        if len(contours) == 0:
            print(f"Warning: No contours found for pothole {pothole_number}")
            continue  # Skip this mask

        # Get the largest contour area (for pothole)
        contour = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(contour)
        total_pothole_area += area

        # Compute Pothole Percentage
        pothole_percentage = (area / image_area) * 100
        pothole_areas.append(f"Pothole {pothole_number}: {pothole_percentage:.2f}%")

        # Store detection info
        pothole_detections.append({
            "pothole_number": pothole_number,
            "confidence": round(float(confidence), 2),
            "pothole_percentage": round(pothole_percentage, 2),
        })

        # **Step 5: Draw contours and assign a pothole number**
        cv2.drawContours(img, [contour], -1, (0, 255, 0), thickness=3)

        # Get bounding box for placing the pothole number
        x, y, w, h = cv2.boundingRect(contour)
        cv2.putText(
            img, str(pothole_number), (x + w // 2, y + h // 2),  # Place number inside pothole
            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2
        )

    # **Step 6: Compute severity percentage**
    severity_percentage = (total_pothole_area / image_area) * 100 if image_area > 0 else 0

    # **Step 7: Overlay segmentation mask (Now covering all potholes)**
    colored_mask = cv2.applyColorMap(combined_mask, cv2.COLORMAP_JET)
    masked_img = cv2.addWeighted(img, 0.6, colored_mask, 0.4, 0)

    # **Step 8: Display Summary Labels at the Top-Left (No Black Background)**
    summary_text = f"Total Damage: {severity_percentage:.2f}%"
    
    # Draw white text with black shadow for visibility
    cv2.putText(masked_img, summary_text, (15, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 3)  # Shadow
    cv2.putText(masked_img, summary_text, (15, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)  # Main Text

    # Display individual pothole percentages below the total
    y_offset = 60
    for pothole_info in pothole_areas:
        cv2.putText(masked_img, pothole_info, (15, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 3)  # Shadow
        cv2.putText(masked_img, pothole_info, (15, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)  # Main Text
        y_offset += 20

    # **Step 9: Save processed image**
    processed_image_path = "processed_pothole.jpg"
    cv2.imwrite(processed_image_path, masked_img)

    # **Step 10: Upload to Cloudinary**
    upload_result = cloudinary.uploader.upload(
        processed_image_path, folder="pothole_images"
    )
    cloudinary_url = upload_result.get("secure_url", None)

    return {
        "pothole_detected": True,
        "severity": round(severity_percentage, 2),
        "image_url": cloudinary_url,  # Processed image URL
        "detections": pothole_detections,  # Confidence scores and pothole percentages
    }
