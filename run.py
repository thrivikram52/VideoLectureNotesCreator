from Video2FramesExtractor import *
from config import *

def main(
    # File paths and processing parameters
    video_path=OUTPUT_VIDEO_PATH,
    output_folder=OUTPUT_FOLDER,
    ssim_threshold=SSIM_THRESHOLD,
    frame_skip=FRAME_SKIP,
    cleanup=CLEANUP_ENABLED,
    
    # System prompts
    transcript_system_prompt=TRANSCRIPT_SYSTEM_PROMPT,
    image_summary_system_prompt=IMAGE_SUMMARY_SYSTEM_PROMPT,
    
    # User prompts
    meaningful_content_prompt=MEANINGFUL_CONTENT_PROMPT,
    duplicate_detection_prompt=DUPLICATE_DETECTION_PROMPT,
    transcript_user_prompt=TRANSCRIPT_USER_PROMPT,
    image_summary_user_prompt=IMAGE_SUMMARY_USER_PROMPT
):
    """
    Main execution function for video processing pipeline
    
    Args:
        # File paths and processing parameters
        video_path (str): Path to input video file
        output_folder (str): Directory to save extracted scenes
        ssim_threshold (float): Threshold for structural similarity comparison
        frame_skip (int): Number of frames to skip during processing
        cleanup (bool): Whether to cleanup temporary files after processing
        
        # System prompts
        transcript_system_prompt (str): System prompt for transcript summarization
        image_summary_system_prompt (str): System prompt for image summarization
        
        # User prompts
        meaningful_content_prompt (str): Prompt for detecting meaningful content in images
        duplicate_detection_prompt (str): Prompt for detecting duplicate images
        transcript_user_prompt (str): Template for transcript summarization user prompt
        image_summary_user_prompt (str): Template for image summarization user prompt
    
    Returns:
        dict: Processing results containing paths and statistics
    """
    results = {
        'video_path': video_path,
        'output_folder': output_folder,
        'status': 'started'
    }
    
    try:
        # Create a context dictionary to pass prompts to functions
        context = {
            'transcript_system_prompt': transcript_system_prompt,
            'image_summary_system_prompt': image_summary_system_prompt,
            'meaningful_content_prompt': meaningful_content_prompt,
            'duplicate_detection_prompt': duplicate_detection_prompt,
            'transcript_user_prompt': transcript_user_prompt,
            'image_summary_user_prompt': image_summary_user_prompt
        }
        
        # Transcribe video
        print("Starting video transcription")
        transcript_path = transcribe_video(video_path)
        results['transcript_path'] = transcript_path

        # Perform scene detection
        print("Starting scene detection")
        num_scenes = extract_frames(
            video_path=video_path,
            output_folder=output_folder,
            skip_frames=frame_skip,
            ssim_threshold=ssim_threshold
        )
        print(f"Detected {num_scenes} unique scenes")
        results['num_scenes_detected'] = num_scenes
        
        # Get meaningful images with custom prompt
        meaningful_images = remove_unmeaningful_scenes(
            folder_path=output_folder,
            prompt=context['meaningful_content_prompt']
        )
        if not meaningful_images:
            raise ValueError("No meaningful images found")
        results['num_meaningful_images'] = len(meaningful_images)

        # Remove duplicate scenes using GPT Vision with custom prompt
        unique_scenes = remove_duplicate_scenes_gpt(
            folder_path=output_folder,
            prompt=context['duplicate_detection_prompt']
        )
        print(f"Unique scenes after removing duplicates: {len(unique_scenes)}")
        results['num_unique_scenes'] = len(unique_scenes)
        
        # Summarize transcript with custom prompts
        transcript_summary = summarize_transcript(
            './transcription.txt',
            system_prompt=context['transcript_system_prompt'],
            user_prompt=context['transcript_user_prompt']
        )
        if not transcript_summary:
            raise ValueError("Failed to generate transcript summary")
        results['has_transcript_summary'] = True

        # Get summaries for each meaningful image with custom prompts
        image_summaries = get_image_summaries(
            output_folder=output_folder,
            transcript_summary=transcript_summary,
            system_prompt=context['image_summary_system_prompt'],
            user_prompt=context['image_summary_user_prompt']
        )
        results['num_image_summaries'] = len(image_summaries)

        # Create PDF report
        create_pdf_report(
            image_summaries,
            transcript_summary,
            output_folder=output_folder
        )
        results['pdf_generated'] = True
        
        # Cleanup if requested
        if cleanup:
            try:
                if os.path.exists(transcript_path):
                    os.remove(transcript_path)
                # Optionally remove extracted scenes
                for image in os.listdir(output_folder):
                    os.remove(os.path.join(output_folder, image))
                os.rmdir(output_folder)
                results['cleanup_performed'] = True
            except Exception as e:
                print(f"Warning: Cleanup failed: {str(e)}")
                results['cleanup_performed'] = False

        results['status'] = 'completed'
        print("Main execution completed successfully")
        
    except Exception as e:
        error_message = f"Error during execution: {str(e)}"
        print(error_message, file=sys.stderr)
        results['status'] = 'failed'
        results['error'] = error_message
        raise

    return results


if __name__ == "__main__":
    try:
        # Example of using main function with custom parameters and prompts
        results = main(
            # File paths and processing parameters
            video_path=OUTPUT_VIDEO_PATH,
            output_folder=OUTPUT_FOLDER,
            ssim_threshold=SSIM_THRESHOLD,
            frame_skip=FRAME_SKIP,
            cleanup=CLEANUP_ENABLED,
            
            # Optionally override any prompts
            transcript_system_prompt=TRANSCRIPT_SYSTEM_PROMPT,
            image_summary_system_prompt=IMAGE_SUMMARY_SYSTEM_PROMPT,
            meaningful_content_prompt=MEANINGFUL_CONTENT_PROMPT,
            duplicate_detection_prompt=DUPLICATE_DETECTION_PROMPT,
            transcript_user_prompt=TRANSCRIPT_USER_PROMPT,
            image_summary_user_prompt=IMAGE_SUMMARY_USER_PROMPT
        )
        
        # Print results summary
        print("\nProcessing Results:")
        for key, value in results.items():
            print(f"{key}: {value}")
            
    except Exception as e:
        print(f"Error in main execution: {str(e)}", file=sys.stderr)
        sys.exit(1) 