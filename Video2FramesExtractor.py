import cv2
import numpy as np
import os
from skimage.metrics import structural_similarity as ssim
from tqdm import tqdm
import openai
from PIL import Image
import base64
import io
from openai import OpenAI
import pytesseract
import re
import sys
import json
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
import logging
import markdown2
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.platypus import Paragraph, Spacer, Image as RLImage
import html
from bs4 import BeautifulSoup
import whisper

# Constants and thresholds
OUTPUT_VIDEO_PATH = 'video.mp4'
OUTPUT_FOLDER = 'scenes'
OUTPUT_PDF = 'presentation_slides.pdf'

# Scene detection parameters
SSIM_THRESHOLD = 0.65  # Adjust this value based on your video characteristics
FRAME_SKIP = 300  # Process every 30th frame
MIN_SCENE_DURATION = 1  # Minimum time (in seconds) between saved frames

client = OpenAI()

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

def analyze_image(image_path):
    try:
        with open(image_path, "rb") as image_file:
            encoded_image = base64.b64encode(image_file.read()).decode('utf-8')
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Updated model name
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", 
                         "text": "Definition of Meaningful Content:\
Meaningful content includes any text, diagrams, charts, images (beyond participant profile pictures), \
tables, or visual elements that provide valuable information or insights. This content should contribute \
directly to the understanding or learning points you want to cover in your lecture notes. \
Examples include slides with data, key points, or visual aids that can be explained further in the notes. \
What is Not Considered Meaningful Content:\
Slides that only display people's profile pictures, names, or generic visuals from the meeting \
(e.g., video feeds or participant screens), as well as blank slides, are classified as No Meaningful Content. \
These slides do not provide valuable material for lecture notes.\
Task:\
Analyze the provided slide and classify it as Contains Meaningful Content if it includes \
text, diagrams, or other elements that can be elaborated upon in lecture notes. \
If the slide contains only people's images or does not have useful content, \
classify it as false otherwise true. You give only TRUE or FALSE(case sensitive). Do not give explanation.\
"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{encoded_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=300
        )

        return response.choices[0].message.content
    except Exception as e:
        print(f"Error analyzing image {image_path}: {str(e)}", file=sys.stderr)
        return None

def remove_non_meaningful_scenes(folder_path=OUTPUT_FOLDER):
    print("Starting remove_non_meaningful_scenes function")
    image_files = [f for f in os.listdir(folder_path) if f.endswith('.png')]
    if not image_files:
        print(f"No png files found in {folder_path}")
        return []

    image_files.sort(key=lambda x: int(x.split('_')[1].split('.')[0]))
    print(f"Found {len(image_files)} images to process")

    results = []
    for image_file in image_files:
        image_path = os.path.join(folder_path, image_file)
        print(f"Processing {image_file}")
        has_meaningful_content = analyze_image(image_path)
        if has_meaningful_content == "TRUE":
            results.append((image_file, has_meaningful_content))
        else:
            print(f"Skipping {image_file} as it doesn't have meaningful content")

    print(f"Processed {len(results)} meaningful images")
    print("Finished remove_non_meaningful_scenes function")
    return results

def summarize_transcript(transcript_path):
    print(f"Starting summarize_transcript function for {transcript_path}")
    try:
        with open(transcript_path, 'r', encoding='utf-8') as file:
            full_text = file.read()
        
        user_prompt = f"Please summarize the following transcript, ensuring that no details are missed. Use markdown headers, paragraphs, and bullet points for clear structure:\n\n{full_text}"
        system_prompt = "As an instructor, generate a comprehensive summary that captures the key points and insights from the provided material. \
            Focus on explaining concepts clearly and engagingly, ensuring that the content is informative and easy to understand for the intended audience. \
            Highlight important details, examples, and any relevant applications without referring to the source material.\
            Aim for a concise yet thorough overview that could serve as a teaching aid.Use markdown formatting for structure, including headers and bullet points where appropriate."

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=1000
        )
        
        print("Successfully generated transcript summary")
        print("Finished summarize_transcript function")
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error summarizing transcript: {str(e)}", file=sys.stderr)
        print(f"File content (first 100 characters): {full_text[:100]}", file=sys.stderr)
        print("Finished summarize_transcript function with errors")
        return None

