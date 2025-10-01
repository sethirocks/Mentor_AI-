# Mentor_AI–

AI-powered roadmap & assistant for students to discover important university knowledge they don’t know they need.

## 🗂 Organizational Structure

This project is organized across three main tools:

### 📦 GitHub Repository
Source code, scripts, documentation, and issue tracking are maintained here.  
We use branches, pull requests, and GitHub Projects to organize tasks.

---

### 📄 Google Docs  
[Shared document for writing research notes, planning, meeting summaries, and discussion of ideas](https://docs.google.com/document/d/1y1kVfFjQbXq8OdFGCSOu9GP_EXO3aulRecfcXGN_ks/edit?usp=sharing)

---

### 💬 Discord Server  
[Main channel for team communication, quick updates, screen sharing, and daily coordination](https://discord.gg/p9fqusES)

---

Each team member uses their preferred IDE (e.g., **PyCharm** or **VS Code**).  
Tasks are created and assigned via GitHub Issues, with status updates managed through the GitHub Project Board.

## Technical Setup

Mentor_AI is designed to act as a personalized assistant for university students by combining peer-submitted tips with official university information. T
### Tech Stack Overview

- **Frontend**: Static HTML/CSS/JS with embedded student tip form  
- **Backend**: Python (FastAPI or Flask)  
- **LLM Integration**: OpenAI API (e.g., GPT 3.5/4) via HTTPS requests  
- **Database**: ChromaDB (lightweight vector store)  
- **Scraping**: BeautifulSoup + Requests (official h-da.de only)  
- **Visualization**: Obsidian mind map (via API or markdown export)  
- **Conflict Detection**: Phase 2 feature to flag contradictory information  

### System Modules

#### 1. Student Tip Collection

Students submit information via a web form:
- Fields: semester, issue type, tip description
- Tips are parsed and stored in a structured format for downstream use

#### 2. Web Scraper

- Collects official data from h-da.de
- Tags each entry with metadata like topic and semester
- Scheduled or on-demand execution

#### 3. Unified Knowledge Base

- Combines both sources (tips + scraped content)
- Schema: `topic`, `semester`, `source`, `content`
- Enables downstream modules to access curated insights

#### 4. AI Chatbot (Discovery Feed)

- Starts by asking for semester and program (e.g., "1st semester Informatics at h_da")
- Returns a curated discovery feed based on user context:
  - Exam registration rules
  - Deadlines
  - Available electives
  - Key regulations
  - Mentoring links and study tips
- Switches to open QA mode after initial suggestions

#### 5. Interactive Network Graph

- Uses only student-submitted tips
- Visual map: parent node = semester, child nodes = categorized tips
- Implemented using Obsidian (via plugin or markdown link mapping)

#### 6. Conflict Detection Engine (Phase 2)

- If two entries refer to the same topic but differ in content:
  - Entry is flagged for contradiction
  - Can be shown to users or logged for review
  - Helps address information asymmetry from unofficial vs. official sources

---

### High-Level Data Flow
<img width="664" height="266" alt="Screenshot 2025-10-01 at 16 10 09" src="https://github.com/user-attachments/assets/879d351d-5320-4820-8ad1-b8ef9698de71" />

