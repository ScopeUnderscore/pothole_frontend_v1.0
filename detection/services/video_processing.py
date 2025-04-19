import requests
import base64
import os
import tempfile
import cloudinary.uploader
from django.conf import settings
from urllib.parse import urlparse

import requests
from django.conf import settings

# FastAPI endpoint from settings or fallback
FASTAPI_ENDPOINT = getattr(settings, "FASTAPI_ENDPOINT", "https://17dc-34-44-90-93.ngrok-free.app")


def process_video(cloudinary_video_url):
    """
    Send the Cloudinary video URL directly to FastAPI for processing.
    FastAPI will handle downloading and inference.

    Parameters:
    cloudinary_video_url -- Direct URL to the uploaded video in Cloudinary.
    """

    try:
        # payload = {"video_url": cloudinary_video_url}
        response = requests.post(
        FASTAPI_ENDPOINT,
        json={"video_url": cloudinary_video_url}, 
        timeout=60  # Optional, good for long processing
    )
        print(f"fastapi endpoint response:{response}")
        response.raise_for_status()
        result = response.json()

        # Check if FastAPI returned expected data
        if "video_base64" in result:
            # Upload the returned processed video to Cloudinary
            import base64, tempfile, cloudinary.uploader, os

            video_data = base64.b64decode(result["video_base64"])
            processed_path = os.path.join(tempfile.gettempdir(), "processed_video.mp4")

            with open(processed_path, "wb") as f:
                f.write(video_data)

            upload_result = cloudinary.uploader.upload(
                processed_path,
                resource_type="video",
                folder="pothole_videos",
                format="mp4",
                eager=[{"format": "mp4"}],
                eager_async=True,
            )

            # Clean up
            os.remove(processed_path)

            return {
                "average_severity": result.get("average_severity", 0.0),
                "damaged_road_percentage": result.get("damaged_road_percentage", 0.0),
                "total_potholes_detected": result.get("total_potholes_detected", 0),
                "video_url": upload_result.get("secure_url"),
            }

        return {"error": "No processed video received from FastAPI"}

    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
        return {"error": f"Failed to connect to FastAPI: {str(e)}"}
    except Exception as e:
        print(f"Unexpected error: {e}")
        return {"error": f"Video processing failed: {str(e)}"}
