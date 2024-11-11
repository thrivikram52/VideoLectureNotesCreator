from openai import OpenAI
import json
import time
import os
from typing import Dict, Optional
import asyncio
from constants import (
    TEACHER_INSTRUCTIONS,
    STUDENT_INSTRUCTIONS,
    INITIAL_NOTES_PROMPT,
    MISSING_CONTENT_PROMPT,
    COMBINE_NOTES_PROMPT,
    REVIEW_NOTES_PROMPT,
    QA_PROMPT,
    INITIAL_NOTES_FILE,
    MISSING_CONTENT_FILE,
    COMBINED_NOTES_FILE,
    STUDENT_QUESTIONS_FILE,
    DEBUG_FOLDER,
    DEFAULT_MODEL,
    MAX_RETRIES,
    INITIAL_RETRY_DELAY,
    BACKOFF_FACTOR
)

class Assistant:
    """Base class for OpenAI Assistants"""
    def __init__(self, client: OpenAI, role: str, instructions: str):
        self.assistant = client.beta.assistants.create(
            name=f"Lecture {role}",
            instructions=instructions,
            model="gpt-4o-mini"
        )
        self.thread = client.beta.threads.create()
        self.client = client

    async def send_message(self, content: str) -> str:
        """Send message and get response asynchronously"""
        # Create message
        self.client.beta.threads.messages.create(
            thread_id=self.thread.id,
            role="user",
            content=content
        )
        
        # Create run
        run = self.client.beta.threads.runs.create(
            thread_id=self.thread.id,
            assistant_id=self.assistant.id
        )
        
        # Check status with exponential backoff
        max_retries = 10
        retry_delay = 1
        
        for attempt in range(max_retries):
            run_status = self.client.beta.threads.runs.retrieve(
                thread_id=self.thread.id,
                run_id=run.id
            )
            
            if run_status.status == "completed":
                messages = self.client.beta.threads.messages.list(
                    thread_id=self.thread.id
                )
                return messages.data[0].content[0].text.value
                
            elif run_status.status == "failed":
                raise Exception("Assistant run failed")
                
            await asyncio.sleep(retry_delay)
            retry_delay *= 1.5  # Exponential backoff
            
        raise TimeoutError("Assistant response timed out")

class Teacher(Assistant):
    """Teacher Assistant for creating lecture notes"""
    def __init__(self, client: OpenAI):
        super().__init__(client, "Teacher", TEACHER_INSTRUCTIONS)

    async def create_initial_notes(self, transcript: str) -> str:
        """Create initial lecture notes with enhanced visual and comparative elements"""
        return await self.send_message(
            INITIAL_NOTES_PROMPT.format(transcript=transcript)
        )
    
    async def add_missing_content(self, initial_notes: str) -> str:
        """Analyze initial notes and provide only missing major points and enhancements"""
        return await self.send_message(f"""
            Initial Notes:
            {initial_notes}
            
            {MISSING_CONTENT_PROMPT}""")

    async def combine_notes(self, enhanced_notes: str, missing_content: str) -> str:
        """Combine enhanced notes with missing content in a structured way"""
        return await self.send_message(
            COMBINE_NOTES_PROMPT.format(enhanced_notes=enhanced_notes, missing_content=missing_content)
        )

    async def answer_student_questions(self, student_questions: str) -> str:
        """Generate answers for student questions"""
        return await self.send_message(
            QA_PROMPT.format(student_questions=student_questions)
        )

    def format_qa_section(self, questions: str, answers: str) -> str:
        """Format Q&A section with enhanced visual elements"""
        return f"""
---

# Questions and Answers

> 💭 Student Questions and Teacher Responses

{answers}

---

📝 Summary of Key Points from Q&A:
"""

