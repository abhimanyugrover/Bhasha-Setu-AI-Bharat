import boto3
import re

TECH_KEYWORDS = [
    "variable","loop","function","array","string","integer","float","boolean",
    "class","object","method","algorithm","database","server","client","API",
]

def protect(text):
    kmap = {}
    for i, kw in enumerate(TECH_KEYWORDS):
        marker = f"BSTK{i}END"
        pat = re.compile(r'(?<!\w)' + re.escape(kw) + r'(?!\w)', re.IGNORECASE)
        if pat.search(text):
            text = pat.sub(marker, text)
            kmap[marker] = kw
    return text, kmap

def restore(text, kmap):
    for marker, kw in kmap.items():
        text = text.replace(marker, kw)
    return text

# Load cached transcript
import os, json, hashlib

cache_dir = r'C:\bhasha-setu\cache'
files = os.listdir(cache_dir)
print(f"Cache files: {files}")

if files:
    with open(os.path.join(cache_dir, files[0]), 'r', encoding='utf-8') as f:
        data = json.load(f)
    text = data['text']
    print(f"\nTranscript length: {len(text)} chars")
    print(f"Transcript preview: {text[:200]}")

    # Truncate
    text = text.encode('utf-8')[:9000].decode('utf-8', errors='ignore')

    # Translate to Tamil
    modified, kmap = protect(text)
    client = boto3.client('translate', region_name='ap-south-1')
    resp = client.translate_text(Text=modified, SourceLanguageCode='en', TargetLanguageCode='ta')
    translated = restore(resp['TranslatedText'], kmap)

    print(f"\nTranslated length: {len(translated)} chars")
    print(f"Translated preview: {translated[:300]}")

    # Now test Polly with first 500 chars
    polly = boto3.client('polly', region_name='ap-south-1')
    chunk = translated[:500]
    print(f"\nTesting Polly with chunk: {chunk[:100]}...")

    try:
        resp = polly.synthesize_speech(
            Text=chunk,
            OutputFormat='mp3',
            VoiceId='Kajal',
            Engine='neural',
            LanguageCode='ta-IN'
        )
        audio = resp['AudioStream'].read()
        print(f"✅ Polly returned: {len(audio)} bytes")
        with open(r'C:\bhasha-setu\output\test_chunk.mp3', 'wb') as f:
            f.write(audio)
    except Exception as e:
        print(f"❌ Polly failed: {e}")