def get_image_summaries(meaningful_images, transcript_summary):
    print("Starting get_image_summaries function")
    image_summaries = []
    for image_file, _ in meaningful_images:
        print(f"Generating summary for image: {image_file}")
        image_path = os.path.join(OUTPUT_FOLDER, image_file)
        user_prompt = f"Based on this transcript summary:\n\n{transcript_summary}\n\nPlease provide a brief description of what is shown in the image {image_file}. Focus on how it relates to the content of the transcript"
        system_prompt = "As an instructor, generate a comprehensive summary that captures the key points and insights from the provided material. \
            Focus on explaining concepts clearly and engagingly, ensuring that the content is informative and easy to understand for the intended audience. \
            Highlight important details, examples, and any relevant applications without referring to the source material.\
            Aim for a concise yet thorough overview that could serve as a teaching aid.Use markdown formatting for structure, including headers and bullet points where appropriate."
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=200
        )
        
        image_summaries.append((image_file, response.choices[0].message.content))
        print(f"Generated summary for image: {image_file}")

    print(f"Generated summaries for {len(image_summaries)} images")
    print("Finished get_image_summaries function")
    return image_summaries

def markdown_to_pdf_elements(markdown_text, styles):
    html_content = markdown2.markdown(markdown_text)
    
    # Use BeautifulSoup to parse and clean up the HTML
    soup = BeautifulSoup(html_content, 'html.parser')
    
    elements = []
    
    for element in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'li']):
        if element.name.startswith('h'):
            level = int(element.name[1])
            text = element.get_text()
            elements.append(Paragraph(text, styles[f'Heading{level}']))
        elif element.name == 'p':
            text = element.get_text()
            elements.append(Paragraph(text, styles['BodyText']))
        elif element.name == 'li':
            text = '• ' + element.get_text()
            elements.append(Paragraph(text, styles['BodyText']))
        
        elements.append(Spacer(1, 0.1*inch))
    
    return elements

def create_pdf_report(image_summaries, transcript_summary, output_pdf='presentation_summary.pdf'):
    print(f"Starting create_pdf_report function, output: {output_pdf}")
    doc = SimpleDocTemplate(output_pdf, pagesize=letter)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Justify', alignment=TA_JUSTIFY))
    story = []

    print("Adding image summaries to PDF")
    for image_file, image_summary in image_summaries:
        print(f"Adding summary for image: {image_file}")
        try:
            img = RLImage(os.path.join(OUTPUT_FOLDER, image_file), width=6*inch, height=4*inch)
            story.append(img)
        except Exception as e:
            print(f"Error adding image {image_file}: {str(e)}")
            story.append(Paragraph(f"[Image {image_file} could not be loaded]", styles['BodyText']))
        story.append(Spacer(1, 0.2*inch))
        story.extend(markdown_to_pdf_elements(image_summary, styles))
        story.append(Spacer(1, 0.5*inch))

    print("Adding overall transcript summary to PDF")
    story.append(Paragraph("Overall Transcript Summary", styles['Heading1']))
    story.extend(markdown_to_pdf_elements(transcript_summary, styles))
    story.append(Spacer(1, 0.5*inch))

    try:
        doc.build(story)
        print(f"PDF report created: {output_pdf}")
    except Exception as e:
        print(f"Error building PDF: {str(e)}")
        # Attempt to save what we can
        try:
            doc.build(story[:len(story)//2])  # Try to build with half the content
            print(f"Partial PDF report created: {output_pdf}")
        except:
            print("Failed to create even a partial PDF report")

    print("Finished create_pdf_report function")

def transcribe_video(video_path, output_path='transcription.txt'):
    print(f"Starting transcription of video: {video_path}")
    model = whisper.load_model("base")  # You can change "base" to other model sizes if needed
    
    result = model.transcribe(video_path)
    
    with open(output_path, "w", encoding="utf-8") as file:
        file.write(result["text"])
    
    print(f"Transcription completed and saved to: {output_path}")
    return output_path

# Main execution
if __name__ == "__main__":
    print("Starting main execution")

    # Transcribe video
    print("Starting vedio transcription")
    video_path = OUTPUT_VIDEO_PATH  # Adjust this to your video file path
    transcript_path = transcribe_video(video_path)
    print("Vedio transcription completed")

    # Perform scene detection
    print("Starting scene detection")
    num_scenes = scene_detection(video_path)
    print(f"Detected {num_scenes} unique scenes")

    # Get meaningful images
    meaningful_images = remove_non_meaningful_scenes()
    if not meaningful_images:
        print("No meaningful images found", file=sys.stderr)
        sys.exit(1)

    # Summarize transcript
    transcript_summary = summarize_transcript(transcript_path)
    if not transcript_summary:
        print("Failed to generate transcript summary", file=sys.stderr)
        sys.exit(1)

    # Get summaries for each meaningful image
    image_summaries = get_image_summaries(meaningful_images, transcript_summary)

    # Create PDF report
    create_pdf_report(image_summaries, transcript_summary)

    print("Main execution completed successfully")
