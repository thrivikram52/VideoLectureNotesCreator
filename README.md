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

- Python 3.7+
- Homebrew (for macOS)

## System Dependencies

For macOS:
```bash
# Install Tesseract for OCR
brew install tesseract

# Install Tkinter for file dialogs
brew install python-tk@3.13  # Use appropriate version matching your Python

# Install Pandoc for document conversion
brew install pandoc
```

For Windows:
- Install Tesseract OCR from the official installer
- Python's tkinter usually comes pre-installed

## Installation

1. Clone the repository or download the source code.

2. Create a virtual environment:

On macOS/Linux:
```bash
python -m venv VideoLectureNotesCreator
source VideoLectureNotesCreator/bin/activate
```

On Windows:
```bash
python -m venv VideoLectureNotesCreator
VideoLectureNotesCreator\Scripts\activate
```

3. Install the required dependencies:
```bash
# Upgrade pip and setuptools first
pip install --upgrade pip setuptools wheel

# Install the required packages
pip install -r requirements.txt

# Install additional required packages
pip install tk nest_asyncio
```

## Usage

1. Set up your OpenAI API Key:
```bash
# Option 1: Export as environment variable
export OPENAI_API_KEY={YOUR_API_KEY}

# Option 2: Create a .env file
echo "OPENAI_API_KEY=your_api_key_here" > .env
```

2. Run the streamlit app:
```bash
streamlit run run_ui.py
```

3. Configure Processing Parameters:
   - **SSIM Threshold** (0.0-1.0): Controls scene detection sensitivity
   - **Frame Skip**: Number of frames to skip during analysis
   - **Cleanup**: Toggle temporary file removal

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

## Notes

- Processing time varies based on video length and quality
- Internet connection required for AI processing
- Ensure sufficient disk space for temporary files
- API keys should be configured in environment variables

## Troubleshooting

Common issues and solutions:

1. **Tkinter Issues**:
   - If you get tkinter-related errors, ensure python-tk is installed for your Python version
   - On macOS M1/M2: `brew install python-tk@3.13` (adjust version as needed)

2. **Event Loop Errors**:
   - If you get asyncio event loop errors, the app uses nest_asyncio to handle them
   - This is automatically installed with the requirements

3. **OpenAI API Issues**:
   - Ensure your API key is correctly set
   - Check your API key has sufficient credits

4. **Performance Issues**:
   - Install watchdog for better performance:
     ```bash
     xcode-select --install  # macOS only
     pip install watchdog
     ```

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