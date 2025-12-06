# audio_engine.py
# Audio synthesis with harmonics for theremin sound generation

import numpy as np
import sounddevice as sd
import threading
import queue

# ===== CONFIG =====
SAMPLE_RATE = 44100  # Hz
CHUNK_DURATION = 0.05  # seconds
CHUNK_SIZE = int(SAMPLE_RATE * CHUNK_DURATION)

# Harmonic ratios for instrument-like timbre
HARMONIC_RATIOS = [
    (1.0, 1.00),   # fundamental
    (2.0, 0.80),   # 2nd harmonic
    (3.0, 1.75),   # 3rd harmonic
    (4.0, 0.25),   # 4th harmonic
    (5.0, 0.18),   # 5th harmonic
]

# ===== GLOBAL STATE =====
current_frequency = 440.0
current_volume = 0.5
is_playing = False

# Audio stream
audio_stream = None
audio_queue = queue.Queue(maxsize=10)

# ===== AUDIO GENERATION =====
def generate_tone(frequency, volume, duration):
    """Generate audio chunk with harmonics"""
    # time array
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    
    # start with silence
    waveform = np.zeros_like(t)
    
    # add each harmonic
    for harmonic_mult, amplitude_mult in HARMONIC_RATIOS:
        harmonic_freq = frequency * harmonic_mult
        harmonic_wave = amplitude_mult * np.sin(2 * np.pi * harmonic_freq * t)
        waveform += harmonic_wave
    
    # normalize to prevent clipping
    max_amplitude = sum([amp for _, amp in HARMONIC_RATIOS])
    waveform = waveform / max_amplitude
    
    # apply volume
    waveform = waveform * volume
    
    return waveform.astype(np.float32)

def generate_silence(duration):
    """Generate silence chunk"""
    num_samples = int(SAMPLE_RATE * duration)
    return np.zeros(num_samples, dtype=np.float32)

def audio_callback(outdata, frames, time_info, status):
    """Called by sounddevice to get next audio chunk"""
    global current_frequency, current_volume, is_playing
    
    if status:
        print(f"Audio callback status: {status}")
    
    try:
        # check if sound should play
        if is_playing and current_frequency > 0:
            # generate tone
            chunk = generate_tone(current_frequency, current_volume, CHUNK_DURATION)
        else:
            # generate silence
            chunk = generate_silence(CHUNK_DURATION)
        
        # copy to output buffer
        outdata[:] = chunk.reshape(-1, 1)
        
    except Exception as e:
        print(f"Error in audio callback: {e}")
        outdata[:] = np.zeros((frames, 1), dtype=np.float32)

def start_audio_stream():
    """Initialize and start audio output stream"""
    global audio_stream
    
    try:
        # create output stream
        audio_stream = sd.OutputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            blocksize=CHUNK_SIZE,
            callback=audio_callback,
            dtype=np.float32,
            device=4
        )
        
        # start stream
        audio_stream.start()
        print("Audio stream started")
        
    except Exception as e:
        print(f"Failed to start audio stream: {e}")

def stop_audio_stream():
    """Stop audio output stream"""
    global audio_stream
    
    if audio_stream is not None:
        audio_stream.stop()
        audio_stream.close()
        print("Audio stream stopped")

def update_audio_params(frequency, volume, playing):
    """Update audio parameters from sensor data"""
    global current_frequency, current_volume, is_playing
    
    current_frequency = frequency
    current_volume = volume
    is_playing = playing

def get_current_waveform():
    """Get current waveform for visualization"""
    global current_frequency, current_volume, is_playing
    
    if is_playing and current_frequency > 0:
        # generate short sample for viz
        sample_duration = 0.02  # 20ms
        waveform = generate_tone(current_frequency, current_volume, sample_duration)
        # downsample for frontend (send every Nth sample)
        downsampled = waveform[::20]  # ~1000 points
        return downsampled.tolist()
    else:
        # return silence
        return [0.0] * 50

# ===== INIT =====
def init_audio():
    """Initialize audio system"""
    print("Initializing audio engine...")
    start_audio_stream()

def cleanup_audio():
    """Cleanup audio system"""
    print("Cleaning up audio engine...")
    stop_audio_stream()