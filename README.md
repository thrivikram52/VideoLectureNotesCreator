# Video Lecture Notes Creator

A Streamlit-based application that processes video lectures to automatically generate structured notes with key frames and summaries.

## Features

- 🎥 Video Processing
  - Supports MP4, AVI, and MOV formats
  - Automatic transcription generation
  - Optional manual transcript upload
  - Intelligent frame extraction and analysis

- 📄 Output Generation
  - Creates a Document report combining visual and text summaries
  - Includes both transcript and key frame analysis
  - Downloadable transcript and final report

## Requirements

- Python 3.6+

brew install tesseract

## Installation

1. Clone the repository or download the source code.
2. Create a virtual environment on Mac as follows

python -m venv VideoLectureNotesCreator
source VideoLectureNotesCreator/bin/activate

On Windows
python -m venv VideoLectureNotesCreator
VideoLectureNotesCreator\Scripts\activate


3. Install the required dependencies:
pip install -r requirements.txt

## Usage
Export open AI API Key on terminal
export OPENAI_API_KEY={KEY}

Run the streamlit app
streamlit run run_ui.py


2. Configure Processing Parameters:
   - **SSIM Threshold** (0.0-1.0): Controls scene detection sensitivity
   - **Frame Skip**: Number of frames to skip during analysis
   - **Cleanup**: Toggle temporary file removal

3. Customize AI Prompts (Optional):

4. Upload and Process:
   - Upload your video file
   - Optionally upload a pre-existing transcript
   - Click "Process" to start the pipeline

## Processing Pipeline

1. **Video Upload & Transcription**
   - Processes uploaded video
   - Generates or uses provided transcript

2. **Frame Analysis**
   - Extracts key frames
   - Removes unmeaningful content
   - Eliminates duplicate scenes

3. **Content Generation**
   - Summarizes transcript
   - Generates descriptions for key frames
   - Creates comprehensive PDF report

4. **Output**
   - Downloadable transcript
   - Doc report with annotated frames and summaries

## Output Structure

## Requirements

- Python 3.7+
- Streamlit
- OpenAI API access
- FFmpeg (for video processing)
- Additional dependencies listed in requirements.txt

## Notes

- Processing time varies based on video length and quality
- Internet connection required for AI processing
- Ensure sufficient disk space for temporary files
- API keys should be configured in environment variables


Logic:

#### Step-by-Step Process

1. **Initial Notes Creation** 
   - Process raw transcript
   - Extract main topics and concepts
   - Create structured outline
   - Highlight key terminology

2. **Missing Content Analysis**
   - Review initial notes for gaps
   - Identify unexplained concepts
   - Check for logical flow issues
   - Suggest additional examples/clarifications

3. **Notes Combination**
   - Merge initial notes with missing content
   - Ensure coherent structure
   - Add visual elements and formatting
   - Create clear section breaks

4. **Student Review**
   - AI student role reviews notes
   - Identifies unclear sections
   - Generates clarifying questions
   - Checks for completeness

5. **Q&A Enhancement**
   - Generate answers to student questions
   - Add Q&A section to notes
   - Summarize key points from Q&A
   - Format for readability

6. **Final Output**
   - Combine notes with extracted frames
   - Add visual annotations
   - Create downloadable formats
   - Generate metadata

### AI Roles

- **Teacher Assistant**
  - Creates initial notes
  - Identifies missing content
  - Combines and enhances notes
  - Answers student questions

- **Student Assistant**
  - Reviews notes for clarity
  - Generates relevant questions
  - Ensures comprehensibility
  - Validates completeness

Need to install brew install pandoc