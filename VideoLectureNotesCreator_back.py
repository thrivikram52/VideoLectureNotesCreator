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
import shutil

client = OpenAI()

def transcribe_video(video_path, output_folder):
    """
    Transcribes video if transcript doesn't exist
    """
    transcript_path = os.path.join(output_folder, "transcript.txt")
    
    # If transcript already exists, return its path
    if os.path.exists(transcript_path):
        return transcript_path
        
    # Generate transcript if it doesn't exist
    try:
        # Your existing transcription code here
        model = whisper.load_model("base")
        result = model.transcribe(video_path)
        
        # Save transcript
        with open(transcript_path, "w", encoding="utf-8") as f:
            f.write(result["text"])
            
        return transcript_path
        
    except Exception as e:
        raise Exception(f"Failed to transcribe video: {str(e)}")

def clean_output_folder(folder_path):
    if os.path.exists(folder_path):
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f"Error cleaning up {file_path}: {e}")
    else:
        os.makedirs(folder_path)
    print(f"Cleaned output folder: {folder_path}")

def extract_frames(video_path, output_folder, skip_frames, ssim_threshold ):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
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

            if processed_frames % skip_frames != 0:
                continue

            gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            if last_saved_frame is not None:
                ssim_score, _ = ssim(last_saved_frame, gray_frame, full=True)

                if ssim_score < ssim_threshold :
                    scene_number += 1
                    output_filename = f'{output_folder}/scene_{scene_number}.png'
                    cv2.imwrite(output_filename, frame)
                    last_saved_frame = gray_frame
                    print(f"New scene detected: {output_filename}, SSIM={ssim_score:.2f}")
            else:
                # Save the first frame
                scene_number += 1
                output_filename = f'{output_folder}/scene_{scene_number}.png'
                cv2.imwrite(output_filename, frame)
                last_saved_frame = gray_frame
                print(f"First scene saved: {output_filename}")

    cap.release()
    cv2.destroyAllWindows()

    print(f'Total unique scenes detected: {scene_number}')
    return scene_number

def check_image_has_meaningful_content(image_path, prompt):
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
                         "text": prompt},
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

def extract_scene_number(filename):
    """Helper function to safely extract scene number from filename"""
    try:
        # Extract number between 'scene_' and '.png'
        return int(filename.split('_')[1].split('.')[0])
    except (IndexError, ValueError):
        return 0

def remove_unmeaningful_frames(folder_path, prompt):
    print("Starting remove_non_meaningful_scenes function")
    image_files = [f for f in os.listdir(folder_path) if f.endswith('.png')]
    if not image_files:
        print(f"No png files found in {folder_path}")
        return []

    # Use the safe sorting function
    image_files.sort(key=extract_scene_number)
    print(f"Found {len(image_files)} images to process")

    meaningful_images = []
    for image_file in image_files:
        image_path = os.path.join(folder_path, image_file)
        print(f"Processing {image_file}")
        has_meaningful_content = check_image_has_meaningful_content(image_path, prompt)
        if has_meaningful_content == "TRUE":
            meaningful_images.append((image_file, has_meaningful_content))
            print(f"Keeping {image_file} as it has meaningful content")
        else:
            # Remove the non-meaningful image
            try:
                os.remove(image_path)
                print(f"Removed {image_file} as it doesn't have meaningful content")
            except Exception as e:
                print(f"Error removing {image_file}: {str(e)}")

    print(f"Kept {len(meaningful_images)} meaningful images")
    print("Finished remove_non_meaningful_scenes function")
    return meaningful_images

def remove_duplicate_frames_gpt(folder_path, prompt):
    print("Starting remove_duplicate_frames_gpt function")
    image_files = [f for f in os.listdir(folder_path) if f.endswith('.png')]
    if not image_files:
        print(f"No png files found in {folder_path}")
        return []

    # Sort in reverse order using the safe sorting function
    image_files.sort(key=extract_scene_number, reverse=True)
    print(f"Found {len(image_files)} images to process for duplicates using GPT Vision")

    unique_images = []
    for i, image_file in enumerate(image_files):
        image_path = os.path.join(folder_path, image_file)
        
        is_duplicate = False
        for j in range(i + 1, len(image_files)):
            next_image_path = os.path.join(folder_path, image_files[j])
            
            # Encode both images
            with open(image_path, "rb") as img1_file, open(next_image_path, "rb") as img2_file:
                encoded_img1 = base64.b64encode(img1_file.read()).decode('utf-8')
                encoded_img2 = base64.b64encode(img2_file.read()).decode('utf-8')

            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", 
                                 "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/png;base64,{encoded_img1}"
                                    }
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/png;base64,{encoded_img2}"
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=10
                )

                is_same = response.choices[0].message.content.strip() == "TRUE"
                print(f"Comparing {image_file} and {image_files[j]}: {'Same' if is_same else 'Different'}")
                
                if is_same:
                    print(f"Duplicate scene detected: {image_file} and {image_files[j]}")
                    is_duplicate = True
                    break

            except Exception as e:
                print(f"Error comparing images {image_file} and {image_files[j]}: {str(e)}")
                continue

        if not is_duplicate:
            unique_images.append(image_file)

    # Remove duplicate images
    for image_file in image_files:
        if image_file not in unique_images:
            os.remove(os.path.join(folder_path, image_file))
            print(f"Removed duplicate scene: {image_file}")

    print(f"Finished remove_duplicate_frames_gpt function, {len(unique_images)} unique images remain")
    return unique_images

