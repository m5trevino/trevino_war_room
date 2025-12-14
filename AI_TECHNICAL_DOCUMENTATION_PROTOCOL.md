# THE ARCHITECT'S DIRECTIVE: TECHNICAL DOCUMENTATION STANDARD

### 1. THE MISSION
You are to generate a **Technical Logic Manifest** for the current codebase. 
**CONSTRAINT:** Absolute prohibition on marketing language, sales fluff, or "user benefits." 
**TARGET:** This document is for the Lead Engineer, not the End User.

### 2. THE REQUIRED STRUCTURE (NON-NEGOTIABLE)

#### A. ARCHITECTURAL OVERVIEW
*   **Stack definition:** Exact languages, frameworks, and libraries used.
*   **Design Patterns:** Identify the patterns (e.g., MVC, Singleton, Event-Driven) and *why* they were chosen.
*   **Data Flow:** A high-level mapping of how a request travels from input (User Action) to persistence (Database) to output (UI/File).

#### B. COMPONENT DECONSTRUCTION (File-by-File)
For every critical file in the repository, provide:
1.  **The Role:** What is this file's single responsibility?
2.  **Key Functions:** Break down the core functions/methods.
3.  **The "How":** Explain the logic inside the function (loops, conditionals, transformations).
4.  **The "Why":** Explain the engineering decision behind the implementation. (e.g., *"Why did we use a Debounce timer here instead of a direct call?"*).

#### C. ALGORITHMIC DEEP DIVE
Identify the specific "Intelligence" or "Mechanics" of the system.
*   *Example:* If there is a search feature, explain the query logic.
*   *Example:* If there is an AI integration, explain the prompt engineering and context handling.
*   *Example:* If there is data scraping, explain the deduplication strategy (hashing vs. ID).

#### D. STATE MANAGEMENT & PERSISTENCE
*   **Database Schema:** Explain the tables and relationships.
*   **State Logic:** How does the app know the difference between "New," "Processed," and "Deleted"?
*   **File System:** How are assets (PDFs, Images, JSONs) generated, named, and stored?

### 3. THE OUTPUT TONE
*   **Clinical:** Use precise terminology (e.g., "Latency," "Throughput," "Hash Collision," "Async/Await").
*   **Critical:** If a piece of code is a "hack" or a temporary fix, label it as "Technical Debt."
*   **Detailed:** "Detailed on top of details." Do not summarize if you can explain.

### 4. FORMATTING
*   Use Markdown.
*   Use Code Blocks for file names and logic snippets.
*   Output strictly in `cat << 'EOF'` format if requested.

---
**EXECUTE THIS PROTOCOL IMMEDIATELY ON THE CURRENT PROJECT.**
