release: python -m spacy download en_core_web_sm
web: gunicorn app:app --bind 0.0.0.0:$PORT
