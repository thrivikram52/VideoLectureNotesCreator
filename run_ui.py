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
    clean_output_folder
)
from config import *
import tkinter as tk
from tkinter import filedialog
import zipfile

def select_folder():
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    root.wm_attributes('-topmost', 1)  # Bring the dialog to the front
    folder_path = filedialog.askdirectory()
    return folder_path

def create_streamlit_app():
    st.set_page_config(
        page_title="Video Processing Pipeline",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    st.title("Video Processing Pipeline")
    
    # Create a container for file selection
    with st.container():
        st.header("Setup")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Video File Selection
            st.subheader("1️⃣ Upload Video")
            uploaded_video = st.file_uploader(
                "Select your video file (MP4, AVI, or MOV)", 
                type=['mp4', 'avi', 'mov']
            )
            
            if uploaded_video:
                st.success(f"✅ Video selected: {uploaded_video.name}")
                # Display video details
                st.info(f"""
                **Video Details:**
                - Name: {uploaded_video.name}
                - Size: {uploaded_video.size/1024/1024:.2f} MB
                - Type: {uploaded_video.type}
                """)
            else:
                st.warning("⚠️ Please upload a video file to begin")

        with col2:
            # Optional Transcript Upload
            st.subheader("2️⃣ Upload Transcript (Optional)")
            uploaded_transcript = st.file_uploader(
                "Select transcript file (TXT)", 
                type=['txt']
            )
            
            if uploaded_transcript:
                st.success(f"✅ Transcript selected: {uploaded_transcript.name}")
            else:
                st.info("ℹ️ Transcript will be generated automatically if not provided")

    # Add stage selection before the processing parameters
    st.markdown("---")
    st.subheader("3️⃣ Select Stages to Run")
    
    # Add information about folder cleanup behavior
    st.info("""
    📂 **Output Folder Behavior:**
    - If **all stages** are selected: The output folder will be cleaned for a fresh start
    - If **Transcribe** or **Extract Frames** is selected: The output folder will be cleaned
    - Otherwise: Existing files will be preserved and reused
    """)
    
    # Create columns for stage selection checkboxes
    stage_cols = st.columns(2)
    with stage_cols[0]:
        stages = {
            "transcribe": st.checkbox("Transcribe Video", value=True),
            "extract_frames": st.checkbox("Extract Frames", value=True),
            "remove_unmeaningful": st.checkbox("Remove Unmeaningful Frames", value=True),
            "remove_duplicates": st.checkbox("Remove Duplicates", value=True),
        }
    with stage_cols[1]:
        stages.update({
            "summarize_transcript": st.checkbox("Summarize Transcript", value=True),
            "generate_summaries": st.checkbox("Generate Image Summaries", value=True),
            "create_pdf": st.checkbox("Create PDF Report", value=True),
            "cleanup": st.checkbox("Cleanup", value=True),
        })

    # Add dynamic warning based on selection
    all_stages_enabled = all(stages.values())
    initial_stages_enabled = stages["transcribe"] or stages["extract_frames"]
    
    if all_stages_enabled:
        st.warning("⚠️ All stages selected: Output folder will be cleaned for a fresh start")
    elif initial_stages_enabled:
        st.warning("⚠️ Initial stages selected: Output folder will be cleaned")

    # Add warning about video requirement
    if initial_stages_enabled:
        if not uploaded_video:
            st.warning("⚠️ Video upload is mandatory when Transcribe or Extract Frames is selected!")
    else:
        if not uploaded_video:
            st.info("ℹ️ Video upload is optional for the selected stages")

    # Create two columns for parameters and prompts
    st.markdown("---")  # Add a separator line
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("4️⃣ Processing Parameters")
        
        # Add input validation for numeric parameters
        try:
            ssim_threshold = st.slider(
                "SSIM Threshold", 
                min_value=0.0, 
                max_value=1.0, 
                value=float(SSIM_THRESHOLD),  # Convert to float
                help="Controls how different frames need to be to be considered unique scenes."
            )
            
            frame_skip = st.number_input(
                "Frame Skip", 
                min_value=1, 
                value=int(FRAME_SKIP),  # Convert to integer
                help="Number of frames to skip between analyses."
            )
        except ValueError as e:
            st.error("Invalid value in config for SSIM_THRESHOLD or FRAME_SKIP. Please check your config file.")
            return

        cleanup = st.checkbox(
            "Enable Cleanup", 
            value=bool(CLEANUP_ENABLED),  # Convert to boolean
            help="Remove temporary files after processing"
        )

    with col2:
        st.subheader("5️⃣ Prompts Configuration")
        
        st.info("""
        Customize the AI prompts used for different stages of processing. 
        Expand each section below to view and modify the prompts.
        """)
        
        # Initialize session state for prompts
        if 'transcript_summary_prompt' not in st.session_state:
            st.session_state.transcript_summary_prompt = TRANSCRIPT_SUMMARY_PROMPT
        if 'image_summary_prompt' not in st.session_state:
            st.session_state.image_summary_prompt = IMAGE_SUMMARY_PROMPT
        if 'remove_unmeaningful_frames_prompt' not in st.session_state:
            st.session_state.remove_unmeaningful_frames_prompt = REMOVE_UNMEANINGFUL_FRAMES_PROMPT
        if 'duplicate_frames_detection_prompt' not in st.session_state:
            st.session_state.duplicate_frames_detection_prompt = DUPLICATE_FRAMES_DETECTION_PROMPT
        
        # Individual prompt expanders
        with st.expander("📝 Transcript Summary Prompt", expanded=False):
            st.session_state.transcript_summary_prompt = st.text_area(
                "Configure how transcript summaries are generated", 
                value=st.session_state.transcript_summary_prompt,
                height=150,
                help="Template for generating transcript summaries"
            )
        
        with st.expander("🖼️ Image Summary Prompt", expanded=False):
            st.session_state.image_summary_prompt = st.text_area(
                "Configure how image descriptions are generated", 
                value=st.session_state.image_summary_prompt,
                height=150,
                help="Template for generating image descriptions"
            )
        
        with st.expander("🔍 Remove Unmeaningful Frames Prompt", expanded=False):
            st.session_state.remove_unmeaningful_frames_prompt = st.text_area(
                "Configure how unmeaningful frames are identified", 
                value=st.session_state.remove_unmeaningful_frames_prompt,
                height=150,
                help="Helps identify and remove unmeaningful frames"
            )
        
        with st.expander("🎬 Duplicate Frames Detection Prompt", expanded=False):
            st.session_state.duplicate_frames_detection_prompt = st.text_area(
                "Configure how duplicate frames are detected", 
                value=st.session_state.duplicate_frames_detection_prompt,
                height=150,
                help="Guides the detection of duplicate frames"
            )

    # Add a separator before the process button
    st.markdown("---")
    
    # Center the process button and add output folder info
    col1, col2, col3 = st.columns([3, 2, 3])
    with col2:
        st.info("Files will be saved in the 'output' folder")
        process_button = st.button("▶️ Process", type="primary", use_container_width=True)

    if process_button:
        # Check if video is required and not provided
        if initial_stages_enabled and not uploaded_video:
            st.error("Please upload a video file first! Video is required for Transcribe or Extract Frames stages.")
            return
            
        # Create output folder
        output_folder = "output"
        os.makedirs(output_folder, exist_ok=True)
        
        # Save uploaded video to output folder if needed
        if initial_stages_enabled:
            video_path = os.path.join(output_folder, uploaded_video.name)
            with open(video_path, "wb") as f:
                f.write(uploaded_video.getbuffer())

        # Create progress containers
        progress_bar = st.progress(0)
        status_text = st.empty()

        # Create checklist container
        st.markdown("### Processing Steps:")
        checklist_cols = st.columns(2)
        with checklist_cols[0]:
            checklist_items = {
                "transcribe": st.empty(),
                "extract_frames": st.empty(),
                "remove_unmeaningful_frames": st.empty(),
                "remove_duplicates": st.empty(),
            }
        with checklist_cols[1]:
            checklist_items.update({
                "summarize_transcript": st.empty(),
                "generate_image_summary": st.empty(),
                "create_pdf": st.empty(),
                "cleanup": st.empty(),
            })
        
        # Initialize checklist
        for key in checklist_items:
            checklist_items[key].markdown("⬜ " + key.replace("_", " ").title())
        
        results = {'status': 'started'}
        
        try:
            # Check if all stages are enabled
            all_stages_enabled = all(stages.values())
            
            # Clean output folder if all stages are enabled or if initial stages are enabled
            if all_stages_enabled or stages["transcribe"] or stages["extract_frames"]:
                status_text.text("Cleaning output folder...")
                st.warning("⚠️ Output folder will be cleaned and all existing files will be removed.")
                clean_output_folder(output_folder)
                if stages["extract_frames"]:
                    with open(video_path, "wb") as f:
                        f.write(uploaded_video.getbuffer())
            else:
                st.info("ℹ️ Using existing files in output folder where available.")

            # Handle transcript
            if stages["transcribe"]:
                if uploaded_transcript:
                    transcript_path = os.path.join(output_folder, "transcript.txt")
                    with open(transcript_path, "wb") as f:
                        f.write(uploaded_transcript.getbuffer())
                    checklist_items["transcribe"].markdown("✅ Using Uploaded Transcript")
                else:
                    status_text.text("Transcribing video...")
                    progress_bar.progress(10)
                    transcript_path = transcribe_video(video_path, output_folder)
                    checklist_items["transcribe"].markdown("✅ Generated Transcript")
            else:
                # Try to use existing transcript
                transcript_path = os.path.join(output_folder, "transcript.txt")
                if not os.path.exists(transcript_path):
                    st.error("No transcript found! Enable transcription or upload a transcript.")
                    return
                checklist_items["transcribe"].markdown("⏭️ Using Existing Transcript")

            results['transcript_path'] = transcript_path

            # Extract frames
            if stages["extract_frames"]:
                status_text.text("Detecting scenes...")
                progress_bar.progress(25)
                num_scenes = extract_frames(
                    video_path=video_path,
                    output_folder=output_folder,
                    skip_frames=frame_skip,
                    ssim_threshold=ssim_threshold
                )
                results['num_scenes_detected'] = num_scenes
                checklist_items["extract_frames"].markdown(f"✅ Extract Frames ({num_scenes} scenes)")
            else:
                checklist_items["extract_frames"].markdown("⏭️ Using Existing Frames")
            
            # Remove unmeaningful scenes
            if stages["remove_unmeaningful"]:
                status_text.text("Analyzing scenes for meaningful content...")
                progress_bar.progress(40)
                meaningful_images = remove_unmeaningful_frames(
                    folder_path=output_folder,
                    prompt=st.session_state.remove_unmeaningful_frames_prompt
                )
                results['num_meaningful_images'] = len(meaningful_images)
                checklist_items["remove_unmeaningful_frames"].markdown(f"✅ Analyze Content ({len(meaningful_images)} meaningful)")
            else:
                checklist_items["remove_unmeaningful_frames"].markdown("⏭️ Skipped Content Analysis")
        
            # Remove duplicate scenes
            if stages["remove_duplicates"]:
                status_text.text("Removing duplicate scenes...")
                progress_bar.progress(55)
                unique_scenes = remove_duplicate_frames_gpt(
                    folder_path=output_folder,
                    prompt=st.session_state.duplicate_frames_detection_prompt
                )
                results['num_unique_scenes'] = len(unique_scenes)
                checklist_items["remove_duplicates"].markdown(f"✅ Remove Duplicates ({len(unique_scenes)} unique)")
            else:
                checklist_items["remove_duplicates"].markdown("⏭️ Skipped Duplicate Removal")
            
            # Summarize transcript
            if stages["summarize_transcript"]:
                status_text.text("Summarizing transcript...")
                progress_bar.progress(70)
                transcript_summary = summarize_transcript(
                    transcript_path=transcript_path,
                    prompt=st.session_state.transcript_summary_prompt
                )
                # Save transcript summary
                summary_path = os.path.join(output_folder, "transcript_summary.txt")
                with open(summary_path, "w", encoding="utf-8") as f:
                    f.write(transcript_summary)
                results['has_transcript_summary'] = bool(transcript_summary)
                checklist_items["summarize_transcript"].markdown("✅ Summarize Transcript")
            else:
                checklist_items["summarize_transcript"].markdown("⏭️ Skipped Transcript Summary")
                transcript_summary = None
            
            # Get image summaries
            if stages["generate_summaries"]:
                status_text.text("Generating image summaries...")
                progress_bar.progress(85)
                image_summaries = get_image_summaries(
                    output_folder=output_folder,
                    transcript_summary=transcript_summary,
                    prompt=st.session_state.image_summary_prompt
                )
                # Save image summaries
                summaries_path = os.path.join(output_folder, "image_summaries.txt")
                with open(summaries_path, "w", encoding="utf-8") as f:
                    for image_file, summary in image_summaries:
                        f.write(f"Image: {image_file}\n")
                        f.write(f"Summary: {summary}\n")
                        f.write("-" * 50 + "\n")
                results['num_image_summaries'] = len(image_summaries)
                checklist_items["generate_image_summary"].markdown(f"✅ Generate Summaries ({len(image_summaries)} images)")
            else:
                checklist_items["generate_image_summary"].markdown("⏭️ Skipped Image Summaries")
                image_summaries = []
            
            # Create PDF report
            if stages["create_pdf"]:
                status_text.text("Creating PDF report...")
                progress_bar.progress(95)
                pdf_path = os.path.join(output_folder, "notes.pdf")
                create_pdf_report(
                    image_summaries=image_summaries,
                    transcript_summary=transcript_summary,
                    output_folder=output_folder,
                    output_pdf=pdf_path
                )
                results['pdf_generated'] = True
                checklist_items["create_pdf"].markdown("✅ Create PDF Report")
            else:
                checklist_items["create_pdf"].markdown("⏭️ Skipped PDF Creation")
            
            # Cleanup if enabled
            if stages["cleanup"]:
                status_text.text("Cleaning up temporary files...")
                try:
                    # Cleanup code here
                    checklist_items["cleanup"].markdown("✅ Cleanup Complete")
                except Exception as e:
                    checklist_items["cleanup"].markdown("❌ Cleanup Failed")
            else:
                checklist_items["cleanup"].markdown("⏭️ Cleanup Skipped")

            # Update final progress
            progress_bar.progress(100)
            status_text.text("Processing completed successfully!")
            results['status'] = 'completed'
            
            # Display results and download buttons
            st.success("Video processing completed!")
            st.write("### Processing Results:")
            for key, value in results.items():
                if key != 'status':
                    st.write(f"**{key}:** {value}")
            
            # Provide download links
            st.write("### Download Files")
            col1, col2 = st.columns(2)
            
            with col1:
                # Create zip file of complete output
                zip_path = os.path.join(output_folder, "complete_output.zip")
                with zipfile.ZipFile(zip_path, 'w') as zipf:
                    for root, dirs, files in os.walk(output_folder):
                        for file in files:
                            # Skip the zip file itself and the uploaded video file
                            if file != "complete_output.zip" and not file.endswith(('.mp4', '.avi', '.mov')):
                                file_path = os.path.join(root, file)
                                arcname = os.path.relpath(file_path, output_folder)
                                zipf.write(file_path, arcname)
                
                with open(zip_path, "rb") as f:
                    st.download_button(
                        label="📦 Download Complete Output",
                        data=f,
                        file_name="complete_output.zip",
                        mime="application/zip",
                        help="Download all files (transcripts, summaries, images, PDF) except the original video"
                    )
            
            with col2:
                with open(pdf_path, "rb") as f:
                    st.download_button(
                        label="📄 Download PDF Notes Only",
                        data=f,
                        file_name="notes.pdf",
                        mime="application/pdf",
                        help="Download only the final PDF report"
                    )
                    
        except Exception as e:
            progress_bar.progress(100)
            status_text.text("Processing failed!")
            st.error(f"Error during processing: {str(e)}")
            results['status'] = 'failed'
            results['error'] = str(e)
            
            # Mark the failed step with a red X
            for key, item in checklist_items.items():
                current_text = item.markdown
                if isinstance(current_text, str) and "✅" not in current_text:
                    item.markdown(f"❌ {key.replace('_', ' ').title()} (Failed)")

if __name__ == "__main__":
    create_streamlit_app() 
 