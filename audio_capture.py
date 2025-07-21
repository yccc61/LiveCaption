import sounddevice as sd
import numpy as np
import threading
import queue
import time
from typing import Callable, Optional

class SystemAudioCapture:
    """
    Captures system audio with low latency for real-time processing
    """
    
    def __init__(self, 
                 sample_rate: int = 16000,
                 chunk_duration: float = 1.0,  # 1 second chunks for low latency
                 channels: int = 1):
        self.sample_rate = sample_rate
        self.chunk_duration = chunk_duration
        self.chunk_size = int(sample_rate * chunk_duration)
        self.channels = channels
        
        self.audio_queue = queue.Queue()
        self.is_recording = False
        self.recording_thread = None
        
        # Callback function for processing audio chunks
        self.audio_callback: Optional[Callable[[np.ndarray], None]] = None
        
    def set_audio_callback(self, callback: Callable[[np.ndarray], None]):
        """Set callback function to process audio chunks"""
        self.audio_callback = callback
    
    def _find_best_input_device(self):
        """Find the best audio input device (preferably loopback/monitor)"""
        devices = sd.query_devices()
        
        # Look for loopback or monitor devices first (system audio)
        for i, device in enumerate(devices):
            device_name = device['name'].lower()
            if any(keyword in device_name for keyword in ['loopback', 'monitor', 'what u hear', 'stereo mix']):
                if device['max_input_channels'] > 0:
                    print(f"Found system audio device: {device['name']}")
                    return i
        
        # Fallback to default input device
        default_device = sd.default.device[0]
        if default_device is not None:
            print(f"Using default input device: {devices[default_device]['name']}")
            return default_device
        
        # Last resort: first available input device
        for i, device in enumerate(devices):
            if device['max_input_channels'] > 0:
                print(f"Using first available input device: {device['name']}")
                return i
                
        raise RuntimeError("No suitable input device found")
    
    def _audio_callback_internal(self, indata, frames, time, status):
        """Internal callback for sounddevice"""
        if status:
            print(f"Audio callback status: {status}")
        
        # Convert to mono if stereo
        if indata.shape[1] > 1:
            audio_data = np.mean(indata, axis=1)
        else:
            audio_data = indata.flatten()
            
        # Put in queue for processing
        try:
            self.audio_queue.put_nowait(audio_data.copy())
        except queue.Full:
            # Drop oldest data if queue is full
            try:
                self.audio_queue.get_nowait()
                self.audio_queue.put_nowait(audio_data.copy())
            except queue.Empty:
                pass
    
    def _processing_thread(self):
        """Thread for processing audio chunks"""
        while self.is_recording:
            try:
                # Get audio chunk with timeout
                audio_chunk = self.audio_queue.get(timeout=0.1)
                
                # Call user callback if set
                if self.audio_callback:
                    self.audio_callback(audio_chunk)
                    
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error in audio processing: {e}")
    
    def start_capture(self):
        """Start capturing system audio"""
        if self.is_recording:
            return
            
        try:
            device_id = self._find_best_input_device()
            
            self.is_recording = True
            
            # Start audio stream
            self.stream = sd.InputStream(
                device=device_id,
                channels=self.channels,
                samplerate=self.sample_rate,
                blocksize=self.chunk_size,
                callback=self._audio_callback_internal,
                dtype=np.float32
            )
            
            # Start processing thread
            self.recording_thread = threading.Thread(target=self._processing_thread)
            self.recording_thread.start()
            
            self.stream.start()
            print(f"Started audio capture at {self.sample_rate}Hz")
            
        except Exception as e:
            print(f"Error starting audio capture: {e}")
            self.is_recording = False
            raise
    
    def stop_capture(self):
        """Stop capturing audio"""
        if not self.is_recording:
            return
            
        self.is_recording = False
        
        if hasattr(self, 'stream'):
            self.stream.stop()
            self.stream.close()
        
        if self.recording_thread:
            self.recording_thread.join(timeout=2.0)
        
        print("Stopped audio capture")
    
    def list_audio_devices(self):
        """List all available audio devices"""
        print("Available audio devices:")
        devices = sd.query_devices()
        for i, device in enumerate(devices):
            print(f"{i}: {device['name']} - In: {device['max_input_channels']}, Out: {device['max_output_channels']}")

# Test function
if __name__ == "__main__":
    def test_callback(audio_data):
        # Simple volume level indicator
        volume = np.sqrt(np.mean(audio_data**2))
        print(f"Audio level: {'█' * int(volume * 50)}")
    
    capture = SystemAudioCapture()
    capture.list_audio_devices()
    capture.set_audio_callback(test_callback)
    
    try:
        capture.start_capture()
        print("Recording... Press Ctrl+C to stop")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        capture.stop_capture()
        print("Stopped")
