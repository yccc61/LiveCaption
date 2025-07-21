#!/usr/bin/env python3
"""
Live Caption - Japanese to Chinese Real-time Translation
Captures system audio, transcribes Japanese speech, and displays natural Chinese translations
"""

import argparse
import signal
import sys
import threading
import time
from pathlib import Path

# Import our components
from audio_capture import SystemAudioCapture
from transcription import FastJapaneseTranscriber
from translation import NaturalJapaneseChinese
from caption_ui import FloatingCaptionUI

class LiveCaptionApp:
    """
    Main application that orchestrates all components
    """
    
    def __init__(self, 
                 whisper_model: str = "base",
                 chunk_duration: float = 1.0,
                 font_size: int = 14,
                 opacity: float = 0.8):
        
        self.whisper_model = whisper_model
        self.chunk_duration = chunk_duration
        self.font_size = font_size
        self.opacity = opacity
        
        # Components
        self.audio_capture = None
        self.transcriber = None
        self.translator = None
        self.caption_ui = None
        
        # Threading
        self.ui_thread = None
        self.is_running = False
        
        # Stats
        self.stats = {
            'audio_chunks': 0,
            'transcriptions': 0,
            'translations': 0,
            'start_time': None
        }
        
        print("Live Caption initialized")
    
    def _setup_components(self):
        """Initialize all components"""
        print("Setting up components...")
        
        try:
            # Initialize caption UI first (needs to be in main thread)
            print("Creating caption UI...")
            self.caption_ui = FloatingCaptionUI(
                font_size=self.font_size,
                opacity=self.opacity
            )
            
            # Initialize transcriber
            print("Loading transcription model...")
            self.transcriber = FastJapaneseTranscriber(model_size=self.whisper_model)
            self.transcriber.set_result_callback(self._on_transcription)
            
            # Initialize translator
            print("Loading translation model...")
            self.translator = NaturalJapaneseChinese()
            self.translator.set_result_callback(self._on_translation)
            
            # Initialize audio capture
            print("Setting up audio capture...")
            self.audio_capture = SystemAudioCapture(
                chunk_duration=self.chunk_duration
            )
            self.audio_capture.set_audio_callback(self._on_audio_chunk)
            
            print("All components initialized successfully")
            
        except Exception as e:
            print(f"Error setting up components: {e}")
            raise
    
    def _on_audio_chunk(self, audio_data):
        """Handle new audio chunk"""
        self.stats['audio_chunks'] += 1
        
        # Send to transcriber
        if self.transcriber:
            self.transcriber.add_audio_chunk(audio_data)
    
    def _on_transcription(self, japanese_text):
        """Handle transcription result"""
        self.stats['transcriptions'] += 1
        print(f"Transcribed: {japanese_text}")
        
        # Update UI with Japanese text immediately
        if self.caption_ui:
            self.caption_ui.update_caption(japanese=japanese_text)
        
        # Send to translator
        if self.translator:
            self.translator.translate(japanese_text)
    
    def _on_translation(self, japanese_text, chinese_text):
        """Handle translation result"""
        self.stats['translations'] += 1
        print(f"Translated: {japanese_text} -> {chinese_text}")
        
        # Update UI with both texts
        if self.caption_ui:
            self.caption_ui.update_caption(
                japanese=japanese_text,
                chinese=chinese_text
            )
    
    def _start_services(self):
        """Start all background services"""
        print("Starting services...")
        
        # Start transcription service
        self.transcriber.start()
        
        # Start translation service
        self.translator.start()
        
        # Start audio capture (this should be last)
        self.audio_capture.start_capture()
        
        print("All services started")
    
    def _stop_services(self):
        """Stop all background services"""
        print("Stopping services...")
        
        # Stop audio capture first
        if self.audio_capture:
            self.audio_capture.stop_capture()
        
        # Stop other services
        if self.transcriber:
            self.transcriber.stop()
        
        if self.translator:
            self.translator.stop()
        
        print("All services stopped")
    
    def _print_stats(self):
        """Print usage statistics"""
        if self.stats['start_time']:
            runtime = time.time() - self.stats['start_time']
            print(f"\n--- Live Caption Statistics ---")
            print(f"Runtime: {runtime:.1f} seconds")
            print(f"Audio chunks processed: {self.stats['audio_chunks']}")
            print(f"Transcriptions: {self.stats['transcriptions']}")
            print(f"Translations: {self.stats['translations']}")
            if runtime > 0:
                print(f"Transcription rate: {self.stats['transcriptions']/runtime:.2f}/sec")
                print(f"Translation rate: {self.stats['translations']/runtime:.2f}/sec")
    
    def _run_ui(self):
        """Run the UI in a separate thread"""
        try:
            self.caption_ui.run()
        except Exception as e:
            print(f"UI error: {e}")
        finally:
            self.is_running = False
    
    def start(self):
        """Start the live caption application"""
        try:
            print("Starting Live Caption...")
            self.stats['start_time'] = time.time()
            self.is_running = True
            
            # Setup all components
            self._setup_components()
            
            # Start UI in separate thread
            self.ui_thread = threading.Thread(target=self._run_ui)
            self.ui_thread.daemon = True
            self.ui_thread.start()
            
            # Give UI time to initialize
            time.sleep(1)
            
            # Start background services
            self._start_services()
            
            print("Live Caption is running!")
            print("- Audio will be captured from system output")
            print("- Japanese speech will be transcribed and translated to Chinese")
            print("- Captions will appear in floating window")
            print("- Right-click caption window for options")
            print("- Press Ctrl+C to stop")
            
            # Keep main thread alive
            try:
                while self.is_running:
                    time.sleep(0.1)
            except KeyboardInterrupt:
                print("\nShutdown requested...")
                
        except Exception as e:
            print(f"Error starting application: {e}")
            raise
        finally:
            self.stop()
    
    def stop(self):
        """Stop the live caption application"""
        print("Stopping Live Caption...")
        self.is_running = False
        
        # Stop services
        self._stop_services()
        
        # Stop UI
        if self.caption_ui:
            self.caption_ui.destroy()
        
        # Print final stats
        self._print_stats()
        
        print("Live Caption stopped")

