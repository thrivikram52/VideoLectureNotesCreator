# Constants and thresholds
OUTPUT_VIDEO_PATH = 'video.mp4'
OUTPUT_FOLDER = 'scenes'
OUTPUT_PDF = 'presentation_slides.pdf'
TRANSCRIPT_PATH = 'transcription.txt'
SSIM_THRESHOLD = 0.65
FRAME_SKIP = 300
CLEANUP_ENABLED = False

# System Prompts
TRANSCRIPT_SYSTEM_PROMPT = """As an instructor, generate a comprehensive summary that captures the key points and insights \
from the provided material. Focus on explaining concepts clearly and engagingly, ensuring that the content is informative \
and easy to understand for the intended audience. Highlight important details, examples, and any relevant applications \
without referring to the source material. Aim for a concise yet thorough overview that could serve as a teaching aid.\
Use markdown formatting for structure, including headers and numbering points where appropriate."""

IMAGE_SUMMARY_SYSTEM_PROMPT = TRANSCRIPT_SYSTEM_PROMPT  # Using the same prompt for consistency

MEANINGFUL_CONTENT_PROMPT = """Definition of Meaningful Content:\
Meaningful content includes any text, diagrams, charts, images (beyond participant profile pictures), \
tables, or visual elements that provide valuable information or insights. This content should contribute \
directly to the understanding or learning points you want to cover in your lecture notes. \
Examples include slides with data, key points, or visual aids that can be explained further in the notes. \
What is Not Considered Meaningful Content:\
Slides that only display people's profile pictures, names, or generic visuals from the meeting \
(e.g., video feeds or participant screens), as well as blank slides, are classified as No Meaningful Content. \
These slides do not provide valuable material for lecture notes.\
Task:\
Analyze the provided slide and classify it as Contains Meaningful Content if it includes \
text, diagrams, or other elements that can be elaborated upon in lecture notes. \
If the slide contains only people's images or does not have useful content, \
classify it as false otherwise true. You give only TRUE or FALSE(case sensitive). Do not give explanation.\
"""

DUPLICATE_DETECTION_PROMPT = """Compare these two images and determine if they show the same content or slide. \
Consider text, diagrams, and visual elements. Respond with only 'TRUE' if they are duplicates or 'FALSE' if they are different. \
No explanation needed."""

TRANSCRIPT_USER_PROMPT = """Please summarize the following transcript, ensuring that no details are missed. \
:\n\n{text}"""

IMAGE_SUMMARY_USER_PROMPT = """Based on this transcript summary:\n\n{transcript}\n\n\
Please provide a brief description of what is shown in the image {image}. \
Focus on how it relates to the content of the transcript"""