def summarize_transcript(transcript_path: str, prompt: str) -> str:
    """
    Summarize transcript using GPT
    """
    try:
        # Initialize OpenAI client with API key
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        with open(transcript_path, 'r') as f:
            transcript = f.read()
        
        response = client.chat.completions.create(
            model="gpt-4",  # or "gpt-3.5-turbo"
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": transcript}
            ]
        )
        
        return response.choices[0].message.content
    except Exception as e:
        raise Exception(f"Error in summarize_transcript: {str(e)}")

def get_image_summaries(output_folder: str, transcript_summary: str, prompt: str) -> dict:
    """
    Generate summaries for images using GPT
    """
    try:
        # Initialize OpenAI client with API key
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        image_files = [f for f in os.listdir(output_folder) if f.endswith('.png')]
        if not image_files:
            print(f"No png files found in {output_folder}")
            return []
            
        # Use the safe sorting function
        image_files.sort(key=extract_scene_number)
        print(f"Found {len(image_files)} images to process")
        
        image_summaries = []
        
        for image_file in image_files:
            print(f"Generating summary for image: {image_file}")
            image_path = os.path.join(output_folder, image_file)
            
            try:
                formatted_prompt = prompt.format(transcript=transcript_summary, image=image_file)
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "user", "content": formatted_prompt}
                    ],
                    max_tokens=400
                )
                
                summary = response.choices[0].message.content
                image_summaries.append((image_file, summary))
                
                # Save individual summary file directly in output folder
                # Convert scene_1.png to scene_1_summary.txt
                summary_filename = image_file.replace('.png', '_summary.txt')
                summary_path = os.path.join(output_folder, summary_filename)
                
                with open(summary_path, "w", encoding="utf-8") as f:
                    f.write(f"Image: {image_file}\n")
                    f.write(f"Scene Number: {extract_scene_number(image_file)}\n")
                    f.write("-" * 50 + "\n")
                    f.write("Summary:\n")
                    f.write(summary)
                
                print(f"Saved summary for {image_file} to {summary_path}")
                
            except Exception as e:
                print(f"Error generating summary for {image_file}: {str(e)}")
                # Save error information in output folder
                error_filename = image_file.replace('.png', '_error.txt')
                error_path = os.path.join(output_folder, error_filename)
                with open(error_path, "w", encoding="utf-8") as f:
                    f.write(f"Error processing {image_file}: {str(e)}")
                continue

        # Create an index file in output folder
        index_path = os.path.join(output_folder, "summaries_index.txt")
        with open(index_path, "w", encoding="utf-8") as f:
            f.write("Image Summaries Index\n")
            f.write("=" * 20 + "\n\n")
            for image_file, _ in image_summaries:
                summary_filename = image_file.replace('.png', '_summary.txt')
                f.write(f"- {image_file} -> {summary_filename}\n")

        print(f"Generated summaries for {len(image_summaries)} images")
        print("Finished get_image_summaries function")
        return image_summaries
    except Exception as e:
        raise Exception(f"Error in get_image_summaries: {str(e)}")

