import torch
import os
from ultralytics import YOLO



# model path 
MODEL_PATH = os.path.join(os.path.dirname(__file__), "../../model_s/best.pt")


# Use MPS for Apple Silicon if available, else fallback to CPU
device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")

# Load YOLO model 
model = YOLO(MODEL_PATH)  # Load the entire YOLO model

# Move model to appropriate device
model.to(device)

# Set model to evaluation mode
model.eval()







# def predict_pothole(image_path, output_path):
#     """
#     Runs the YOLOv11 model on an image and returns:
#     - Masked image highlighting potholes
#     - Severity percentage
#     - Bounding boxes (optional)
#     """
#     img = cv2.imread(image_path)
#     results = model(img)

#     # Extract segmentation masks
#     masks = results.pred[0][:, 6:] if len(results.pred[0]) > 0 else None
#     mask = masks[0].cpu().numpy() if masks is not None and len(masks) > 0 else None

#     # Compute severity percentage
#     total_area = img.shape[0] * img.shape[1]
#     pothole_area = np.sum(mask > 0) if mask is not None else 0
#     severity_percentage = (pothole_area / total_area) * 100 if total_area > 0 else 0

#     # Generate masked image
#     if mask is not None:
#         mask = (mask * 255).astype(np.uint8)  # Convert to grayscale
#         colored_mask = cv2.applyColorMap(mask, cv2.COLORMAP_JET)  # Apply color map
#         masked_img = cv2.addWeighted(img, 0.6, colored_mask, 0.4, 0)  # Overlay mask

#         # Add severity percentage text to image
#         text = f"Pothole Damage: {severity_percentage:.2f}%"
#         cv2.putText(masked_img, text, (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
#         cv2.imwrite(output_path, masked_img)
#     else:
#         cv2.imwrite(output_path, img)  # Return original image if no pothole found

#     return {
#         "severity": severity_percentage,
#         "image_path": output_path  # Path to the saved masked image
#     }
 