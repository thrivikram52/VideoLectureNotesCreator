import os
import shutil

def get_output_folder(video_filename):
    """
    Creates and returns output folder path based on video filename
    Example: 'lecture1.mp4' -> 'lecture1'
    
    Args:
        video_filename (str): Name of the video file
        
    Returns:
        str: Path to the output folder
    """
    # Remove file extension and any special characters
    base_name = os.path.splitext(video_filename)[0]
    # Create a valid folder name (remove special characters)
    safe_name = "".join(c for c in base_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
    # Create directory if it doesn't exist
    os.makedirs(safe_name, exist_ok=True)
    return safe_name

def extract_scene_number(filename):
    """
    Helper function to safely extract scene number from filename
    
    Args:
        filename (str): Name of the file (e.g., 'scene_1.png')
        
    Returns:
        int: Scene number, or 0 if extraction fails
    """
    try:
        # Extract number between 'scene_' and '.png'
        return int(filename.split('_')[1].split('.')[0])
    except (IndexError, ValueError):
        return 0 