from fastapi import FastAPI

app = FastAPI(title="Water Quality API")


@app.get("/")
def read_root():
    return {"message": "Water Quality Monitoring API is running"}
