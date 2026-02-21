Install Ollama



Download Ollama:



👉 https://ollama.com/download



Download AI model



Open PowerShell and run:



ollama pull llama3.1:8b



Open project folder in PowerShell



Go to project folder:



cd Desktop\\legal-ai-agent



Create virtual environment

python -m venv venv



Activate environment

venv\\Scripts\\activate



Install dependencies

pip install -r requirements.txt



Create vector database (IMPORTANT)

cd ipc-vector-db\\scripts

python create\_faiss\_ipc.py



Run Django server



Go back:



cd ..\\..\\legal\_agent



Then run:



python manage.py migrate

python manage.py runserver



Open app



Open browser:



&nbsp;http://127.0.0.1:8000

