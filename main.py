import os
import json
import random
import logging
from flask import Flask, request, jsonify, render_template, Response
from openai import OpenAI
import webbrowser
from threading import Timer

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

api_key = os.environ.get("OPENAI_API_KEY", "YOUR_API_KEY_HERE")
client = OpenAI(api_key=api_key)

# Liste verfügbarer Sprachen: engl. Bezeichner und deutsches Label inkl. Flagge
LANGUAGES = [
    {"en": "German",     "de": "Deutsch 🇩🇪"},
    {"en": "English",    "de": "Englisch 🇬🇧"},
    {"en": "French",     "de": "Französisch 🇫🇷"},
    {"en": "Spanish",    "de": "Spanisch 🇪🇸"},
    {"en": "Italian",    "de": "Italienisch 🇮🇹"},
    {"en": "Portuguese", "de": "Portugiesisch 🇵🇹"},
    {"en": "Dutch",      "de": "Niederländisch 🇳🇱"},
    {"en": "Russian",    "de": "Russisch 🇷🇺"},
    {"en": "Polish",     "de": "Polnisch 🇵🇱"},
    {"en": "Turkish",    "de": "Türkisch 🇹🇷"},
    {"en": "Arabic",     "de": "Arabisch 🇸🇦"},
    {"en": "Hebrew",     "de": "Hebräisch 🇮🇱"},
    {"en": "Chinese",    "de": "Chinesisch 🇨🇳"},
    {"en": "Japanese",   "de": "Japanisch 🇯🇵"},
    {"en": "Korean",     "de": "Koreanisch 🇰🇷"},
    {"en": "Hindi",      "de": "Hindi 🇮🇳"},
    {"en": "Vietnamese", "de": "Vietnamesisch 🇻🇳"},
    {"en": "Thai",       "de": "Thailändisch 🇹🇭"},
    {"en": "Indonesian", "de": "Indonesisch 🇮🇩"},
    {"en": "Swedish",    "de": "Schwedisch 🇸🇪"},
    {"en": "Norwegian",  "de": "Norwegisch 🇳🇴"},
    {"en": "Danish",     "de": "Dänisch 🇩🇰"},
    {"en": "Finnish",    "de": "Finnisch 🇫🇮"},
    {"en": "Czech",      "de": "Tschechisch 🇨🇿"},
    {"en": "Hungarian",  "de": "Ungarisch 🇭🇺"},
    {"en": "Romanian",   "de": "Rumänisch 🇷🇴"},
    {"en": "Greek",      "de": "Griechisch 🇬🇷"},
    {"en": "Ukrainian",  "de": "Ukrainisch 🇺🇦"},
    {"en": "Bulgarian",  "de": "Bulgarisch 🇧🇬"},
    {"en": "Malay",      "de": "Malaiisch 🇲🇾"}
]

TONES = ["positive", "neutral", "negative"]
REGISTERS = ["simple", "normal", "formal"]

def get_random_choice(options):
    return random.choice(options)

def build_prompt(text, language, tone, register, length="equal"):
    if length == "shorter":
        length_instruction = " The translation should be noticeably shorter than the original."
    elif length == "longer":
        length_instruction = " The translation should be noticeably longer than the original."
    else:
        length_instruction = " The translation should be of approximately equal length to the original."
    return (
        f"Translate the following text into {language}.\n"
        f"Adapt the tone to be {tone}, and the language register to be {register}.{length_instruction}\n"
        f"Respond with a JSON object in the form: {{\"text\": \"...\"}} only.\n\n"
        f"Text: {text}"
    )

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/languages', methods=['GET'])
def get_languages():
    return jsonify(LANGUAGES)

@app.route('/api/translate', methods=['POST'])
def translate():
    data = request.get_json()
    if not data or "text" not in data:
        return jsonify({"error": "No text provided"}), 400

    text = data.get("text", "")
    language = data.get("target_language", "random")
    tone = data.get("tone", "random")
    register = data.get("register", "random")
    length = data.get("length", "equal")

    if language == "random":
        language = get_random_choice(LANGUAGES)["en"]
    if tone == "random":
        tone = get_random_choice(TONES)
    if register == "random":
        register = get_random_choice(REGISTERS)

    prompt = build_prompt(text, language, tone, register, length)
    logging.debug(f"Prompt:\n{prompt}")

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a professional translator who adjusts tone, register and length as requested."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.6,
            max_tokens=1000
        )
        gpt_output = response.choices[0].message.content
        json_data = json.loads(gpt_output)
        return jsonify(json_data)
    except Exception as e:
        logging.error("OpenAI API error", exc_info=True)
        return jsonify({"error": "API error", "details": str(e)}), 500

