import torch
import numpy as np
import threading
import queue
import time
from typing import Callable, Optional
from transformers import WhisperProcessor, WhisperForConditionalGeneration
import librosa

class DirectJapaneseChinese:
    """
    Direct Japanese audio to Chinese text transcription using specialized Whisper model
    Uses Itbanque/whisper-ja-zh-base for high accuracy and low latency
    """
    
    def __init__(self, model_name: str = "Itbanque/whisper-ja-zh-base"):
        """
        Initialize with Japanese-to-Chinese Whisper model
        """
        self.model_name = model_name
        self.model = None
        self.processor = None
        self.transcription_queue = queue.Queue()
        self.result_callback: Optional[Callable[[str], None]] = None
        self.is_running = False
        self.transcription_thread = None
        
        # Audio preprocessing settings
        self.sample_rate = 16000  # Whisper standard
        self.min_audio_length = 0.5  # seconds
        self.max_audio_length = 30   # seconds (Whisper limit)
        
        # Performance settings
        self.chunk_overlap = 0.1  # 10% overlap for better continuity
        
        self._load_model()
    
    def _find_local_model(self) -> str:
        """Find local model directory"""
        from pathlib import Path
        
        # Check for local models in order of preference
        models_dir = Path(__file__).parent / "models"
        
        if self.model_name.startswith("Itbanque/"):
            model_name = self.model_name.split("/")[-1]  # Extract just the model name
        else:
            model_name = self.model_name
        
        local_model_paths = [
            models_dir / model_name,
            models_dir / "whisper-ja-zh-base",
            models_dir / "whisper-ja-zh-small", 
            models_dir / "whisper-ja-zh-large"
        ]
        
        for model_path in local_model_paths:
            if model_path.exists():
                # Check if required files exist
                required_files = ["config.json", "tokenizer_config.json"]
                model_files = ["pytorch_model.bin", "model.safetensors"]  # Either one is fine
                
                has_config = all((model_path / f).exists() for f in required_files)
                has_model = any((model_path / f).exists() for f in model_files)
                
                if has_config and has_model:
                    print(f"Found local model: {model_path}")
                    return str(model_path)
        
        return None
    
    def _auto_download_model(self) -> bool:
        """Automatically download model using China-friendly mirrors"""
        try:
            print("Attempting to download model automatically using China-friendly mirrors...")
            import subprocess
            import sys
            
            # Run the download script which prioritizes hf-mirror.com for China users
            result = subprocess.run([
                sys.executable, "download_models.py", "whisper-ja-zh-base"
            ], capture_output=True, text=True, timeout=600)  # 10 minute timeout
            
            if result.returncode == 0:
                print("Model downloaded successfully from mirror!")
                return True
            else:
                print(f"Download failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("Download timed out (>10 minutes) - network may be slow")
            return False
        except Exception as e:
            print(f"Auto-download error: {e}")
            return False
    
    def _load_model(self):
        """Load the Japanese-to-Chinese Whisper model"""
        print(f"Loading direct Japanese-Chinese model: {self.model_name}")
        
        try:
            # Use GPU if available for faster inference
            device = "cuda" if torch.cuda.is_available() else "cpu"
            
            # First try to load from local models directory
            local_model_path = self._find_local_model()
            
            if local_model_path:
                print(f"Using local model from: {local_model_path}")
                model_path = local_model_path
            else:
                print("Local model not found.")
                print("Attempting automatic download with mirror support...")
                
                # Try to download automatically using our download script
                if self._auto_download_model():
                    # Try to find local model again after download
                    local_model_path = self._find_local_model()
                    if local_model_path:
                        print(f"Using downloaded model from: {local_model_path}")
                        model_path = local_model_path
                    else:
                        raise Exception("Model download succeeded but model not found locally")
                else:
                    print("Automatic download failed.")
                    print("Trying direct download from Hugging Face...")
                    model_path = self.model_name
            
            # Load processor and model
            print("Loading model files...")
            self.processor = WhisperProcessor.from_pretrained(model_path)
            self.model = WhisperForConditionalGeneration.from_pretrained(model_path)
            
            if device == "cuda":
                self.model = self.model.to(device)
                # Use half precision for faster GPU inference
                self.model = self.model.half()
            
            self.device = device
            print(f"Direct model loaded successfully on {device}")
            
            # Warm up the model with dummy audio
            dummy_audio = np.zeros(self.sample_rate, dtype=np.float32)  # 1 second of silence
            self._transcribe_audio(dummy_audio)
            print("Direct model warmed up and ready!")
            
        except Exception as e:
            print(f"Error loading direct model: {e}")
            print("\n" + "="*50)
            print("MODEL LOADING FAILED - TROUBLESHOOTING GUIDE")
            print("="*50)
            print("For users in China or restricted regions:")
            print("1. Manual download: python download_models.py whisper-ja-zh-base")
            print("2. Use VPN if available")
            print("3. Download manually from alternative sources")
            print("4. Use legacy mode: python live_caption.py")
            print("="*50)
            raise Exception("Failed to load direct Japanese-Chinese model. See troubleshooting guide above.")
    
    def set_result_callback(self, callback: Callable[[str], None]):
        """Set callback function to receive transcription results (Chinese text)"""
        self.result_callback = callback
    
    def _preprocess_audio(self, audio_data: np.ndarray) -> np.ndarray:
        """Preprocess audio for Whisper"""
        # Ensure audio is float32
        if audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32)
        
        # Resample to 16kHz if needed (Whisper requirement)
        if len(audio_data) > 0:
            # Normalize audio to [-1, 1] range
            if np.max(np.abs(audio_data)) > 0:
                audio_data = audio_data / np.max(np.abs(audio_data))
        
        # Ensure minimum length
        min_samples = int(self.sample_rate * self.min_audio_length)
        if len(audio_data) < min_samples:
            # Pad with zeros if too short
            audio_data = np.pad(audio_data, (0, min_samples - len(audio_data)))
        
        # Truncate if too long
        max_samples = int(self.sample_rate * self.max_audio_length)
        if len(audio_data) > max_samples:
            audio_data = audio_data[:max_samples]
        
        return audio_data
    
    def _transcribe_audio(self, audio_data: np.ndarray) -> str:
        """Directly transcribe Japanese audio to Chinese text"""
        try:
            # Preprocess audio
            processed_audio = self._preprocess_audio(audio_data)
            
            # Process with Whisper processor
            inputs = self.processor(
                processed_audio,
                sampling_rate=self.sample_rate,
                return_tensors="pt"
            )
            
            # Move to same device as model
            if self.device == "cuda":
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Generate Chinese text directly from Japanese audio
            with torch.no_grad():
                # Force the model to generate Chinese text
                generated_ids = self.model.generate(
                    inputs["input_features"],
                    # Generation parameters for better quality and speed
                    max_length=448,  # Reasonable length for captions
                    num_beams=1,     # Greedy decoding for speed
                    do_sample=False, # Deterministic output
                    temperature=1.0,
                    # Language tokens - force Chinese output
                    forced_decoder_ids=self.processor.get_decoder_prompt_ids(
                        language="zh", task="transcribe"
                    )
                )
            
            # Decode the generated text
            chinese_text = self.processor.batch_decode(
                generated_ids, 
                skip_special_tokens=True
            )[0].strip()
            
            # Post-process the text
            chinese_text = self._post_process_chinese(chinese_text)
            
            return chinese_text
            
        except Exception as e:
            print(f"Direct transcription error: {e}")
            return ""
    
    def _post_process_chinese(self, text: str) -> str:
        """Post-process Chinese text for better readability"""
        if not text:
            return ""
        
        # Remove common transcription artifacts
        text = text.strip()
        
        # Remove timestamps and other metadata if present
        import re
        text = re.sub(r'\[\d+:?\d*\]', '', text)  # Remove timestamps like [00:01]
        text = re.sub(r'<[^>]*>', '', text)       # Remove XML-like tags
        text = re.sub(r'\s+', ' ', text)          # Normalize whitespace
        
        # Filter out very short or nonsensical results
        if len(text) < 2:
            return ""
        
        # Filter out repetitive noise (like repeated characters)
        if len(set(text)) < len(text) * 0.3 and len(text) > 5:
            return ""
        
        return text.strip()
    
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
                
                # Direct transcription from Japanese audio to Chinese text
                start_time = time.time()
                chinese_text = self._transcribe_audio(audio_chunk)
                transcription_time = time.time() - start_time
                
                # Call result callback if text found
                if chinese_text and self.result_callback:
                    print(f"Direct transcription ({transcription_time:.2f}s): Japanese audio -> {chinese_text}")
                    self.result_callback(chinese_text)
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error in direct transcription worker: {e}")
    
    def add_audio_chunk(self, audio_data: np.ndarray):
        """Add audio chunk for direct transcription"""
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
        """Start direct transcription service"""
        if self.is_running:
            return
        
        self.is_running = True
        self.transcription_thread = threading.Thread(target=self._transcription_worker)
        self.transcription_thread.start()
        print("Direct Japanese-Chinese transcription service started")
    
    def stop(self):
        """Stop direct transcription service"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        if self.transcription_thread:
            self.transcription_thread.join(timeout=3.0)
        
        print("Direct Japanese-Chinese transcription service stopped")

# Test function
if __name__ == "__main__":
    def test_transcription_callback(chinese_text):
        print(f"Chinese result: {chinese_text}")
    
    # Test with dummy audio (replace with actual audio for real testing)
    try:
        transcriber = DirectJapaneseChinese()
        transcriber.set_result_callback(test_transcription_callback)
        
        transcriber.start()
        
        # Simulate audio chunks (replace with real audio capture)
        print("Direct transcriber ready. Add audio chunks to test...")
        time.sleep(5)
        
    except Exception as e:
        print(f"Test failed: {e}")
    finally:
        if 'transcriber' in locals():
            transcriber.stop()
        print("Stopped direct transcription test")
