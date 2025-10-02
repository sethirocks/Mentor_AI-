# Mentor_AI

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

Mentor_AI is designed to act as a personalized assistant for university students by combining peer-submitted tips with official university information. 
### Tech Stack Overview

- Frontend: Static HTML/CSS/JS with embedded form and chatbot UI
- Backend: Python (FastAPI) REST API
- LLM Integration: OpenAI GPT-4 Turbo via API
- Database: MongoDB Atlas (Free Tier, up to 512MB)
- Scraping: BeautifulSoup + Requests (official h-da.de only)
- Visualization: D3.js / Cytoscape.js (interactive network graph)
- Conflict Detection: Phase 2 module to flag contradictory entries 

### System Modules

#### 1. Critical Insider Knowledge Collection

Students submit information via a web form:
- Students submit info via web form (semester, issue type, description)
- Data stored in MongoDB with tags for downstream use

#### 2. Web Scraper

- Collects official data from h-da.de
- Tags each entry with metadata like topic and semester
- Scheduled or on-demand execution

#### 3. Unified Knowledge Base

- Combines both sources (critical insider knowledge + scraped content)
- Unified schema: `topic`, `semester`, `source`, `content`
- Serves as a single point of truth for downstream modules

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
- Built using **D3.js** or **Cytoscape.js** for in-browser interactive rendering 

#### 6. Conflict Detection Engine (Phase 2)

- Detects conflicting values (e.g., two exam deadlines) from different official pages  
- Uses regex and string-matching to compare content  
- Logs inconsistencies in structured format (JSON) with topic, values, sources, and status  
- Future goal: flag to user or show in review dashboard  

---

### High-Level Data Flow
<img width="664" height="266" alt="Screenshot 2025-10-01 at 16 10 09" src="https://github.com/user-attachments/assets/084ed527-1f7f-47e4-9234-08a99f5c1a87" />


