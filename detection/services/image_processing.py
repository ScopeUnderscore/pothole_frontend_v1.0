import requests
import base64
import cloudinary.uploader
from django.conf import settings

# Configure your FastAPI endpoint - this would be the ngrok URL from Colab
FASTAPI_ENDPOINT = getattr(settings, 'FASTAPI_ENDPOINT', 'https://716a-104-196-44-117.ngrok-free.app')


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
    Downloads an image from a URL, sends it to FastAPI server for processing,
    and uploads the processed image to Cloudinary.
    """
    # Step 1: Download Image
    local_image_path = download_image(image_url)
    if local_image_path is None:
        return {"error": "Failed to download image"}
    
    # Step 2: Convert image to base64
    with open(local_image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
    
    # Step 3: Send to FastAPI server
    try:
        response = requests.post(
            f"{FASTAPI_ENDPOINT}/predict-image/", 
            data={"image_base64": encoded_string}
        )
        response.raise_for_status()  # Raise error for bad responses
        result = response.json()
        
        # If no pothole detected, return early
        if not result.get("pothole_detected", False):
            return {
                "pothole_detected": False,
                "severity": 0.0,
                "image_url": None,
                "detections": [],
            }
        
        # Step 4: Save processed image from base64
        image_data = result.get("image_base64")
        if image_data:
            # Decode base64 and save locally
            processed_image_path = "processed_pothole.jpg"
            imgdata = base64.b64decode(image_data)
            with open(processed_image_path, 'wb') as f:
                f.write(imgdata)
            
            # Step 5: Upload to Cloudinary
            upload_result = cloudinary.uploader.upload(
                processed_image_path, folder="pothole_images"
            )
            cloudinary_url = upload_result.get("secure_url", None)
            
            # Return results with Cloudinary URL
            return {
                "pothole_detected": result.get("pothole_detected", False),
                "severity": result.get("severity", 0.0),
                "image_url": cloudinary_url,
                "detections": result.get("detections", []),
            }
    except requests.exceptions.RequestException as e:
        print(f"Error communicating with FastAPI server: {str(e)}")
        return {"error": f"Failed to process image: {str(e)}"}
    
    # Fallback response
    return {"error": "Failed to process image"}