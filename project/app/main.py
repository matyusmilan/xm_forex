# project/app/main.py

from fastapi import FastAPI, Depends


app = FastAPI()


@app.get("/health-check/")
def health_check():
    return {"message": "OK"}
