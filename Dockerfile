# Usa imagem oficial do Playwright (já tem Chrome/Firefox e Python)
FROM mcr.microsoft.com/playwright/python:v1.41.0-jammy

WORKDIR /app

# Copia os requisitos e instala
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o código do repositório para a pasta /app
COPY . .

# Expõe a porta do Streamlit
EXPOSE 8501

# Comando de inicialização
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
