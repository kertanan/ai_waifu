from click import option
from transformers.models import whisper
import whisper

#load audio pad/trim it for 30 second
model = whisper.load_model("turbo")
result = model.transcribe("audio.mp3", fp16=False)
audio = whisper.load_audio("audio.mp3")
audio = whisper.pad_or_trim(audio)
#make log-mel
mel = whisper.log_mel_spectrogram(audio, n_mels=model.dims.n_mels).to(model.device)

#detect spoken leagugae 
probs = model.detect_language(mel)
print(f"Detected language: {max(probs, key=probs.get)}")

#decode the audio
option = whisper.DecodingOptions()
result = whisper.decode(model,mel, option)

print (result.text)
#Transcribe