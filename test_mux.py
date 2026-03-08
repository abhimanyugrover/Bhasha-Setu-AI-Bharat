import subprocess
import os

# Test paths - update these to your actual files
video_path = r"C:\bhasha-setu\sample\test_video.mp4"
output_dir = r"C:\bhasha-setu\output"

# Find the most recent audio file
audio_files = [f for f in os.listdir(output_dir) if f.endswith('_audio.mp3')]
if not audio_files:
    print("❌ No audio files found in output dir!")
    exit()

mp3_path = os.path.join(output_dir, sorted(audio_files)[-1])
print(f"Testing with audio: {mp3_path}")
print(f"Testing with video: {video_path}")

# Step 1: Check files exist
print(f"\n--- File Check ---")
print(f"Video exists: {os.path.exists(video_path)} ({os.path.getsize(video_path)//1024}KB)")
print(f"Audio exists: {os.path.exists(mp3_path)} ({os.path.getsize(mp3_path)//1024}KB)")

# Step 2: Test MP3 info
print(f"\n--- MP3 Info ---")
r = subprocess.run(['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', mp3_path],
                   capture_output=True, text=True)
print(r.stdout[:500])
print("STDERR:", r.stderr[:300])

# Step 3: Convert MP3 to WAV
wav_path = mp3_path.replace('.mp3', '_test.wav')
print(f"\n--- MP3 → WAV ---")
r = subprocess.run(['ffmpeg', '-y', '-i', mp3_path, '-acodec', 'pcm_s16le', '-ar', '44100', '-ac', '1', wav_path],
                   capture_output=True, text=True)
print("Return code:", r.returncode)
print("STDERR:", r.stderr[-500:])
if os.path.exists(wav_path):
    print(f"WAV created: {os.path.getsize(wav_path)//1024}KB")
else:
    print("❌ WAV not created!")
    exit()

# Step 4: Get durations
def get_dur(p):
    r = subprocess.run(['ffprobe','-v','error','-show_entries','format=duration',
                        '-of','default=noprint_wrappers=1:nokey=1',p],
                       capture_output=True, text=True)
    return r.stdout.strip()

print(f"\n--- Durations ---")
print(f"Video: {get_dur(video_path)}s")
print(f"WAV:   {get_dur(wav_path)}s")

# Step 5: Apply volume boost (no speed change)
adj_wav = wav_path.replace('_test.wav', '_adj.wav')
print(f"\n--- Volume Boost ---")
r = subprocess.run(['ffmpeg', '-y', '-i', wav_path,
                    '-filter:a', 'volume=3.0,aresample=44100',
                    '-ar', '44100', '-ac', '1', adj_wav],
                   capture_output=True, text=True)
print("Return code:", r.returncode)
print("STDERR:", r.stderr[-300:])

# Step 6: Final merge
out_path = os.path.join(output_dir, "debug_output.mp4")
print(f"\n--- Final Merge ---")
r = subprocess.run([
    'ffmpeg', '-y',
    '-i', video_path,
    '-i', adj_wav,
    '-map', '0:v:0', '-map', '1:a:0',
    '-c:v', 'copy', '-c:a', 'aac',
    '-b:a', '192k', '-ar', '44100',
    '-shortest', '-movflags', '+faststart',
    out_path
], capture_output=True, text=True)
print("Return code:", r.returncode)
print("STDOUT:", r.stdout[-300:])
print("STDERR:", r.stderr[-500:])
if os.path.exists(out_path):
    print(f"\n✅ Output created: {os.path.getsize(out_path)//1024}KB")
else:
    print("\n❌ Output NOT created!")