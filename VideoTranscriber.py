import whisper
import os

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