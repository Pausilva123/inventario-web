import webbrowser
from threading import Timer
from app import app

def abrir_navegador():
    webbrowser.open_new("http://127.0.0.1:5000")

if __name__ == "__main__":
    Timer(1, abrir_navegador).start()
    app.run()

