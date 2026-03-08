import boto3

print("Testing AWS connection...")

# Test Translate
translate = boto3.client('translate', region_name='ap-south-1')
result = translate.translate_text(
    Text="Hello, how are you?",
    SourceLanguageCode="en",
    TargetLanguageCode="hi"
)
print(f"✅ Translate working — 'Hello, how are you?' → '{result['TranslatedText']}'")

# Test Polly
polly = boto3.client('polly', region_name='ap-south-1')
response = polly.synthesize_speech(
    Text="नमस्ते, आप कैसे हैं?",
    OutputFormat="mp3",
    VoiceId="Aditi"
)
with open("C:\\bhasha-setu\\test_output.mp3", "wb") as f:
    f.write(response['AudioStream'].read())
print("✅ Polly working — saved test_output.mp3")

print("\n🎉 AWS is ready! Let's build Bhasha-Setu!")