class Student(Assistant):
    """Student Assistant for reviewing lecture notes"""
    def __init__(self, client: OpenAI):
        super().__init__(client, "Student", STUDENT_INSTRUCTIONS)
    
    async def review_notes(self, notes: str) -> str:
        """Review lecture notes and provide questions"""
        return await self.send_message(
            REVIEW_NOTES_PROMPT.format(notes=notes)
        )

class LectureNotesCreator:
    """Main class for creating lecture notes"""
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
        self.teacher = Teacher(self.client)
        self.student = Student(self.client)

    async def create_notes(self, transcript_path: str, output_folder: str) -> None:
        """Create lecture notes with clear separation of initial and missing content"""
        try:
            print("\n📚 Starting lecture notes creation...")
            
            # Step 1: Initial notes creation
            print("\n👨‍🏫 Teacher creating initial notes...")
            transcript = self._read_file(transcript_path)
            initial_notes = await self.teacher.create_initial_notes(transcript)
            self._save_intermediate("step1_initial_notes.md", initial_notes, output_folder)
            
            # Step 2: Identify missing content
            print("\n👨‍🏫 Teacher identifying missing content...")
            missing_content = await self.teacher.add_missing_content(initial_notes)
            self._save_intermediate("step2_missing_content.md", missing_content, output_folder)
            
            # Step 3: Create final combined notes
            print("\n👨‍🏫 Teacher combining notes...")
            combined_notes = await self.teacher.combine_notes(initial_notes, missing_content)
            self._save_intermediate("step3_combined_notes.md", combined_notes, output_folder)
            
            # Step 4: Student review
            print("\n👨‍🎓 Student reviewing notes...")
            student_questions = await self.student.review_notes(combined_notes)
            self._save_intermediate("step4_student_questions.md", student_questions, output_folder)
            
            # Step 5: Add Q&A section
            if "SATISFIED" not in student_questions:
                print("\n👨‍🏫 Teacher adding Q&A section...")
                qa_answers = await self.teacher.answer_student_questions(student_questions)
                final_notes_with_qa = combined_notes + "\n\n" + self.teacher.format_qa_section(student_questions, qa_answers)
            else:
                print("\n✅ No questions from student. Notes are clear.")
                final_notes_with_qa = combined_notes
            
            # Save final output
            self._save_output(final_notes_with_qa, output_folder)
            print(f"\n💾 All files saved to: {output_folder}")
            
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            raise

    @staticmethod
    def _read_file(path: str) -> str:
        """Read content from file"""
        with open(path, 'r') as f:
            return f.read()

    @staticmethod
    def _save_intermediate(filename: str, content: str, output_folder: str) -> None:
        """Save intermediate results to debug folder"""
        debug_folder = os.path.join(output_folder, "debug")
        os.makedirs(debug_folder, exist_ok=True)
        
        # Save content
        filepath = os.path.join(debug_folder, filename)
        with open(filepath, 'w') as f:
            f.write(content)
            
        # Save timestamp
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        metadata_path = os.path.join(debug_folder, f"{os.path.splitext(filename)[0]}_metadata.json")
        metadata = {
            "filename": filename,
            "created_at": timestamp,
            "file_size": len(content)
        }
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

    @staticmethod
    def _save_output(content: str, output_folder: str) -> None:
        """Save final output files"""
        os.makedirs(output_folder, exist_ok=True)
        
        # Save final notes
        with open(os.path.join(output_folder, "lecture_notes.md"), 'w') as f:
            f.write(content)
        
        # Save metadata
        metadata = {
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "version": "1.0",
            "files_generated": {
                "debug/step1_initial_notes.md": "Initial notes from transcript",
                "debug/step2_missing_content.md": "Missing content",
                "debug/step3_combined_notes.md": "Final combined notes",
                "debug/step4_student_questions.md": "Student questions",
                "lecture_notes.md": "Final lecture notes with Q&A"
            }
        }
        with open(os.path.join(output_folder, "metadata.json"), 'w') as f:
            json.dump(metadata, f, indent=2)