#TODO styles shall be passed from the caller
def markdown_to_pdf_elements(markdown_text, styles):
    # Convert markdown to HTML
    html_content = markdown2.markdown(markdown_text)
    
    # Use BeautifulSoup to parse the HTML
    soup = BeautifulSoup(html_content, 'html.parser')
    
    elements = []
    
    # Process each element only once
    for element in soup.children:
        # Skip if it's just a string or empty
        if isinstance(element, str) or not element.name:
            continue
            
        if element.name.startswith('h'):
            # Handle headers
            level = int(element.name[1])
            style_name = f'Heading{level}' if level <= 6 else 'Heading6'
            elements.append(Paragraph(
                element.get_text().strip(),
                styles[style_name]
            ))
            
        elif element.name == 'p':
            # Handle paragraphs
            text = element.get_text().strip()
            if text:  # Only add non-empty paragraphs
                elements.append(Paragraph(
                    text,
                    styles['BodyText']
                ))
                
        elif element.name == 'ul':
            # Handle unordered lists
            for li in element.find_all('li', recursive=False):
                text = '• ' + li.get_text().strip()
                elements.append(Paragraph(
                    text,
                    styles['BodyText']
                ))
                
        elif element.name == 'ol':
            # Handle ordered lists
            for i, li in enumerate(element.find_all('li', recursive=False), 1):
                text = f"{i}. {li.get_text().strip()}"
                elements.append(Paragraph(
                    text,
                    styles['BodyText']
                ))
        
        # Add spacing after each element
        if elements:  # Only add spacer if we added an element
            elements.append(Spacer(1, 0.1*inch))
    
    return elements

def create_pdf_report(output_folder: str, output_filename: str = None) -> str:
    """
    Create PDF report from transcript and images
    """
    if output_filename is None:
        output_filename = "notes.pdf"
        
    output_pdf = os.path.join(output_folder, output_filename)
    
    print(f"Starting create_pdf_report function, output: {output_pdf}")
    doc = SimpleDocTemplate(output_pdf, pagesize=letter)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Justify', alignment=TA_JUSTIFY))
    story = []

    # Add title
    story.append(Paragraph("Lecture Notes", styles['Title']))
    story.append(Spacer(1, 0.5*inch))

    # Get all image files and their summaries first
    image_files = [f for f in os.listdir(output_folder) if f.endswith('.png')]
    image_files.sort(key=extract_scene_number)

    if image_files:
        story.append(Paragraph("Summary", styles['Heading1']))
        story.append(Spacer(1, 0.3*inch))

        print("Adding image summaries to PDF")
        for image_file in image_files:
            # Get corresponding summary file
            summary_file = image_file.replace('.png', '_summary.txt')
            summary_path = os.path.join(output_folder, summary_file)
            
            if not os.path.exists(summary_path):
                print(f"Warning: Summary not found for {image_file}")
                continue
            
            # Add image
            try:
                img_path = os.path.join(output_folder, image_file)
                img = RLImage(img_path, width=6*inch, height=4*inch)
                story.append(img)
            except Exception as e:
                print(f"Error adding image {image_file}: {str(e)}")
                story.append(Paragraph(f"[Image {image_file} could not be loaded]", styles['BodyText']))
            
            # Add summary
            try:
                with open(summary_path, 'r', encoding='utf-8') as f:
                    # Skip the header lines and get only the summary
                    lines = f.readlines()
                    summary = ''.join(lines[4:])  # Skip first 4 lines (Image:, Scene Number:, ---, Summary:)
                story.append(Spacer(1, 0.2*inch))
                story.extend(markdown_to_pdf_elements(summary, styles))
                story.append(Spacer(1, 0.5*inch))
            except Exception as e:
                print(f"Error adding summary for {image_file}: {str(e)}")

    # Add transcript summary section at the end if exists
    transcript_summary_path = os.path.join(output_folder, "transcript_summary.txt")
    if os.path.exists(transcript_summary_path):
        story.append(Paragraph("Transcript Summary", styles['Heading1']))
        with open(transcript_summary_path, 'r', encoding='utf-8') as f:
            transcript_summary = f.read()
        story.extend(markdown_to_pdf_elements(transcript_summary, styles))
        story.append(Spacer(1, 0.5*inch))

    try:
        doc.build(story)
        print(f"PDF report created: {output_pdf}")
    except Exception as e:
        print(f"Error building PDF: {str(e)}")
        try:
            doc.build(story[:len(story)//2])
            print(f"Partial PDF report created: {output_pdf}")
        except:
            print("Failed to create even a partial PDF report")

    print("Finished create_pdf_report function")
    return output_pdf

def get_output_folder(video_filename):
    """
    Creates and returns output folder path based on video filename
    Example: 'lecture1.mp4' -> 'lecture1'
    """
    # Remove file extension and any special characters
    base_name = os.path.splitext(video_filename)[0]
    # Create a valid folder name (remove special characters)
    safe_name = "".join(c for c in base_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
    # Create directory if it doesn't exist
    os.makedirs(safe_name, exist_ok=True)
    return safe_name

