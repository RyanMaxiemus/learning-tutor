# 📚 AI Learning Tutor

An intelligent, adaptive learning assistant powered by locally-run LLMs via Ollama. Study any subject with AI-generated questions, personalized difficulty adjustment, and optional document-based learning from your own materials.

## ✨ Features

- 🎯 **Adaptive Learning**: Difficulty automatically adjusts based on your performance
- 📖 **Multi-Subject Support**: Learn anything from programming to languages to certifications
- 📄 **Document Import**: Upload PDFs, DOCX, or text files to study your own materials
- 📊 **Progress Tracking**: Detailed analytics and mastery levels for each topic
- 🔄 **Session Management**: Restart sessions, change difficulty, export/import progress
- 🔒 **Privacy-First**: Everything runs locally on your machine - no data leaves your computer
- 💾 **Data Portability**: Export and import your learning progress

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- [Ollama](https://ollama.com/download) installed and running
- 8GB+ RAM recommended
- 10GB+ free disk space

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/ryanmaxiemus/learning-tutor.git
cd learning-tutor
```

2. **Create a virtual environment**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install Ollama and download a model**
```bash
# Install Ollama from https://ollama.com/download

# Pull the LLM model (this may take a few minutes)
ollama pull llama3.2
```

4. **Install Python dependencies**

**Option A: Full Installation (with document processing)**
```bash
pip install --no-cache-dir -r requirements.txt
```

**Option B: Minimal Installation (faster, no document import)**
```bash
pip install --no-cache-dir -r requirements-minimal.txt
```

5. **Initialize the database**
```bash
python -m backend.database.init_db
```

6. **Run the application**
```bash
streamlit run frontend/app.py
```

7. **Open your browser**
Navigate to `http://localhost:8501`

## 📖 Usage

### Starting a Study Session

1. Select **Study Session** from the sidebar
2. Enter a subject (e.g., "Python Programming")
3. Enter a topic (e.g., "Control Flow")
4. Choose difficulty level (Beginner/Intermediate/Advanced)
5. Click **Start Session**

### Importing Study Materials

1. Go to **Study Materials** tab
2. Click **Upload New Material**
3. Select your PDF, DOCX, or TXT file
4. Assign it to a subject
5. The app will process and create questions from your material

### Restarting a Session

If you start at the wrong difficulty:
- Click **Restart Session** button in the sidebar
- Choose new difficulty level
- Your progress is saved for analytics

### Exporting/Importing Progress

**Export:**
1. Go to **Settings** → **Export Progress**
2. Download the JSON file
3. Keep it safe as a backup

**Import:**
1. Go to **Settings** → **Import Progress**
2. Select your JSON file
3. Choose merge strategy if conflicts exist

## 🛠️ Tech Stack

- **LLM Runtime**: Ollama (llama3.2)
- **Backend**: FastAPI, SQLAlchemy, Pydantic
- **Frontend**: Streamlit
- **Database**: SQLite
- **Vector DB**: ChromaDB (for document search)
- **Embeddings**: sentence-transformers
- **Document Processing**: PyPDF2, pdfplumber, python-docx

## 📁 Project Structure
```
learning-tutor/
├── backend/
│   ├── api/              # FastAPI routes (future expansion)
│   ├── models/           # SQLAlchemy database models
│   ├── services/         # Business logic (LLM, progress tracking, material processing)
│   ├── database/         # Database setup and initialization
│   └── prompts/          # LLM system prompts
├── frontend/
│   └── app.py           # Streamlit UI
├── data/
│   ├── uploads/         # User-uploaded study materials
│   └── chroma_db/       # Vector database for document search
├── config/
│   └── settings.py      # Application configuration
├── requirements.txt     # Python dependencies
└── README.md
```

## ⚙️ Configuration

Edit `config/settings.py` or create a `.env` file:
```env
# Ollama Settings
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2

# Session Settings
SESSION_DURATION_MINUTES=30
QUESTIONS_PER_SESSION=15

# Database
DATABASE_URL=sqlite:///data/learning_tutor.db
```

## 🐛 Troubleshooting

### "No space left on device" during pip install
```bash
pip cache purge
pip install --no-cache-dir -r requirements.txt
```

### Ollama connection errors
```bash
# Check if Ollama is running
ollama list

# Restart Ollama service
# On macOS/Linux: restart the Ollama app
# On Windows: restart Ollama from system tray
```

### Database errors
```bash
# Reset the database
rm data/learning_tutor.db
python -m backend.database.init_db
```

### Slow response times
- Use a smaller model: `ollama pull llama3.2:1b`
- Update `OLLAMA_MODEL=llama3.2:1b` in settings
- Close other applications using RAM

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [Ollama](https://ollama.com/) for local LLM inference
- UI powered by [Streamlit](https://streamlit.io/)
- Embeddings by [sentence-transformers](https://www.sbert.net/)

## 📧 Contact

Your Name - [@RyanMaxiemus](https://twitter.com/RyanMaxiemus)

Project Link: [https://github.com/RyanMaxiemus/learning-tutor](https://github.com/ryanmaxiemus/learning-tutor)

---

**Note**: This application runs completely offline. Your learning data never leaves your machine, ensuring complete privacy.
```