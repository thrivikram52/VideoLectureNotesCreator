# Teacher related constants
TEACHER_INSTRUCTIONS = """You are an expert teacher creating comprehensive lecture notes. 
Include the following elements wherever applicable:

1. Visual Elements:
   - Flow charts using mermaid syntax:
     ```mermaid
     flowchart LR
         A[Start] --> B[Process]
         B --> C[End]
     ```
   
   - Sequence diagrams for processes:
     ```mermaid
     sequenceDiagram
         participant A as Component A
         participant B as Component B
         A->>B: Request
         B->>A: Response
     ```
   
   - Class diagrams for object-oriented concepts:
     ```mermaid
     classDiagram
         class ClassName{
             +attributes
             +methods()
         }
     ```

2. Comparative Elements:
   - Use tables for comparisons
   - Use bullet points for pros/cons
   
3. Examples:
   - Provide practical examples in code blocks
   - Include real-world examples
   - Add sample scenarios
   - Show step-by-step solutions

4. Key Concepts:
   - Highlight important definitions in blockquotes
   - Use callouts for important notes

5. Write python code for the examples

6. Write the summary at the end

7. After summary write list of technical terms with definitions

Format the notes with clear headings, subheadings, and maintain consistent formatting throughout."""

INITIAL_NOTES_PROMPT = """Create detailed lecture notes from this transcript.
Follow the formatting guidelines to include:
1. Mermaid diagrams where processes or flows are discussed
2. Comparison tables for contrasting concepts
3. Code examples where applicable
4. Clear pros and cons lists
5. Visual representations of key concepts

Transcript:
{transcript}"""

MISSING_CONTENT_PROMPT = """Analyze the initial notes and identify ONLY missing major points and sections.
Focus on these aspects:

1. Missing Technical Elements:
   - Missing technical explanations
   - Absent mathematical foundations
   - Missing architectural details
   - Lacking complexity analysis
   - Missing algorithms/pseudocode

2. Missing Visual Elements:
   - Required but missing diagrams
   - Missing flowcharts
   - Missing sequence diagrams
   - Missing architecture diagrams
   - Missing state diagrams

3. Missing Comparative Elements:
   - Missing comparison tables
   - Absent trade-off analysis
   - Missing alternative approaches
   - Missing performance comparisons

4. Missing Implementation Details:
   - Missing code examples
   - Missing best practices
   - Missing error handling
   - Missing optimization techniques

5. Missing Real-world Context:
   - Missing industry examples
   - Missing case studies
   - Missing practical applications
   - Missing production considerations"""

COMBINE_NOTES_PROMPT = """Combine the enhanced notes with the missing content.
Follow these rules:
1. Keep all original content
2. Insert missing technical elements in appropriate sections
3. Add missing comparisons after related concepts
4. Add implementation examples where relevant
5. Add visual elements where they best explain the concept
6. Maintain clear section separation with headers"""

QA_PROMPT = """Please provide detailed answers to these student questions:
1. Give thorough explanations
2. Include relevant examples
3. Reference concepts from the lecture
4. Use clear and concise language

Format each answer as:
Q: [Question]
A: [Detailed answer]"""

# Student related constants
STUDENT_INSTRUCTIONS = """You are a student reviewing lecture content with no prior knowledge.
Review the provided lecture notes and:
1. Identify unclear concepts
2. Point out areas needing more examples
3. Ask about confusing technical details
4. Request clarification on complex processes
5. Identify terms needing better definitions

Format your response as numbered questions.
If everything is clear, respond with "SATISFIED"."""

REVIEW_NOTES_PROMPT = """Review these lecture notes and list any unclear points or questions:

{notes}"""

# File related constants
INITIAL_NOTES_FILE = "step1_initial_notes.md"
MISSING_CONTENT_FILE = "step2_missing_content.md"
COMBINED_NOTES_FILE = "step3_combined_notes.md"
STUDENT_QUESTIONS_FILE = "step4_student_questions.md"
FINAL_NOTES_FILE = "lecture_notes.md"
METADATA_FILE = "metadata.json"
DEBUG_FOLDER = "debug"

# API related constants
DEFAULT_MODEL = "gpt-4-turbo-preview"
MAX_RETRIES = 10
INITIAL_RETRY_DELAY = 1.0
BACKOFF_FACTOR = 1.5 

# Constants and thresholds
OUTPUT_VIDEO_PATH = 'video.mp4'
OUTPUT_FOLDER = 'scenes'
OUTPUT_PDF = 'presentation_slides.pdf'
TRANSCRIPT_PATH = 'transcription.txt'
SSIM_THRESHOLD = 0.8
FRAME_SKIP = 30
CLEANUP_ENABLED = False
