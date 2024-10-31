# Video2FramesExtractor

Video2FramesExtractor is a Python program that detects and extracts unique scenes from a video file. It uses structural similarity index (SSIM) to identify significant changes between frames, allowing for efficient scene detection and extraction.

## Features

- Automatic scene detection based on structural similarity
- Customizable sensitivity and frame skip settings
- Progress bar for visual feedback during processing
- Outputs individual frames as PNG images
- Supports various video formats

## Requirements

- Python 3.6+
- OpenCV
- NumPy
- scikit-image
- tqdm

brew install tesseract

## Installation

1. Clone the repository or download the source code.
2. Create a virtual environment on Mac as follows

python -m venv Video2FramesExtractor
source Video2FramesExtractor/bin/activate

On Windows
python -m venv Video2FramesExtractor
Video2FramesExtractor\Scripts\activate


3. Install the required dependencies:
pip install -r requirements.txt

## Usage

1. Place your video file in the same directory as the script, or update the `video_path` variable in the script with the path to your video file.

2. Run the script:
python Video2FramesExtractor.py

Run the same functionality from UI using below command
python Video2FramesExtractorUI.py

3. The script will process the video and save detected scenes as PNG images in the `scenes` folder.

## Configuration

You can adjust the following parameters in the script to fine-tune the scene detection:

- `SSIM_THRESHOLD`: Adjust this value to change the sensitivity of scene detection. Lower values will detect more subtle changes. 
For Academic Videos which has animation prefer to give 0.8 as SSIM Threshold
For Zoom meetings explaining about some architecture prefer to give 0.65 as SSIM Threshold
It varies between -1 to 1

- `FRAME_SKIP`: Change this value to process frames at different intervals. Higher values will speed up processing but may miss short scenes.
- `MIN_SCENE_DURATION`: Set the minimum time (in seconds) between saved frames to avoid saving too similar scenes.


