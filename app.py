from flask import Flask, render_template, request
from chandas import analyze_text

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

if __name__ == "__main__":
    app.run(debug=True)