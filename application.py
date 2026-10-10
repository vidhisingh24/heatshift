from flask import Flask, render_template

# Elastic Beanstalk's Python platform looks for a WSGI callable named `application`.
application = Flask(__name__)


@application.get("/")
def index():
    return render_template("index.html")


@application.get("/health")
def health():
    return "ok"


if __name__ == "__main__":
    application.run(debug=True)
