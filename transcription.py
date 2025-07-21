import whisper
import numpy as np
import threading
import queue
import time
from typing import Callable, Optional
import torch

class FastJapaneseTranscriber:
    """
    Fast Japanese speech-to-text using lightweight Whisper model
    Optimized for low latency live transcription
    """
    
    def __init__(self, model_size: str = "base"):
        """
        Initialize with Whisper model
        Models by speed/accuracy tradeoff:
        - tiny: fastest, lowest accuracy
        - base: good balance for live transcription  
        - small: better accuracy, slower
        """
        self.model_size = model_size
        self.model = None
        self.transcription_queue = queue.Queue()
        self.result_callback: Optional[Callable[[str], None]] = None
        self.is_running = False
        self.transcription_thread = None
        
        # Audio preprocessing settings
        self.min_audio_length = 0.5  # seconds
        self.max_audio_length = 30   # seconds (Whisper limit)
        
        self._load_model()
    
    def _load_model(self):
        """Load Whisper model with optimizations"""
        print(f"Loading Whisper {self.model_size} model...")
        
        # Use GPU if available for faster inference
        device = "cuda" if torch.cuda.is_available() else "cpu"
        
        try:
            self.model = whisper.load_model(
                self.model_size, 
                device=device,
                # Use fp16 for faster inference on GPU
                in_memory=True
            )
            print(f"Whisper model loaded on {device}")
            
            # Warm up the model with dummy audio
            dummy_audio = np.zeros(16000, dtype=np.float32)  # 1 second of silence
            self._transcribe_audio(dummy_audio)
            print("Model warmed up")
            
        except Exception as e:
            print(f"Error loading Whisper model: {e}")
            raise
    
    def set_result_callback(self, callback: Callable[[str], None]):
        """Set callback function to receive transcription results"""
        self.result_callback = callback
    
    def _preprocess_audio(self, audio_data: np.ndarray) -> np.ndarray:
        """Preprocess audio for Whisper"""
        # Ensure audio is float32
        if audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32)
        
        # Normalize audio to [-1, 1] range
        if np.max(np.abs(audio_data)) > 0:
            audio_data = audio_data / np.max(np.abs(audio_data))
        
        # Pad or truncate to reasonable length
        target_length = int(16000 * min(self.max_audio_length, max(self.min_audio_length, len(audio_data) / 16000)))
        
        if len(audio_data) < target_length:
            # Pad with zeros if too short
            audio_data = np.pad(audio_data, (0, target_length - len(audio_data)))
        elif len(audio_data) > target_length:
            # Truncate if too long
            audio_data = audio_data[:target_length]
        
        return audio_data
    
    def _transcribe_audio(self, audio_data: np.ndarray) -> str:
        """Transcribe audio using Whisper"""
        try:
            # Fast transcription with Japanese language hint
            result = self.model.transcribe(
                audio_data,
                language="ja",  # Force Japanese language
                task="transcribe",
                # Fast settings for low latency
                beam_size=1,          # Greedy decoding (fastest)
                best_of=1,            # No multiple candidates
                temperature=0,        # Deterministic output
                no_speech_threshold=0.3,
                # Skip silence detection for faster processing
                condition_on_previous_text=False,
                verbose=False
            )
            
            text = result["text"].strip()
            
            # Filter out obvious transcription errors or noise
            if len(text) < 2 or text.count("ん") > len(text) * 0.8:
                return ""
            
            return text
            
        except Exception as e:
            print(f"Transcription error: {e}")
            return ""
    
    def _transcription_worker(self):
        """Worker thread for transcription processing"""
        while self.is_running:
            try:
                # Get audio chunk from queue
                audio_chunk = self.transcription_queue.get(timeout=0.1)
                
                # Skip if audio is too quiet (likely silence)
                volume = np.sqrt(np.mean(audio_chunk**2))
                if volume < 0.01:  # Adjust threshold as needed
                    continue
                
                # Preprocess audio
                processed_audio = self._preprocess_audio(audio_chunk)
                
                # Transcribe
                start_time = time.time()
                japanese_text = self._transcribe_audio(processed_audio)
                transcription_time = time.time() - start_time
                
                # Call result callback if text found
                if japanese_text and self.result_callback:
                    print(f"Transcription ({transcription_time:.2f}s): {japanese_text}")
                    self.result_callback(japanese_text)
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error in transcription worker: {e}")
    
    def add_audio_chunk(self, audio_data: np.ndarray):
        """Add audio chunk for transcription"""
        if not self.is_running:
            return
        
        try:
            # Non-blocking add to queue
            self.transcription_queue.put_nowait(audio_data)
        except queue.Full:
            # Drop oldest chunk if queue is full to maintain low latency
            try:
                self.transcription_queue.get_nowait()
                self.transcription_queue.put_nowait(audio_data)
            except queue.Empty:
                pass
    
    def start(self):
        """Start transcription service"""
        if self.is_running:
            return
        
        self.is_running = True
        self.transcription_thread = threading.Thread(target=self._transcription_worker)
        self.transcription_thread.start()
        print("Japanese transcription service started")
    
    def stop(self):
        """Stop transcription service"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        if self.transcription_thread:
            self.transcription_thread.join(timeout=3.0)
        
        print("Japanese transcription service stopped")

# Test function
if __name__ == "__main__":
    def test_transcription_callback(japanese_text):
        print(f"Transcribed: {japanese_text}")
    
    # Test with dummy audio (replace with actual audio for real testing)
    transcriber = FastJapaneseTranscriber(model_size="base")
    transcriber.set_result_callback(test_transcription_callback)
    
    try:
        transcriber.start()
        
        # Simulate audio chunks (replace with real audio capture)
        print("Transcriber ready. Add audio chunks to test...")
        time.sleep(5)
        
    except KeyboardInterrupt:
        transcriber.stop()
        print("Stopped transcription test")
