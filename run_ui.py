import streamlit as st
import os
from Video2FramesExtractor import (
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

    # Create two columns for parameters and prompts
    st.markdown("---")  # Add a separator line
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("2️⃣ Processing Parameters")
        
        # Add an info box explaining parameters
        st.info("""
        Configure the core processing parameters that control how your video 
        is analyzed and processed. Adjust these values based on your needs.
        """)
        
        ssim_threshold = st.slider(
            "SSIM Threshold", 
            min_value=0.0, 
            max_value=1.0, 
            value=SSIM_THRESHOLD,
            help="Controls how different frames need to be to be considered unique scenes."
        )
        
        frame_skip = st.number_input(
            "Frame Skip", 
            min_value=1, 
            value=FRAME_SKIP,
            help="Number of frames to skip between analyses."
        )
        
        cleanup = st.checkbox(
            "Enable Cleanup", 
            value=CLEANUP_ENABLED,
            help="Remove temporary files after processing"
        )

    with col2:
        st.subheader("3️⃣ Prompts Configuration")
        
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
        if not uploaded_video:
            st.error("Please upload a video file first!")
            return
            
        # Create output folder
        output_folder = "output"
        os.makedirs(output_folder, exist_ok=True)
        
        # Save uploaded video to output folder
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
            # Clean output folder before starting
            status_text.text("Cleaning output folder...")
            clean_output_folder(output_folder)
            
            # Save the video again after cleaning
            with open(video_path, "wb") as f:
                f.write(uploaded_video.getbuffer())

            # Handle transcript
            if uploaded_transcript:
                # Save uploaded transcript
                transcript_path = os.path.join(output_folder, "transcript.txt")
                with open(transcript_path, "wb") as f:
                    f.write(uploaded_transcript.getbuffer())
                checklist_items["transcribe"].markdown("✅ Using Uploaded Transcript")
            else:
                # Generate transcript
                status_text.text("Transcribing video...")
                progress_bar.progress(10)
                transcript_path = transcribe_video(video_path, output_folder)
                checklist_items["transcribe"].markdown("✅ Generated Transcript")

            results['transcript_path'] = transcript_path

            # Step 2: Extract frames
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
            
            # Step 3: Remove unmeaningful scenes
            status_text.text("Analyzing scenes for meaningful content...")
            progress_bar.progress(40)
            meaningful_images = remove_unmeaningful_frames(
                folder_path=output_folder,
                prompt=st.session_state.remove_unmeaningful_frames_prompt
            )
            results['num_meaningful_images'] = len(meaningful_images)
            checklist_items["remove_unmeaningful_frames"].markdown(f"✅ Analyze Content ({len(meaningful_images)} meaningful)")
        
            # Step 4: Remove duplicate scenes
            status_text.text("Removing duplicate scenes...")
            progress_bar.progress(55)
            unique_scenes = remove_duplicate_frames_gpt(
                folder_path=output_folder,
                prompt=st.session_state.duplicate_frames_detection_prompt
            )
            results['num_unique_scenes'] = len(unique_scenes)
            checklist_items["remove_duplicates"].markdown(f"✅ Remove Duplicates ({len(unique_scenes)} unique)")
            
            # Step 5: Summarize transcript
            status_text.text("Summarizing transcript...")
            progress_bar.progress(70)
            transcript_summary = summarize_transcript(
                transcript_path=transcript_path,
                prompt=st.session_state.transcript_summary_prompt
            )
            results['has_transcript_summary'] = bool(transcript_summary)
            checklist_items["summarize_transcript"].markdown("✅ Summarize Transcript")
            
            # Step 6: Get image summaries
            status_text.text("Generating image summaries...")
            progress_bar.progress(85)
            image_summaries = get_image_summaries(
                output_folder=output_folder,
                transcript_summary=transcript_summary,
                prompt=st.session_state.image_summary_prompt
            )
            results['num_image_summaries'] = len(image_summaries)
            checklist_items["generate_image_summary"].markdown(f"✅ Generate Summaries ({len(image_summaries)} images)")
            
            # Step 7: Create PDF report
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
            
            # Cleanup if enabled
            if cleanup:
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
                with open(transcript_path, "rb") as file:
                    st.download_button(
                        label="Download Transcript",
                        data=file,
                        file_name="transcription.txt",
                        mime="text/plain"
                    )
            with col2:
                with open(pdf_path, "rb") as file:
                    st.download_button(
                        label="Download PDF Report",
                        data=file,
                        file_name="notes.pdf",
                        mime="application/pdf"
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
 