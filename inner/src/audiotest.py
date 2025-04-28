import numpy as np
import simpleaudio as sa

def playNotes(frequencies, duration=2, volume=0.5, sample_rate=44100):
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    
    wave = np.zeros_like(t)
    for freq in frequencies:
        wave += np.sign(np.sin(2 * np.pi * freq * t))
    
    wave = wave / np.max(np.abs(wave))
    wave *= volume
    audio = (wave * 32767).astype(np.int16)
    
    play_obj = sa.play_buffer(audio, 1, 2, sample_rate)
    play_obj.wait_done()

def playNoise(duration=0.08, volume=0.5, sample_rate=44100):
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    
    wave = np.zeros_like(t)
    wave += np.random.random(t.shape) * 2 - 1
    
    wave = wave / np.max(np.abs(wave))
    wave *= volume
    audio = (wave * 32767).astype(np.int16)
    
    play_obj = sa.play_buffer(audio, 1, 2, sample_rate)
    play_obj.wait_done()

playNoise()
#playNotes([440, 550, 660])
playNotes([100, 150, 200, 300, 400, 500, 600, 800, 1000, 1200, 1400, 1600, 2000, 2400, 3000, 3600])
