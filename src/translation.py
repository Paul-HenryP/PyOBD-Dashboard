import polib

def get_available_languages():
    import os
    langs = []
    for fname in os.listdir("src/locale"):
        if fname.endswith(".po"):
            lang_code = fname[:-3]
            langs.append(lang_code)
    return langs

def set_language(lang_code):
    global translations
    try:
        po = polib.pofile(f"src/locale/{lang_code}.po")
        translations = {e.msgid: e.msgstr for e in po}
    except Exception as e:
        print(f"Error loading language '{lang_code}': {e}, defaulting to English.")
        po = polib.pofile(f"src/locale/en.po")
        translations = {e.msgid: e.msgstr for e in po}

def translate(s):
    return translations.get(s, s)