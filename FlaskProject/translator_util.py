from googletrans import Translator

translator = Translator()

def translate_text(text, dest="en"):
    try:
        result = translator.translate(text, dest=dest)
        return result.text
    except Exception as e:
        print(f"Translation error: {e}")
        return text

def detect_language(text):
    try:
        result = translator.detect(text)
        return result.lang
    except Exception as e:
        print(f"Language detection error: {e}")
        return "en"