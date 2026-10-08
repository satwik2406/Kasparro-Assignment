"""
Entity and metadata extractor from raw resume text.
Extracts name, email, phone, github profile, linkedin, skills, and project blocks.
"""

import re
from pathlib import Path
from typing import List, Optional, Tuple
from src.models import ParsedResume
from src.parsers.pdf_parser import PDFParser
from src.parsers.docx_parser import DOCXParser
from src.parsers.txt_parser import TXTParser


EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_REGEX = re.compile(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}")
GITHUB_REGEX = re.compile(r"(?:https?://)?(?:www\.)?github\.com/([a-zA-Z0-9\-_]+)(?:/[a-zA-Z0-9\-_.]+)?", re.IGNORECASE)
GITHUB_HANDLE_REGEX = re.compile(r"(?:github(?:\.com)?\s*[:|/@\-]?\s*@?)([a-zA-Z0-9\-_]+)", re.IGNORECASE)
LINKEDIN_REGEX = re.compile(r"(?:https?://)?(?:www\.)?linkedin\.com/in/([a-zA-Z0-9\-_%]+)", re.IGNORECASE)

KNOWN_SKILLS = [
    # AI / Agentic / RAG
    "LangChain", "LangGraph", "LlamaIndex", "Google ADK", "CrewAI", "AutoGen",
    "RAG", "Retrieval-Augmented Generation", "Vector Search", "ChromaDB", "Chroma",
    "Pinecone", "Qdrant", "Weaviate", "FAISS", "Embeddings", "SentenceTransformers",
    "Tool Calling", "Function Calling", "Multi-Agent", "Evaluation", "Ragas", "TruLens",
    "PyTorch", "TensorFlow", "HuggingFace", "Transformers", "Fine-tuning", "LoRA",
    # Python & Backend
    "Python", "FastAPI", "AsyncIO", "Flask", "Django", "PostgreSQL", "Postgres",
    "Redis", "SQLAlchemy", "Alembic", "Celery", "RabbitMQ", "Kafka", "REST API",
    "GraphQL", "Pydantic", "gRPC",
    # Cloud & DevOps
    "Docker", "Kubernetes", "GCP", "Google Cloud", "AWS", "Azure", "CI/CD",
    "GitHub Actions", "Terraform", "Linux",
    # Frontend & Fullstack
    "React", "Next.js", "TypeScript", "JavaScript", "Node.js", "HTML", "CSS", "Tailwind",
    # Non-Python stacks (for filter analysis)
    "Java", "Spring Boot", "Kotlin", "C++", "C#", ".NET", "PHP", "Go", "Rust"
]


def extract_candidate_name(raw_text: str, file_path: Path) -> str:
    """Extract candidate name from header lines or fallback to filename."""
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    
    # Check top 5 lines for a clean name candidate
    for line in lines[:5]:
        # Filter out common header words
        low = line.lower()
        if any(h in low for h in ["resume", "curriculum", "vitae", "cv", "page 1", "email", "phone", "http", "@"]):
            continue
        words = line.split()
        # Typically candidate names are 2 to 4 capitalized words, no punctuation or numbers
        if 2 <= len(words) <= 4 and all(w[0].isupper() for w in words if w.isalpha()) and not any(c.isdigit() for c in line):
            if len(line) < 40:
                return line

    # Fallback to file name cleaning
    stem = file_path.stem
    # Replace candidate_01_John_Doe -> John Doe
    clean = re.sub(r"^(candidate[_\-\s]?\d+[_\-\s]*)", "", stem, flags=re.IGNORECASE)
    clean = re.sub(r"[_\-]+", " ", clean).strip()
    if clean and len(clean.split()) >= 2:
        return clean.title()
    elif clean:
        return clean.title()

    return stem.replace("_", " ").title()


def extract_github_info(raw_text: str) -> Tuple[Optional[str], Optional[str]]:
    """Extract GitHub profile URL and parsed username."""
    # First search for full URL
    url_match = GITHUB_REGEX.search(raw_text)
    if url_match:
        username = url_match.group(1).strip()
        # Exclude reserved words
        if username.lower() not in ["features", "topics", "collections", "trending", "explore", "pricing"]:
            return f"https://github.com/{username}", username

    # Fallback to handle pattern e.g., "GitHub: @satwik"
    handle_match = GITHUB_HANDLE_REGEX.search(raw_text)
    if handle_match:
        username = handle_match.group(1).strip()
        if username.lower() not in ["features", "topics", "collections", "trending", "explore", "pricing"]:
            return f"https://github.com/{username}", username

    return None, None


def extract_skills_and_keywords(raw_text: str) -> List[str]:
    """Identify matched technical skills present in resume text."""
    matched = []
    text_lower = raw_text.lower()

    for skill in KNOWN_SKILLS:
        skill_lower = skill.lower()
        # Boundary matching for short words like RAG, GCP, AWS, Go
        if len(skill) <= 4:
            pattern = rf"\b{re.escape(skill_lower)}\b"
            if re.search(pattern, text_lower):
                matched.append(skill)
        else:
            if skill_lower in text_lower:
                matched.append(skill)

    return list(dict.fromkeys(matched))


def parse_resume_file(file_path: Path) -> ParsedResume:
    """Parse resume from file with complete error isolation."""
    ext = file_path.suffix.lower()
    raw_text = ""
    is_malformed = False
    parse_error = None

    try:
        if ext == ".pdf":
            parser = PDFParser()
            raw_text = parser.extract_text(file_path)
        elif ext in [".docx", ".doc"]:
            parser = DOCXParser()
            raw_text = parser.extract_text(file_path)
        elif ext in [".txt", ".md"]:
            parser = TXTParser()
            raw_text = parser.extract_text(file_path)
        else:
            raise ValueError(f"Unsupported file format: {ext}")
    except Exception as e:
        is_malformed = True
        parse_error = str(e)
        return ParsedResume(
            file_path=str(file_path),
            file_name=file_path.name,
            raw_text="",
            candidate_name=file_path.stem.replace("_", " ").title(),
            is_malformed=True,
            parse_error=parse_error
        )

    # Extract metadata from text
    email_match = EMAIL_REGEX.search(raw_text)
    email = email_match.group(0) if email_match else None

    phone_match = PHONE_REGEX.search(raw_text)
    phone = phone_match.group(0) if phone_match else None

    github_url, github_username = extract_github_info(raw_text)

    linkedin_match = LINKEDIN_REGEX.search(raw_text)
    linkedin_url = f"https://linkedin.com/in/{linkedin_match.group(1)}" if linkedin_match else None

    candidate_name = extract_candidate_name(raw_text, file_path)
    skills = extract_skills_and_keywords(raw_text)

    return ParsedResume(
        file_path=str(file_path),
        file_name=file_path.name,
        raw_text=raw_text,
        candidate_name=candidate_name,
        email=email,
        phone=phone,
        github_url=github_url,
        github_username=github_username,
        linkedin_url=linkedin_url,
        extracted_skills=skills,
        is_malformed=False,
        parse_error=None
    )
