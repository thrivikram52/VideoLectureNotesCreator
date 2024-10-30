import streamlit as st
import os
from Video2FramesExtractor import (
    transcribe_video,
    extract_frames,
    remove_unmeaningful_scenes,
    remove_duplicate_scenes_gpt,
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
            help="Controls how different frames need to be to be considered unique scenes. Higher values mean more similar frames might be kept."
        )
        
        frame_skip = st.number_input(
            "Frame Skip", 
            min_value=1, 
            value=FRAME_SKIP,
            help="Number of frames to skip between analyses. Higher values process faster but might miss some scenes."
        )
        
        cleanup = st.checkbox(
            "Enable Cleanup", 
            value=CLEANUP_ENABLED,
            help="Remove temporary files after processing is complete"
        )

    with col2:
        st.subheader("3️⃣ Prompts Configuration")
        
        st.info("""
        Customize the AI prompts used for different stages of processing. 
        Expand each section below to view and modify the prompts.
        """)
        
        # System Prompts in an expander
        with st.expander("🤖 System Prompts", expanded=False):
            st.markdown("**Configure how the AI understands its task**")
            transcript_system_prompt = st.text_area(
                "Transcript System Prompt", 
                value=TRANSCRIPT_SYSTEM_PROMPT,
                height=100,
                help="Guides the AI in how to summarize the transcript"
            )
            
            st.markdown("---")  # Separator
            
            image_summary_system_prompt = st.text_area(
                "Image Summary System Prompt", 
                value=IMAGE_SUMMARY_SYSTEM_PROMPT,
                height=100,
                help="Guides the AI in how to analyze images"
            )
        
        # Content Analysis Prompts
        with st.expander("🔍 Content Analysis Prompts", expanded=False):
            st.markdown("**Configure how content is analyzed and filtered**")
            meaningful_content_prompt = st.text_area(
                "Meaningful Content Detection", 
                value=MEANINGFUL_CONTENT_PROMPT,
                height=100,
                help="Helps identify meaningful content in scenes"
            )
            
            st.markdown("---")  # Separator
            
            duplicate_detection_prompt = st.text_area(
                "Duplicate Scene Detection", 
                value=DUPLICATE_DETECTION_PROMPT,
                height=100,
                help="Guides the detection of duplicate scenes"
            )
        
        # Summary Generation Prompts
        with st.expander("📝 Summary Generation Prompts", expanded=False):
            st.markdown("**Configure how summaries are generated**")
            transcript_user_prompt = st.text_area(
                "Transcript Summary", 
                value=TRANSCRIPT_USER_PROMPT,
                height=100,
                help="Template for generating transcript summaries"
            )
            
            st.markdown("---")  # Separator
            
            image_summary_user_prompt = st.text_area(
                "Image Summary", 
                value=IMAGE_SUMMARY_USER_PROMPT,
                height=100,
                help="Template for generating image descriptions"
            )

        # Add a "Reset Prompts" button with better styling
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🔄 Reset All Prompts to Default", use_container_width=True):
                transcript_system_prompt = TRANSCRIPT_SYSTEM_PROMPT
                image_summary_system_prompt = IMAGE_SUMMARY_SYSTEM_PROMPT
                meaningful_content_prompt = MEANINGFUL_CONTENT_PROMPT
                duplicate_detection_prompt = DUPLICATE_DETECTION_PROMPT
                transcript_user_prompt = TRANSCRIPT_USER_PROMPT
                image_summary_user_prompt = IMAGE_SUMMARY_USER_PROMPT
                st.experimental_rerun()

    # Add a separator before the process button
    st.markdown("---")
    
    # Center the process button and add output folder info
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.info("Files will be saved in the 'output' folder in the current directory")
        process_button = st.button("▶️ Start Processing", type="primary", use_container_width=True)

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
                "analyze_content": st.empty(),
                "remove_duplicates": st.empty(),
            }
        with checklist_cols[1]:
            checklist_items.update({
                "summarize_transcript": st.empty(),
                "generate_summaries": st.empty(),
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
            
            # Step 1: Transcribe video
            status_text.text("Transcribing video...")
            progress_bar.progress(10)
            transcript_path = transcribe_video(video_path, output_folder)
            results['transcript_path'] = transcript_path
            checklist_items["transcribe"].markdown("✅ Transcribe Video")
            
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
            meaningful_images = remove_unmeaningful_scenes(
                folder_path=output_folder,
                prompt=meaningful_content_prompt
            )
            results['num_meaningful_images'] = len(meaningful_images)
            checklist_items["analyze_content"].markdown(f"✅ Analyze Content ({len(meaningful_images)} meaningful)")
            
            # Step 4: Remove duplicate scenes
            status_text.text("Removing duplicate scenes...")
            progress_bar.progress(55)
            unique_scenes = remove_duplicate_scenes_gpt(
                folder_path=output_folder,
                prompt=duplicate_detection_prompt
            )
            results['num_unique_scenes'] = len(unique_scenes)
            checklist_items["remove_duplicates"].markdown(f"✅ Remove Duplicates ({len(unique_scenes)} unique)")
            
            # Step 5: Summarize transcript
            status_text.text("Summarizing transcript...")
            progress_bar.progress(70)
            transcript_summary = summarize_transcript(
                transcript_path,
                system_prompt=transcript_system_prompt,
                user_prompt=transcript_user_prompt
            )
            results['has_transcript_summary'] = bool(transcript_summary)
            checklist_items["summarize_transcript"].markdown("✅ Summarize Transcript")
            
            # Step 6: Get image summaries
            status_text.text("Generating image summaries...")
            progress_bar.progress(85)
            image_summaries = get_image_summaries(
                output_folder=output_folder,
                transcript_summary=transcript_summary,
                system_prompt=image_summary_system_prompt,
                user_prompt=image_summary_user_prompt
            )
            results['num_image_summaries'] = len(image_summaries)
            checklist_items["generate_summaries"].markdown(f"✅ Generate Summaries ({len(image_summaries)} images)")
            
            # Step 7: Create PDF report
            status_text.text("Creating PDF report...")
            progress_bar.progress(95)
            pdf_path = os.path.join(output_folder, "notes.pdf")
            create_pdf_report(
                image_summaries,
                transcript_summary,
                output_folder,
                output_pdf=pdf_path
            )
            results['pdf_generated'] = True
            checklist_items["create_pdf"].markdown("✅ Create PDF Report")
            
            # Update final progress
            progress_bar.progress(100)
            status_text.text("Processing completed successfully!")
            results['status'] = 'completed'
            
            # Display results
            st.success("Video processing completed!")
            st.write("### Processing Results:")
            for key, value in results.items():
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
                if "✅" not in item.markdown:
                    item.markdown(f"❌ {key.replace('_', ' ').title()} (Failed)")

if __name__ == "__main__":
    create_streamlit_app() 
 