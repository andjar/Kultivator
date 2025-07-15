# Installation

## Prerequisites

1. **Python 3.10+**
2. **Ollama** with a compatible model (e.g., gemma3, llama3.2)
3. **Git** (for versioning)

## Installation Steps

1. **Clone the repository:**
   ```bash
   git clone https://github.com/andjar/kultivator
   cd kultivator
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Start Ollama** (if not already running):
   ```bash
   ollama serve
   ```

4. **Pull a compatible model:**
   ```bash
   ollama pull gemma3
   # or
   ollama pull llama3.2
   ```
