import cv2
import numpy as np
import cloudinary.uploader
from .model_loader import model
import os


def process_video(video_path):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Unable to open video file {video_path}")
        return {"error": "Unable to open video file"}

    width, height = (
        int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
    )
    fps = cap.get(cv2.CAP_PROP_FPS)

    temp_output_path = "temp_pothole_video.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(temp_output_path, fourcc, fps, (width, height))

    frame_count = 0
    total_severity = 0
    unique_potholes = set()

    global_road_mask = np.zeros(
        (height, width), dtype=np.uint8
    )  # Store total visible road
    global_pothole_mask = np.zeros(
        (height, width), dtype=np.uint8
    )  # Store all potholes

    orb = cv2.ORB_create(500)
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    prev_frame_gray = None
    prev_kp = None
    prev_des = None

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        homography_matrix = None

        # Compute Homography
        if prev_frame_gray is not None:
            kp, des = orb.detectAndCompute(gray_frame, None)
            if kp and des is not None and prev_kp is not None and prev_des is not None:
                matches = bf.match(des, prev_des)
                matches = sorted(matches, key=lambda x: x.distance)[:50]

                if len(matches) > 10:
                    src_pts = np.float32([kp[m.queryIdx].pt for m in matches]).reshape(
                        -1, 1, 2
                    )
                    dst_pts = np.float32(
                        [prev_kp[m.trainIdx].pt for m in matches]
                    ).reshape(-1, 1, 2)
                    homography_matrix, _ = cv2.findHomography(
                        src_pts, dst_pts, cv2.RANSAC, 5.0
                    )

        prev_frame_gray = gray_frame.copy()
        prev_kp, prev_des = orb.detectAndCompute(gray_frame, None)

        # Run YOLO segmentation model on the frame
        results_list = model.predict(frame, show=False)
        if not results_list:
            out.write(frame)
            continue

        results = results_list[0]
        masks = results.masks
        boxes = results.boxes

        binary_mask = np.zeros((frame.shape[0], frame.shape[1]), dtype=np.uint8)
        detected_potholes = []

        if boxes is not None:
            for box in boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                confidence = float(box.conf[0])

                center_x = (x1 + x2) // 2
                center_y = (y1 + y2) // 2
                pothole_id = (center_x // 10, center_y // 10)

                if pothole_id not in unique_potholes:
                    unique_potholes.add(pothole_id)

                detected_potholes.append((x1, y1, x2, y2, confidence))

        if masks is not None and hasattr(masks, "data"):
            mask_data = masks.data.cpu().numpy()
            for mask in mask_data:
                mask = (mask * 255).astype(np.uint8)
                mask_resized = cv2.resize(mask, (frame.shape[1], frame.shape[0]))
                binary_mask = cv2.bitwise_or(binary_mask, mask_resized)

        # Correct Road Area Calculation
        # If homography is available, align binary mask
        if homography_matrix is not None:
            binary_mask = cv2.warpPerspective(
                binary_mask, homography_matrix, (width, height)
            )

        # Update Global Road Mask** (All road pixels seen so far)
        new_road_pixels = (
            (frame[:, :, 0] > 50) | (frame[:, :, 1] > 50) | (frame[:, :, 2] > 50)
        )  # Any non-black pixel
        global_road_mask[new_road_pixels] = 255  # Mark it as road

        # **Update Global Pothole Mask** (All detected potholes)
        global_pothole_mask = cv2.bitwise_or(global_pothole_mask, binary_mask)

        # Compute Correct Percentage
        total_road_pixels = np.sum(global_road_mask > 0)  # Total road pixels
        total_pothole_pixels = np.sum(global_pothole_mask > 0)  # Total pothole pixels

        current_damage = (
            (np.sum(binary_mask > 0) / np.sum(global_road_mask > 0)) * 100
            if np.sum(global_road_mask > 0) > 0
            else 0
        )
        total_damage = (
            (total_pothole_pixels / total_road_pixels) * 100
            if total_road_pixels > 0
            else 0
        )

        # Display Labels
        cv2.putText(
            frame,
            f"Total Damage: {((total_damage)*(1/2)):.2f}%",
            (20, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 0, 255),
            2,
        )

        cv2.putText(
            frame,
            f"Current Frame: {current_damage:.2f}%",
            (20, 60),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 0, 0),
            2,
        )

        # Draw pothole contours
        contours, _ = cv2.findContours(
            binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        for contour in contours:
            cv2.drawContours(frame, [contour], -1, (0, 255, 0), 2)

        mask_colored = cv2.merge(
            [np.zeros_like(binary_mask), np.zeros_like(binary_mask), binary_mask]
        )
        frame = cv2.addWeighted(frame, 0.6, mask_colored, 0.4, 0)

        for x1, y1, x2, y2, confidence in detected_potholes:
            cv2.putText(
                frame,
                f"{confidence:.2f}",
                (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2,
            )

        if frame.shape != (height, width, 3):
            frame = cv2.resize(frame, (width, height))

        out.write(frame)

    cap.release()
    out.release()

    avg_severity = total_severity / frame_count if frame_count > 0 else 0
    total_potholes_detected = len(unique_potholes)

    upload_result = cloudinary.uploader.upload(
        temp_output_path,
        resource_type="video",
        folder="pothole_videos",
        format="mp4",
        eager=[{"format": "mp4"}],
        eager_async=True,
    )

    cloudinary_url = upload_result.get("secure_url", None)
    os.remove(temp_output_path)

    return {
        "average_severity": round(avg_severity, 2),
        "damaged_road_percentage": round(total_damage, 2),
        "video_url": cloudinary_url,
        "total_potholes_detected": total_potholes_detected,
    }
