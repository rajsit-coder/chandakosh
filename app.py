
from flask import Flask, render_template, request
from chandas import analyze_text
import os
app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    sample = "असतो मा सद्गमय । तमसो मा ज्योतिर्गमय । मृत्योर् मा अमृतं गमय ॥"
    if request.method == "POST":
        text = request.form.get("shloka", "").strip()
        prefer_script = request.form.get("script", "auto")
        result = analyze_text(text, prefer_script)
    return render_template("index.html", result=result, sample=sample)


@app.route("/help")
def help_page():
    return render_template("help.html")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
