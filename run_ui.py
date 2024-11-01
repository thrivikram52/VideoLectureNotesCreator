import streamlit as st
import os
from VideoLectureNotesCreator import (
    transcribe_video,
    extract_frames,
    remove_unmeaningful_frames,
    remove_duplicate_frames_gpt,
    summarize_transcript,
    get_image_summaries,
    create_pdf_report,
    clean_output_folder,
    get_output_folder,
    extract_scene_number
)
from config import *
import tkinter as tk
from tkinter import filedialog
import zipfile
from datetime import datetime

def select_folder():
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    root.wm_attributes('-topmost', 1)  # Bring the dialog to the front
    folder_path = filedialog.askdirectory()
    return folder_path

def create_streamlit_app():
    st.set_page_config(page_title="Video Processing Pipeline", layout="wide")
    st.title("Video Processing Pipeline")

    # Create tabs for the two phases
    phase1, phase2 = st.tabs(["📽️ Phase 1: Frame Extraction & Review", "📄 Phase 2: Generate Notes"])

    with phase1:
        st.header("Phase 1: Frame Extraction & Manual Review")
        
        # Step 1: Video Upload
        st.markdown("---")
        st.subheader("1️⃣ Upload Video")
        uploaded_video = st.file_uploader(
            "Select your video file (MP4, AVI, or MOV) *", 
            type=['mp4', 'avi', 'mov']
        )
        
        if uploaded_video:
            st.success(f"✅ Video selected: {uploaded_video.name}")
            st.info(f"""
            **Video Details:**
            - Name: {uploaded_video.name}
            - Size: {uploaded_video.size/1024/1024:.2f} MB
            - Type: {uploaded_video.type}
            """)
        else:
            st.warning("⚠️ Please upload a video file to begin - This is required!")

        # Step 2: Frame Extraction Settings
        st.markdown("---")
        st.subheader("2️⃣ Frame Extraction Settings")
        if uploaded_video:
            # Create two columns for parameters
            col1, col2 = st.columns(2)
            
            with col1:
                ssim_threshold = st.slider(
                    "SSIM Threshold", 
                    min_value=0.0, 
                    max_value=1.0, 
                    value=float(SSIM_THRESHOLD),
                    help="Lower values will extract more frames. Recommended: 0.5-0.8"
                )
            
            with col2:
                frame_skip = st.number_input(
                    "Frame Skip Rate",
                    min_value=1,
                    max_value=300,
                    value=int(FRAME_SKIP),
                    help="Process every Nth frame. Higher values = fewer frames"
                )

            # Add explanation of parameters
            st.info("""
            **Parameter Guide:**
            - **SSIM Threshold**: Controls how different frames need to be to be considered a new scene
                - Lower values (0.3-0.5): More sensitive to changes, extracts more frames
                - Higher values (0.7-0.9): Less sensitive, extracts fewer frames
            - **Frame Skip Rate**: Process every Nth frame
                - Lower values: More accurate but slower processing
                - Higher values: Faster processing but might miss quick changes
            """)

            # Extract Frames Button
            if st.button("🎬 Extract Frames", type="primary"):
                with st.spinner("Extracting frames..."):
                    try:
                        output_folder = get_output_folder(uploaded_video.name)
                        video_path = os.path.join(output_folder, uploaded_video.name)
                        
                        # Save uploaded video
                        with open(video_path, "wb") as f:
                            f.write(uploaded_video.getbuffer())
                        
                        # Show progress message
                        progress_text = st.empty()
                        progress_text.text("Analyzing video and extracting frames...")
                        
                        num_scenes = extract_frames(
                            video_path=video_path,
                            output_folder=output_folder,
                            skip_frames=frame_skip,
                            ssim_threshold=ssim_threshold
                        )
                        
                        # Success message with stats
                        st.success(f"""
                        ✅ Frame extraction complete!
                        - Extracted {num_scenes} unique scenes
                        - Output folder: {output_folder}
                        """)
                        
                    except Exception as e:
                        st.error(f"❌ Error during frame extraction: {str(e)}")
        else:
            st.warning("Please upload a video first to configure frame extraction settings.")

        # Step 3: Manual Frame Review
        st.markdown("---")
        st.subheader("3️⃣ Manual Frame Review")
        if uploaded_video:
            output_folder = get_output_folder(uploaded_video.name)
            if os.path.exists(output_folder):
                image_files = [f for f in os.listdir(output_folder) if f.endswith('.png')]
                if image_files:
                    st.info("👉 Review and delete any unwanted or duplicate frames below")
                    image_files.sort(key=extract_scene_number)
                    
                    # Create a grid layout
                    cols_per_row = 3
                    for i in range(0, len(image_files), cols_per_row):
                        cols = st.columns(cols_per_row)
                        for j, col in enumerate(cols):
                            idx = i + j
                            if idx < len(image_files):
                                image_path = os.path.join(output_folder, image_files[idx])
                                with col:
                                    st.image(image_path, caption=f"Scene {extract_scene_number(image_files[idx])}")
                                    if st.button(f"🗑️ Delete", key=f"delete_{idx}"):
                                        try:
                                            os.remove(image_path)
                                            st.success(f"Deleted {image_files[idx]}")
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"Error deleting {image_files[idx]}: {str(e)}")
                else:
                    st.warning("No frames found. Please extract frames first.")

    with phase2:
        st.header("Phase 2: Generate Notes")
        
        # Check if Phase 1 is completed
        if not uploaded_video:
            st.error("⚠️ Please complete Phase 1 first! Upload a video.")
            return
            
        output_folder = get_output_folder(uploaded_video.name)
        
        # Check for frames but don't block if none exist
        has_frames = os.path.exists(output_folder) and any(f.endswith('.png') for f in os.listdir(output_folder))
        if not has_frames:
            st.warning("⚠️ No frames found. Will proceed with transcript processing only.")
            
        # Optional Transcript Upload
        st.subheader("1️⃣ Transcript (Optional)")
        uploaded_transcript = st.file_uploader(
            "Upload transcript file or let the system generate one", 
            type=['txt'],
            key="transcript_uploader"
        )
        
        if uploaded_transcript:
            st.success(f"✅ Using uploaded transcript: {uploaded_transcript.name}")

        # Prompt Configuration
        st.subheader("2️⃣ Configure Prompts")
        with st.expander("📝 Prompts Configuration", expanded=False):
            transcript_prompt = st.text_area(
                "Transcript Summary Prompt",
                value=TRANSCRIPT_SUMMARY_PROMPT,
                key="transcript_summary_prompt"
            )
            if has_frames:
                image_prompt = st.text_area(
                    "Image Summary Prompt",
                    value=IMAGE_SUMMARY_PROMPT,
                    key="image_summary_prompt"
                )

        # Process Button
        if st.button("▶️ Generate Notes", type="primary"):
            progress = st.progress(0)
            status_text = st.empty()
            results = {}
            
            try:
                # Create checklist for tracking
                checklist_items = {
                    "transcribe": st.empty(),
                    "summarize": st.empty(),
                    "image_summaries": st.empty(),
                    "create_pdf": st.empty()
                }
                
                # 1. Handle Transcript
                transcript_path = os.path.join(output_folder, "transcript.txt")
                
                if uploaded_transcript:
                    status_text.text("Using uploaded transcript...")
                    progress.progress(10)
                    with open(transcript_path, "wb") as f:
                        f.write(uploaded_transcript.getbuffer())
                    checklist_items["transcribe"].markdown("✅ Using uploaded transcript")
                else:
                    # Always generate new transcript if not uploaded
                    status_text.text("Generating transcript... This may take a few minutes...")
                    progress.progress(10)
                    video_path = os.path.join(output_folder, uploaded_video.name)
                    
                    if not os.path.exists(video_path):
                        # Save the video file if it doesn't exist
                        with open(video_path, "wb") as f:
                            f.write(uploaded_video.getbuffer())
                    
                    # Remove existing transcript if any
                    if os.path.exists(transcript_path):
                        os.remove(transcript_path)
                        
                    # Generate new transcript
                    transcript_path = transcribe_video(
                        video_path=video_path,
                        output_folder=output_folder
                    )
                    
                    if os.path.exists(transcript_path):
                        checklist_items["transcribe"].markdown("✅ Generated new transcript")
                    else:
                        raise Exception("Transcript generation failed")
                
                # 2. Summarize Transcript
                status_text.text("Summarizing transcript...")
                progress.progress(30)
                transcript_summary = summarize_transcript(
                    transcript_path=transcript_path,
                    prompt=transcript_prompt
                )
                results['transcript_summary'] = transcript_summary
                checklist_items["summarize"].markdown("✅ Summarized transcript")
                
                # 3. Generate Image Summaries (only if frames exist)
                if has_frames:
                    status_text.text("Generating image summaries...")
                    progress.progress(60)
                    image_summaries = get_image_summaries(
                        output_folder=output_folder,
                        transcript_summary=results.get('transcript_summary', ''),
                        prompt=image_prompt
                    )
                    results['image_summaries'] = image_summaries
                    checklist_items["image_summaries"].markdown("✅ Generated image summaries")
                
                # 4. Create PDF
                status_text.text("Creating PDF report...")
                progress.progress(90)
                pdf_path = create_pdf_report(
                    output_folder=output_folder
                )
                results['pdf_path'] = pdf_path
                checklist_items["create_pdf"].markdown("✅ Created PDF report")
                
                # Complete
                progress.progress(100)
                status_text.text("✅ Processing complete!")
                
                # Show download section
                st.markdown("---")
                st.subheader("📥 Download Results")
                
                # Create and download zip of all artifacts
                try:
                    video_name = os.path.splitext(uploaded_video.name)[0]
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    zip_filename = f"{video_name}_notes_{timestamp}.zip"
                    zip_path = os.path.join(output_folder, "temp_artifacts.zip")
                    
                    with zipfile.ZipFile(zip_path, 'w') as zipf:
                        for root, dirs, files in os.walk(output_folder):
                            for file in files:
                                file_path = os.path.join(root, file)
                                if not (file.endswith(('.mp4', '.avi', '.mov')) or file == "temp_artifacts.zip"):
                                    arcname = os.path.relpath(file_path, output_folder)
                                    zipf.write(file_path, arcname)
                    
                    with open(zip_path, "rb") as f:
                        st.download_button(
                            label="📦 Download Generated Notes & Resources",
                            data=f,
                            file_name=zip_filename,
                            mime="application/zip",
                            help="Download all generated files (transcript, summaries, images, PDF)"
                        )
                    
                    if os.path.exists(zip_path):
                        os.remove(zip_path)
                        
                except Exception as e:
                    st.error(f"Error creating zip file: {str(e)}")
                    
            except Exception as e:
                st.error(f"❌ Error during processing: {str(e)}")
                status_text.text("Processing failed!")
                progress.progress(0)

if __name__ == "__main__":
    create_streamlit_app()
 