from flask import Flask, render_template, request, jsonify
import json
import re
import os

app = Flask(__name__)

# Load rules
try:
    with open("rules.json", "r", encoding="utf-8") as f:
        rules = json.load(f)
except:
    rules = []

# Manual shloka splits for demo
shloka_manual_splits = {
    "sarve bhavantu sukhinaḥ": ["sar", "ve", "bha", "van", "tu", "suk", "hi", "naḥ"],
    "rāma rāma rāmeti": ["rā", "ma", "rā", "ma", "rā", "me", "ti"]
}

# -------------------------------
# Syllable classification
# -------------------------------
def classify_syllable(syl):
    long_vowels = ["ā", "ī", "ū", "e", "o", "ai", "au"]
    s = syl.lower()
    if any(lv in s for lv in long_vowels):
        return "1"
    if re.search(r"[aiuṛḷ]([kgcjtdpbmnśṣsrlvyhwṁḥ])$", s):
        return "1"
    return "0"

# -------------------------------
# Convert shloka -> syllables
# -------------------------------
def shloka_to_syllables(text):
    if text in shloka_manual_splits:
        return shloka_manual_splits[text]
    s = re.sub(r"[^a-zāīūṛḷeoaiuṁḥ\s]", "", text.lower())
    s = re.sub(r"\s+", " ", s).strip()
    consonants = "kgcjtdpbmnśṣsrlvyhw"
    vowels = "aiueoāīūṛḷ"
    pattern = f"[{consonants}]?[{vowels}]"
    syllables = re.findall(pattern, s)
    return syllables

# -------------------------------
# Convert shloka -> pattern
# -------------------------------
def shloka_to_pattern(text):
    syllables = shloka_to_syllables(text)
    pattern = "".join(classify_syllable(syl) for syl in syllables)
    return pattern, syllables

# -------------------------------
# Match pattern -> chandas
# -------------------------------
def identify_chandas(pattern):
    for r in rules:
        if r["pattern"] == pattern:
            return r["name"]
    return None

# -------------------------------
# Routes
# -------------------------------
@app.route("/")
def index():
    return render_template("index.html", rules=rules)

@app.route("/identify", methods=["POST"])
def identify():
    data = request.json or {}
    shloka = data.get("shloka", "")
    if not shloka:
        return jsonify({"error": "No shloka provided"}), 400

    pattern, syllables = shloka_to_pattern(shloka)
    chandas = identify_chandas(pattern)
    return jsonify({
        "shloka": shloka,
        "syllables": syllables,
        "pattern": pattern,
        "chandas": chandas
    })

@app.route("/addrule", methods=["POST"])
def addrule():
    data = request.json or {}
    pattern = data.get("pattern")
    name = data.get("name")
    if not pattern or not name:
        return jsonify({"error": "Both pattern and name required"}), 400
    # Add new rule dynamically
    rules.append({"pattern": pattern, "name": name})
    # Optionally save to rules.json
    with open("rules.json", "w", encoding="utf-8") as f:
        json.dump(rules, f, ensure_ascii=False, indent=2)
    return jsonify({"message": f"Rule '{name}' added for pattern {pattern}."})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Use $PORT if available, otherwise 5000
    app.run(host="0.0.0.0", port=port)
