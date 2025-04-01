import streamlit as st
import os
import tkinter as tk
from tkinter import filedialog
import zipfile
from datetime import datetime
import asyncio
import nest_asyncio

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

# Core functionality imports
from VideoTranscriber import transcribe_video
from VideoFrameExtractor import extract_frames
from LectureNotesCreator import LectureNotesCreator
from Utils import (
    get_output_folder,
    extract_scene_number
)
from constants import (
    SSIM_THRESHOLD,
    FRAME_SKIP,
    TEACHER_INSTRUCTIONS,
    INITIAL_NOTES_PROMPT,
    MISSING_CONTENT_PROMPT,
    COMBINE_NOTES_PROMPT,
    QA_PROMPT,
    STUDENT_INSTRUCTIONS,
    REVIEW_NOTES_PROMPT
)
from DocumentCreator import DocumentCreator

def select_folder():
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    root.wm_attributes('-topmost', 1)  # Bring the dialog to the front
    folder_path = filedialog.askdirectory()
    return folder_path

def create_streamlit_app():
    st.set_page_config(page_title="Video Processing Pipeline", layout="wide")
    st.title("Video Processing Pipeline")

    # API Key Configuration
    with st.sidebar:
        st.header("🔑 API Configuration")
        api_key = st.text_input(
            "Enter OpenAI API Key",
            type="password",
            help="Your OpenAI API key is required for transcript summarization and image analysis",
            value=st.session_state.get('api_key', '')
        )
        
        if api_key:
            st.session_state['api_key'] = api_key
            os.environ['OPENAI_API_KEY'] = api_key
            st.success("✅ API Key set successfully!")
        else:
            st.warning("⚠️ Please enter your OpenAI API Key to use GPT features")

    # Check for API key before proceeding
    if not api_key:
        st.error("Please enter your OpenAI API Key in the sidebar to continue")
        return

    # Initialize tab state if not exists
    if 'active_tab' not in st.session_state:
        st.session_state.active_tab = "Phase 1"

    # Create tabs for the two phases
    tab1, tab2 = st.tabs(["📽️ Phase 1: Frame Extraction & Review", "📄 Phase 2: Generate Notes"])
    
    # Set active tab
    if st.session_state.active_tab == "Phase 2":
        tab2.active = True

    with tab1:
        st.header("Phase 1: Frame Extraction & Manual Review")
        
        # Step 1: Video Upload
        st.markdown("---")
        st.subheader("1️⃣ Upload Video")
        uploaded_video = st.file_uploader(
            "Select your video file (MP4, AVI, MOV or WEBM) *", 
            type=['mp4', 'avi', 'mov', 'webm']
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
                    value=SSIM_THRESHOLD,
                    help="Lower values will extract more frames. Recommended: 0.5-0.8"
                )
            
            with col2:
                frame_skip = st.number_input(
                    "Frame Skip Rate",
                    min_value=1,
                    max_value=300,
                    value=FRAME_SKIP,
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
                    
                    
                    # Create columns for the navigation section
                    nav_col1, nav_col2 = st.columns([2, 1])
                    with nav_col1:
                        st.info("👉 Click on the 'Phase 2: Generate Notes' tab above to proceed with note generation.")
                else:
                    st.warning("No frames found. Please extract frames first.")

    with tab2:
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
            # Teacher Prompts Section
            st.markdown("### 👨‍🏫 Teacher Prompts")
            
            teacher_prompts = {
                "Instructions": st.text_area(
                    "Teacher Instructions",
                    value=TEACHER_INSTRUCTIONS,
                    key="teacher_instructions",
                    help="Base instructions for the teacher role"
                ),
                "Initial Notes": st.text_area(
                    "Initial Notes Creation",
                    value=INITIAL_NOTES_PROMPT,
                    key="initial_notes_prompt",
                    help="Prompt for creating the first draft of notes"
                ),
                "Missing Content": st.text_area(
                    "Missing Content Analysis",
                    value=MISSING_CONTENT_PROMPT,
                    key="missing_content_prompt",
                    help="Prompt for identifying missing content"
                ),
                "Combine Notes": st.text_area(
                    "Notes Combination",
                    value=COMBINE_NOTES_PROMPT,
                    key="combine_notes_prompt",
                    help="Prompt for combining and refining notes"
                ),
                "Q&A": st.text_area(
                    "Question Answering",
                    value=QA_PROMPT,
                    key="qa_prompt",
                    help="Prompt for answering student questions"
                )
            }

            # Student Prompts Section
            st.markdown("### 👨‍🎓 Student Prompts")
            
            student_prompts = {
                "Instructions": st.text_area(
                    "Student Instructions",
                    value=STUDENT_INSTRUCTIONS,
                    key="student_instructions",
                    help="Base instructions for the student role"
                ),
                "Review Notes": st.text_area(
                    "Notes Review",
                    value=REVIEW_NOTES_PROMPT,
                    key="review_notes_prompt",
                    help="Prompt for reviewing and questioning notes"
                )
            }

        # Process Button
        if st.button("▶️ Generate Notes", type="primary"):
            progress = st.progress(0)
            status_text = st.empty()
            
            try:
                # Create checklist for tracking
                checklist_items = {
                    "transcribe": st.empty(),
                    "process": st.empty(),
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
                    status_text.text("Generating transcript... This may take a few minutes...")
                    progress.progress(10)
                    video_path = os.path.join(output_folder, uploaded_video.name)
                    
                    if not os.path.exists(video_path):
                        with open(video_path, "wb") as f:
                            f.write(uploaded_video.getbuffer())
                    
                    transcript_path = transcribe_video(
                        video_path=video_path,
                        output_folder=output_folder
                    )
                    checklist_items["transcribe"].markdown("✅ Generated transcript")

                # 2. Process with LectureNotesCreator
                status_text.text("Processing transcript and generating notes...")
                progress.progress(50)
                
                # Initialize LectureNotesCreator with API key and create notes
                notes_creator = LectureNotesCreator(api_key)
                
                # Create and run the async task
                async def process_notes():
                    await notes_creator.create_notes(
                        transcript_path=transcript_path,
                        output_folder=output_folder
                    )
                
                # Run the async function
                asyncio.run(process_notes())
                
                checklist_items["process"].markdown("✅ Generated notes")
                
                # 3. Create PDF Report
                status_text.text("Creating PDF report...")
                progress.progress(75)
                
                pdf_creator = DocumentCreator()
                doc_path = pdf_creator.create_document(output_folder)
                checklist_items["create_pdf"].markdown("✅ Created PDF report")
                
                # Complete
                progress.progress(100)
                status_text.text("✅ Processing complete!")
                
                # Show download section
                st.markdown("---")
                st.subheader("📥 Download Results")
                
                if os.path.exists(doc_path):
                    with open(doc_path, "rb") as doc_file:
                        st.download_button(
                            label="📄 Download Notes (Word)",
                            data=doc_file,
                            file_name="lecture_notes.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                        )
                
            except Exception as e:
                st.error(f"❌ Error during processing: {str(e)}")
                status_text.text("Processing failed!")
                progress.progress(0)

if __name__ == "__main__":
    create_streamlit_app()
 