from FastAPI import FastAPI

app = FastAPI()

@app.get("/hello")
def say_hello():
    return {"message": "안녕하세요, FastAPI에 오신 걸 환영합니다!"}
    