import os
import requests
import cloudinary.uploader
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.http import JsonResponse
from .services.image_processing import predict_pothole
from .services.video_processing import process_video

class PotholeDetectionView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        if "file" not in request.FILES:
            return Response({"error": "No file uploaded"}, status=400)

        file_obj = request.FILES["file"]
        file_name = file_obj.name.replace(" ", "_")  # Remove spaces
        file_ext = os.path.splitext(file_name)[1].lower()

        # **Image Processing**
        if file_ext in [".jpg", ".jpeg", ".png"]:
            print("Image Upload Detected")  # Debugging
            upload_result = cloudinary.uploader.upload(
                file_obj, folder="pothole_images"
            )
            cloudinary_url = upload_result.get("secure_url", None)
            print(f"Cloudinary Image URL: {cloudinary_url}")

            if not cloudinary_url:
                return JsonResponse({"error": "Failed to upload image"}, status=500)

            # Run pothole detection
            result = predict_pothole(cloudinary_url)
            print(f" Detection Result: {result}")

            return JsonResponse(
                               {
                    "severity": result.get("severity", 0),
                    "image_url": result.get("image_url"),  #  returns Cloudinary URL
                    "objects": "Pothole" if result.get("severity", 0) > 0 else "No pothole",
                }

            )

        # **Video Processing**
        elif file_ext in [".mp4", ".avi", ".mov"]:
            print("Video Upload Detected")  # Debugging
            
            #upload to cloudinary
            upload_result = cloudinary.uploader.upload(
                file_obj, resource_type="video", folder="pothole_videos"
            )
            video_url = upload_result.get("secure_url", None)
            print(f"Cloudinary Video URL: {video_url}")

            if not video_url:
                return JsonResponse({"error": "Failed to upload video"}, status=500)
            

            #  Send Cloudinary URL to your FastAPI backend
         
            try:
                video_result = process_video(video_url)
                
                print(f"Video Processing Result: {video_result}")
                
                return JsonResponse(
                    {"severity": video_result.get("damage_percentage", 0),
                    "video_url": video_result.get("processed_video_path", video_url),
                    "objects": "Potholes"
                    if video_result.get("damage_percentage", 0) > 0
                    else "No pothole detected",}
                )
            except Exception as e:
                print(f"Error processing video: {e}")
                return JsonResponse({"error": "Video processing failed"}, status=500)

                    
            
            
            
            
            
            # video_result = process_video(video_url)
            # print(f" Video Processing Result: {video_result}")

            # return JsonResponse(
            #     {
            #         "severity": video_result.get("average_severity", 0),
            #         "video_url": video_result.get("video_url", video_url),
            #         "objects": "Potholes"
            #         if video_result.get("average_severity", 0) > 0
            #         else "No pothole detected",
            #     }
            # )

        else:
            print("Unsupported File Format")
            return Response({"error": "Unsupported file format"}, status=400)
