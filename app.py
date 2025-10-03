from flask import Flask, render_template, request, jsonify
import re
import json
import os

app = Flask(__name__)

# -------------------------------
# Chandas patterns
# -------------------------------
rules = [
    { "pattern": "10101010", "name": "Anushtubh" },
    { "pattern": "10110101010", "name": "Trishtubh" },
    { "pattern": "101101101010", "name": "Jagati" },
    { "pattern": "10110110110110", "name": "Brihati" },
    { "pattern": "1011010101", "name": "Pankti" },
    { "pattern": "101101101", "name": "Shakvari" },
    { "pattern": "1011011011011010", "name": "Atijagati" },
    { "pattern": "01010110", "name": "Gayatri" },
    { "pattern": "10110110101", "name": "Upajati" },
    { "pattern": "11011011011011011", "name": "Mandakranta" },
    { "pattern": "10101101010110", "name": "Vasantatilaka" },
    { "pattern": "1011011011011011011", "name": "Shardulavikridita" },
    { "pattern": "101101101101101101101", "name": "Sragdhara" },
    { "pattern": "111000111000", "name": "Matrasamaka" }
]

# -------------------------------
# Manual shloka splits for common cases
# -------------------------------
shloka_manual_splits = {
    "sarve bhavantu sukhinaḥ": ["sar", "ve", "bha", "van", "tu", "suk", "hi", "naḥ"],
    "rāma rāma rāmeti": ["rā", "ma", "rā", "ma", "rā", "me", "ti"],
    "om tapasvī jñānī namah": ["o", "ta", "pa", "svī", "jā", "nī", "na", "mah"]
}

# -------------------------------
# Improved syllable classification
# -------------------------------
def classify_syllable(syl):
    """
    Returns '1' for guru (long) and '0' for laghu (short)
    """
    long_vowels = ["ā", "ī", "ū", "e", "o", "ai", "au"]
    s = syl.lower()

    # Long vowel → Guru
    if any(lv in s for lv in long_vowels):
        return "1"

    # Short vowel followed by consonant cluster (2+ consonants) → Guru
    if re.search(r"[aiuṛḷ][kgcjtdpbmnśṣsrlvyhw]{2,}$", s):
        return "1"

    # Syllables like 'om' or ending with anusvara/visarga → Guru
    if re.search(r"[ṁḥ]$", s):
        return "1"

    # Otherwise → Laghu
    return "0"

# -------------------------------
# Convert shloka -> syllables
# -------------------------------
def shloka_to_syllables(text):
    if text in shloka_manual_splits:
        return shloka_manual_splits[text]

    # Clean text
    s = re.sub(r"[^a-zāīūṛḷeoaiuṁḥ\s]", "", text.lower())
    s = re.sub(r"\s+", " ", s).strip()

    consonants = "kgcjtdpbmnśṣsrlvyhw"
    vowels = "aiueoāīūṛḷ"
    pattern = f"[{consonants}]?[{vowels}]"
    
    syllables = re.findall(pattern, s)
    if not syllables:  # fallback if regex fails
        syllables = s.split()
    return syllables

# -------------------------------
# Convert shloka -> pattern
# -------------------------------
def shloka_to_pattern(text):
    syllables = shloka_to_syllables(text)
    pattern = "".join(classify_syllable(syl) for syl in syllables)
    return pattern, syllables

# -------------------------------
# Identify Chandas
# -------------------------------
def identify_chandas(pattern):
    # Exact match first
    for r in rules:
        if r["pattern"] == pattern:
            return r["name"]

    # Closest match by comparing bits
    best_match = "Unknown"
    max_score = 0
    for r in rules:
        # Compare only overlapping length
        min_len = min(len(pattern), len(r["pattern"]))
        score = sum(1 for i in range(min_len) if pattern[i] == r["pattern"][i])
        if score > max_score:
            max_score = score
            best_match = r["name"]
    return best_match


# -------------------------------
# Routes
# -------------------------------
@app.route("/")
def index():
    return render_template("index.html")  # optional HTML form

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

# -------------------------------
# Run server
# -------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
