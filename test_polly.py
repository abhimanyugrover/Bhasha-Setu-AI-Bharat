import boto3
import os

polly = boto3.client('polly', region_name='ap-south-1')

# Test with a simple Tamil sentence
test_text = "வணக்கம். இன்று நாம் Python பற்றி கற்கப் போகிறோம். Variable என்பது ஒரு container ஆகும்."

print(f"Text length: {len(test_text)} chars")
print(f"Text: {test_text[:100]}")

# Try Tamil neural voice
try:
    resp = polly.synthesize_speech(
        Text=test_text,
        OutputFormat='mp3',
        VoiceId='Kajal',
        Engine='neural',
        LanguageCode='ta-IN'
    )
    audio = resp['AudioStream'].read()
    print(f"\n✅ Tamil neural: {len(audio)} bytes")
    with open(r'C:\bhasha-setu\output\test_tamil.mp3', 'wb') as f:
        f.write(audio)
    print("Saved: test_tamil.mp3")
except Exception as e:
    print(f"\n❌ Tamil neural failed: {e}")

# Also check what was in the last translated text
output_dir = r'C:\bhasha-setu\output'
mp3_files = sorted([f for f in os.listdir(output_dir) if f.endswith('_audio.mp3')])
if mp3_files:
    latest = os.path.join(output_dir, mp3_files[-1])
    size = os.path.getsize(latest)
    print(f"\nLatest audio file: {mp3_files[-1]}")
    print(f"Size: {size} bytes ({size//1024}KB)")
    if size < 1000:
        print("⚠️ This is suspiciously small — synthesis likely failed silently")