def setup_signal_handlers(app):
    """Setup signal handlers for graceful shutdown"""
    def signal_handler(signum, frame):
        print(f"\nReceived signal {signum}")
        app.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Live Caption - Japanese to Chinese Real-time Translation"
    )
    
    parser.add_argument(
        "--model", 
        choices=["tiny", "base", "small", "medium"],
        default="base",
        help="Whisper model size (default: base)"
    )
    
    parser.add_argument(
        "--chunk-duration",
        type=float,
        default=1.0,
        help="Audio chunk duration in seconds (default: 1.0)"
    )
    
    parser.add_argument(
        "--font-size",
        type=int,
        default=14,
        help="Caption font size (default: 14)"
    )
    
    parser.add_argument(
        "--opacity",
        type=float,
        default=0.8,
        help="Caption window opacity 0.0-1.0 (default: 0.8)"
    )
    
    parser.add_argument(
        "--list-devices",
        action="store_true",
        help="List available audio devices and exit"
    )
    
    parser.add_argument(
        "--test-ui",
        action="store_true",
        help="Test caption UI with sample text"
    )
    
    args = parser.parse_args()
    
    # Handle special commands
    if args.list_devices:
        from audio_capture import SystemAudioCapture
        capture = SystemAudioCapture()
        capture.list_audio_devices()
        return
    
    if args.test_ui:
        from caption_ui import FloatingCaptionUI
        ui = FloatingCaptionUI(font_size=args.font_size, opacity=args.opacity)
        ui.update_caption("テストメッセージです", "这是测试消息")
        ui.run()
        return
    
    # Create and run the application
    app = LiveCaptionApp(
        whisper_model=args.model,
        chunk_duration=args.chunk_duration,
        font_size=args.font_size,
        opacity=args.opacity
    )
    
    # Setup signal handlers
    setup_signal_handlers(app)
    
    # Run the application
    try:
        app.start()
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
    except Exception as e:
        print(f"Application error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