@app.route('/api/randomtext', methods=['GET'])
def get_random_text():
    try:
        year = random.randint(-2000, 2025)
        era = "v. Chr." if year < 0 else "n. Chr."
        year_str = f"{abs(year)} {era}"

        prompt = (
            f"Think of a well-known story, scene or event that could plausibly take place around the year {year_str}. "
            f"It can come from literature, mythology, religion, film or history. "
            "Summarize that scene in exactly three simple, connected sentences in **German**. "
            "Avoid modern language or references that do not fit the time period. Use clear and understandable phrasing."
        )

        system = (
            "You are a helpful assistant that summarizes culturally or historically relevant stories "
            "in simple German. The summaries should be three connected sentences. Avoid dialogue or poetry."
        )

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt}
            ],
            temperature=1,
            max_tokens=200
        )

        raw_text = response.choices[0].message.content.strip()
        return jsonify({"text": raw_text, "year": year_str})
    except Exception as e:
        logging.error("Fehler beim Generieren eines zufälligen historischen Texts", exc_info=True)
        return jsonify({"error": "Fehler bei der Texterstellung", "details": str(e)}), 500

@app.route('/api/translate10x', methods=['POST'])
def translate_multiple():
    # Hole die Request-Daten einmal vor dem Generator
    data = request.get_json()
    def generate(data):
        if not data or "text" not in data:
            yield json.dumps({"error": "Kein Text übergeben"}) + "\n"
            return

        current_text = data["text"]
        try:
            count = int(data.get("count", 10))
        except ValueError:
            count = 10

        # Hole auch Tone, Register und Length Auswahl
        tone_sel = data.get("tone", "random")
        register_sel = data.get("register", "random")
        length_sel = data.get("length", "equal")

        yield json.dumps({"progress": 0}) + "\n"

        for i in range(count - 1):
            lang_obj = get_random_choice(LANGUAGES)
            language = lang_obj["en"]
            tone = tone_sel if tone_sel != "random" else get_random_choice(TONES)
            register = register_sel if register_sel != "random" else get_random_choice(REGISTERS)
            prompt = build_prompt(current_text, language, tone, register, length_sel)
            logging.debug(f"[{i+1}/{count}] -> {language} / {tone} / {register}\nPrompt:\n{prompt}")
            try:
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a professional translator who adapts tone, register and length as requested."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.4,
                    max_tokens=1000
                )
                gpt_output = response.choices[0].message.content.strip()
                try:
                    current_text = json.loads(gpt_output).get("text", gpt_output)
                except Exception:
                    current_text = gpt_output
                # Sende Fortschritt, aktuell verwendete Sprache (deutsches Label) und aktuellen Text
                yield json.dumps({"progress": i + 1, "language": lang_obj["de"], "current_text": current_text}) + "\n"
            except Exception as e:
                yield json.dumps({"error": f"Fehler bei Schritt {i+1}", "details": str(e)}) + "\n"
                return

        final_prompt = build_prompt(current_text, "German", "neutral", "normal", length_sel)
        logging.debug(f"[{count}/{count}] Rückübersetzung nach German\nPrompt:\n{final_prompt}")
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a professional translator who adapts tone, register and length as requested."},
                    {"role": "user", "content": final_prompt}
                ],
                temperature=0.4,
                max_tokens=1000
            )
            gpt_output = response.choices[0].message.content.strip()
            try:
                final_text = json.loads(gpt_output).get("text", gpt_output)
            except Exception:
                final_text = gpt_output
            yield json.dumps({"progress": count, "final_text": final_text, "current_text": final_text}) + "\n"
        except Exception as e:
            yield json.dumps({"error": "Fehler bei der Rückübersetzung", "details": str(e)}) + "\n"

    return Response(generate(data), mimetype="text/plain")

if __name__ == '__main__':
    app.run(debug=True)
