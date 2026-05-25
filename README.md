[![Need a Full-Stack AI Dev? Let's talk.](https://img.shields.io/badge/Need%20a%20Full--Stack%20AI%20Dev%3F%20Let%27s%20talk.-%231E90FF?style=for-the-badge&logo=github&logoColor=white)](https://linkedin.com/in/RyanMaxie)

# 📚 Learning Tutor AI

> An intelligent, adaptive learning assistant that transforms any subject into a personalized curriculum, powered by local LLMs via Ollama.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](http://makeapullrequest.com)
[![Tech: Python](https://img.shields.io/badge/Tech-Python-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Tech: Streamlit](https://img.shields.io/badge/Tech-Streamlit-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![AI: Ollama](https://img.shields.io/badge/AI-Ollama-000000?logo=ollama&logoColor=white)](https://ollama.com/)

---

## 🧐 What is this?

**AI Learning Tutor** is a privacy-first, adaptive learning system designed to help you master any subject through interactive dialogue. Unlike static courses, it leverages **local LLMs (Llama 3.2)** to generate dynamic questions, provide explanations tailored to your level, and automatically adjust difficulty based on your performance. Whether you're studying programming, languages, or professional certifications, it provides a focused environment for deep learning without your data ever leaving your machine.

## 🛠️ Tech Stack

This project is a full-stack Python application built for local execution and data privacy.

| Component           | Technology           | Key Libraries/Frameworks                 |
| :------------------ | :------------------- | :--------------------------------------- |
| **Frontend**        | Streamlit            | Interactive UI, Session Management       |
| **Backend**         | FastAPI / SQLAlchemy | Business Logic, Database ORM             |
| **LLM Runtime**     | Ollama               | Llama 3.2, Local Inference               |
| **AI Framework**    | LangChain            | RAG, Prompt Templates, LLM Orchestration |
| **Storage**         | SQLite / ChromaDB    | Relational Data, Vector Embeddings       |
| **Data Processing** | Python               | PyPDF2, pdfplumber, python-docx          |

## 🚀 Quick Start

The following instructions are optimized for a Linux environment (**Ubuntu/Debian**).

### Prerequisites

You must have **Python 3.10+** and **Ollama** installed. A minimum of **8GB RAM** and **10GB disk space** is recommended for optimal performance.

1.  **Clone the repository**

    ```bash
    git clone https://github.com/RyanMaxiemus/learning-tutor.git
    cd learning-tutor
    ```

2.  **Set up Environment**

    Create a virtual environment and install the required dependencies.

    ```bash
    python3 -m venv venv
    source venv/bin/activate
    # For full features (recommended):
    pip install -r requirements.txt
    ```

3.  **Configure Ollama**

    Ensure Ollama is running and pull the default model.

    ```bash
    ollama pull llama3.2
    ```

4.  **Initialize Database**

    Prepare the local SQLite database for session and progress tracking.

    ```bash
    python3 -m backend.database.init_db
    ```

5.  **Run the Application**

    Launch the Streamlit interface.

    ```bash
    streamlit run frontend/app.py
    ```

    Navigate to `http://localhost:8501` in your browser to start your first session.

## 📸 Preview

![AI Learning Tutor Screenshot](/assets/images/ai-learning-tutor-screenshot.png)

## 🤝 Contributing

We believe the best way to learn is together! Whether you're fixing a bug, improving a prompt, or adding a new feature, your contributions are welcome.

1.  **Open an Issue:** Found a bug or have a feature idea? Let's discuss it in the issues first to ensure it aligns with the project roadmap.
2.  **Fork and Branch:** Fork the repo and create a descriptive branch (e.g., `feat/add-flashcards`).
3.  **Code and Commit:** Keep it clean! Follow PEP 8 for Python and write descriptive commit messages.
4.  **Submit a PR:** Submit your Pull Request against the `main` branch. We'll review it and get it merged.

Let's build the future of personalized education, one session at a time.
