import cv2
import numpy as np
import os
from skimage.metrics import structural_similarity as ssim
from tqdm import tqdm

# Constants and thresholds
OUTPUT_VIDEO_PATH = 'video.mp4'
OUTPUT_FOLDER = 'scenes'
OUTPUT_PDF = 'presentation_slides.pdf'

# Scene detection parameters
SSIM_THRESHOLD = 0.8  # Adjust this value based on your video characteristics
FRAME_SKIP = 30  # Process every 30th frame
MIN_SCENE_DURATION = 1  # Minimum time (in seconds) between saved frames

def scene_detection(video_path, output_folder=OUTPUT_FOLDER):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    last_saved_frame = None
    scene_number = 0
    processed_frames = 0
    last_save_time = 0

    if not cap.isOpened():
        print("Error: Could not open video.")
        return

    with tqdm(total=frame_count, desc='Processing video frames') as pbar:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            processed_frames += 1
            pbar.update(1)

            if processed_frames % FRAME_SKIP != 0:
                continue

            current_time = processed_frames / fps

            gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            if last_saved_frame is not None:
                ssim_score, _ = ssim(last_saved_frame, gray_frame, full=True)

                if ssim_score < SSIM_THRESHOLD and (current_time - last_save_time) >= MIN_SCENE_DURATION:
                    scene_number += 1
                    output_filename = f'{output_folder}/scene_{scene_number}.png'
                    cv2.imwrite(output_filename, frame)
                    last_saved_frame = gray_frame
                    last_save_time = current_time
                    print(f"New scene detected: {output_filename}, SSIM={ssim_score:.2f}")
            else:
                # Save the first frame
                scene_number += 1
                output_filename = f'{output_folder}/scene_{scene_number}.png'
                cv2.imwrite(output_filename, frame)
                last_saved_frame = gray_frame
                last_save_time = current_time
                print(f"First scene saved: {output_filename}")

    cap.release()
    cv2.destroyAllWindows()

    print(f'Total unique scenes detected: {scene_number}')
    return scene_number

if __name__ == "__main__":
    video_path = 'video.mp4'
    scene_number = scene_detection(video_path)
