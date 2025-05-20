from django.shortcuts import render
import requests
import cloudinary.uploader
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
import logging



def frontend_home(request):
    return render(request, "index.html")



"""
Django views for handling file uploads and video processing status.
Uploads images and videos to Cloudinary and communicates with FastAPI.
"""



logger = logging.getLogger(__name__)

@csrf_exempt
@require_POST
def upload_file(request):
    """
    Handle file uploads (images or videos), store in Cloudinary, and send to FastAPI.

    Args:
        request: HTTP request containing a file in request.FILES['file'].

    Returns:
        JsonResponse: For images, returns processing results; for videos, returns task_id.
    """
    file = request.FILES.get('file')
    if not file:
        logger.error("No file provided in upload request")
        return JsonResponse({'error': 'No file provided.'}, status=400)

    content_type = file.content_type
    logger.info(f"Uploading file with content type: {content_type}")

    try:
        cloudinary_response = cloudinary.uploader.upload(
            file,
            resource_type="auto",
            folder="pothole_detection"
        )
        file_url = cloudinary_response['secure_url']
        logger.info(f"Uploaded file to Cloudinary: {file_url}")
        #http://34.30.224.189:8000/predict-image/'
        if content_type.startswith('image/'):
            fastapi_url = 'http://34.31.170.251:8000/predict-image/'
            api_response = requests.post(
                fastapi_url,
                json={'image_url': file_url},
                timeout=30
            )
            if api_response.status_code == 200:
                image_result = api_response.json()
                logger.info("Image processed successfully by FastAPI")
                return JsonResponse({
                    'type': 'image',
                    'image_result': image_result
                })
            else:
                logger.error(f"Image processing failed: {api_response.text}")
                return JsonResponse({'error': 'Image processing failed on backend.'}, status=500)

        elif content_type.startswith('video/'):
            fastapi_url = 'http://34.31.170.251:8000/process-video/'
            api_response = requests.post(
                fastapi_url,
                json={'video_url': file_url},
                timeout=30
            )
            if api_response.status_code == 200:
                data = api_response.json()
                task_id = data.get('task_id')
                logger.info(f"Video processing started, task_id: {task_id}")
                return JsonResponse({
                    'type': 'video',
                    'task_id': task_id
                })
            else:
                logger.error(f"Video processing failed: {api_response.text}")
                return JsonResponse({'error': 'Video processing failed on backend.'}, status=500)
        else:
            logger.error(f"Unsupported file type: {content_type}")
            return JsonResponse({'error': 'Unsupported file type'}, status=400)

    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        return JsonResponse({'error': f'Upload failed: {str(e)}'}, status=500)

@require_GET
def video_status(request, task_id):
    """
    Retrieve video processing status by proxying to FastAPI.

    Args:
        request: HTTP GET request.
        task_id (str): Celery task ID.

    Returns:
        JsonResponse: Status and results from FastAPI.
    """
    logger.info(f"Checking video status for task_id: {task_id}")
    fastapi_url = f'http://34.31.170.251:8000/video-status/{task_id}'
    try:
        response = requests.get(fastapi_url, timeout=5)
        response.raise_for_status()
        data = response.json()
        logger.info(f"Video status retrieved: {data}")
        return JsonResponse(data)
    except requests.RequestException as e:
        logger.error(f"Failed to get video status: {str(e)}")
        return JsonResponse({'error': f'Failed to get status: {str(e)}'}, status=500)
