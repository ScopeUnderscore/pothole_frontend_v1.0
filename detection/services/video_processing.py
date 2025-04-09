import requests
import base64
import os
import tempfile
import cloudinary.uploader
from django.conf import settings
from urllib.parse import urlparse

# Configure your FastAPI endpoint
FASTAPI_ENDPOINT = getattr(settings, "FASTAPI_ENDPOINT", "https://c404-34-105-3-144.ngrok-free.app")


def process_video(video_source):
    """
    Send a video to FastAPI server for processing,
    then upload the processed video to Cloudinary.

    Parameters:
    video_source -- Can be either a local file path or a URL
    """
    temp_file = None
    try:
        # Check if the video_source is a URL
        is_url = video_source.startswith(("http://", "https://"))

        if is_url:
            # Download the video to a temporary file
            temp_file = os.path.join(tempfile.gettempdir(), "temp_input_video.mp4")
            print(f"Downloading video from URL: {video_source}")

            response = requests.get(video_source, stream=True)
            response.raise_for_status()

            with open(temp_file, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            video_path = temp_file
        else:
            # It's already a local path
            video_path = video_source

        # Now proceed with the regular processing
        with open(video_path, "rb") as video_file:
            files = {"file": (os.path.basename(video_path), video_file, "video/mp4")}

            # Send to FastAPI server
            response = requests.post(f"{FASTAPI_ENDPOINT}/process-video/", files=files)
            response.raise_for_status()
            result = response.json()

            # Process the response
            video_data = result.get("video_base64")
            if video_data:
                # Save processed video temporarily
                processed_video_path = os.path.join(
                    tempfile.gettempdir(), "temp_processed_video.mp4"
                )
                videodata = base64.b64decode(video_data)
                with open(processed_video_path, "wb") as f:
                    f.write(videodata)

                # Upload to Cloudinary
                upload_result = cloudinary.uploader.upload(
                    processed_video_path,
                    resource_type="video",
                    folder="pothole_videos",
                    format="mp4",
                    eager=[{"format": "mp4"}],
                    eager_async=True,
                )
                cloudinary_url = upload_result.get("secure_url", None)

                # Clean up temporary files
                if os.path.exists(processed_video_path):
                    os.remove(processed_video_path)

                # Return results
                return {
                    "average_severity": result.get("average_severity", 0.0),
                    "damaged_road_percentage": result.get(
                        "damaged_road_percentage", 0.0
                    ),
                    "video_url": cloudinary_url,
                    "total_potholes_detected": result.get("total_potholes_detected", 0),
                }

            return {"error": "No processed video received from API"}

    except requests.exceptions.RequestException as e:
        print(f"Error communicating with FastAPI server: {str(e)}")
        return {"error": f"Failed to process video: {str(e)}"}
    except Exception as e:
        print(f"Unexpected error in video processing: {str(e)}")
        return {"error": f"Failed to process video: {str(e)}"}
    finally:
        # Always clean up temporary files
        if temp_file and os.path.exists(temp_file):
            os.remove(temp_file)
