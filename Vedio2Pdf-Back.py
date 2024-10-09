import cv2
import numpy as np
import os
from pytube import YouTube
from skimage.metrics import structural_similarity as ssim
from fpdf import FPDF
from tqdm import tqdm

def download_youtube_video(url, output_path='video.mp4'):
    yt = YouTube(url)
    stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
    total_size = stream.filesize
    print(f"Total video size: {total_size / (1024 * 1024):.2f} MB")
    
    with tqdm(total=total_size, unit='B', unit_scale=True, desc='Downloading video') as pbar:
        def on_progress(chunk, file_handle, bytes_remaining):
            pbar.update(len(chunk))
    
        yt.register_on_progress_callback(on_progress)
        stream.download(filename=output_path)
    return output_path

def compare_histograms(img1, img2):
    hist1 = cv2.calcHist([img1], [0], None, [256], [0, 256])
    hist2 = cv2.calcHist([img2], [0], None, [256], [0, 256])
    cv2.normalize(hist1, hist1)
    cv2.normalize(hist2, hist2)
    score = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
    return score

def scene_detection(video_path, output_folder='scenes', ssim_threshold=0.5, hist_threshold=0.5, frame_skip=5):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    prev_frame = None
    last_saved_frame = None
    scene_number = 0
    processed_frames = 0

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

            if processed_frames % frame_skip != 0:
                continue

            gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            if last_saved_frame is not None:
                ssim_score, _ = ssim(last_saved_frame, gray_frame, full=True)
                hist_score = compare_histograms(last_saved_frame, gray_frame)

                if ssim_score < ssim_threshold or hist_score < hist_threshold:
                    scene_number += 1
                    output_filename = f'{output_folder}/scene_{scene_number}.png'
                    cv2.imwrite(output_filename, frame)
                    last_saved_frame = gray_frame
            else:
                # Save the first frame
                scene_number += 1
                output_filename = f'{output_folder}/scene_{scene_number}.png'
                cv2.imwrite(output_filename, frame)
                last_saved_frame = gray_frame

            prev_frame = gray_frame

    cap.release()
    cv2.destroyAllWindows()

    # Calculate scenes per second
    duration_in_seconds = processed_frames / fps
    scenes_per_second = scene_number / duration_in_seconds
    print(f'Scenes per second: {scenes_per_second:.2f}')

    return scene_number

def create_pdf_from_images(image_folder, output_pdf):
    pdf = FPDF()
    images = [f for f in sorted(os.listdir(image_folder)) if f.endswith('.png')]

    for image in images:
        pdf.add_page()
        pdf.image(os.path.join(image_folder, image), 10, 10, 190)
    
    pdf.output(output_pdf, "F")

    # Delete the images after creating the PDF
    for image in images:
        os.remove(os.path.join(image_folder, image))
    print(f'PDF created: {output_pdf}')

if __name__ == "__main__":
    youtube_url = 'https://www.youtube.com/watch?v=IpGxLWOIZy4'  # Replace with your YouTube URL
    #video_path = download_youtube_video(youtube_url)
    video_path = 'video.mp4'
    scene_number = scene_detection(video_path)
    if scene_number > 0:
        create_pdf_from_images('scenes', 'scenes.pdf')
