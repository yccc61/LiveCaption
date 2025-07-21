# LiveCaption - Japanese to Chinese Real-time Translation

A low-latency live caption system that captures system audio, transcribes Japanese speech using Whisper, and displays natural Chinese translations in a transparent floating window.

## Features

- **System Audio Capture**: Captures audio from any application (videos, games, streams, etc.)
- **Fast Japanese Transcription**: Uses optimized Whisper models for low-latency speech-to-text
- **Natural Translation**: Japanese to Chinese translation with casual/NSFW content support
- **Floating Caption UI**: Transparent, draggable window with Japanese and Chinese text
- **Low Latency**: Optimized for real-time performance (1-2 second delay typical)

## Quick Start

1. **Setup**:
   ```bash
   cd LiveCaption
   python setup.py
   ```

2. **Run**:
   ```bash
   python live_caption.py
   ```

3. **Test UI**:
   ```bash
   python live_caption.py --test-ui
   ```

## Requirements

- Python 3.8+
- System with audio capabilities
- ~4GB RAM for base Whisper model
- Optional: NVIDIA GPU for faster inference

## Usage

### Basic Usage
```bash
# Run with default settings
python live_caption.py

# Use faster but less accurate model
python live_caption.py --model tiny

# Use more accurate but slower model  
python live_caption.py --model small

# Adjust UI settings
python live_caption.py --font-size 16 --opacity 0.9
```

### Command Line Options
```
--model {tiny,base,small,medium}    Whisper model size (default: base)
--chunk-duration FLOAT             Audio chunk duration in seconds (default: 1.0)
--font-size INT                     Caption font size (default: 14)
--opacity FLOAT                     Window opacity 0.0-1.0 (default: 0.8)
--list-devices                      List available audio devices
--test-ui                          Test caption UI with sample text
```

### Model Performance Comparison

| Model  | Speed | Accuracy | Memory | Best For |
|--------|-------|----------|--------|----------|
| tiny   | Fast  | Low      | ~1GB   | Real-time, basic |
| base   | Good  | Good     | ~1GB   | **Recommended** |
| small  | Slow  | High     | ~2GB   | Accuracy priority |
| medium | Very Slow | Very High | ~5GB | Offline processing |

## System Audio Setup

### Windows
- Enable "Stereo Mix" or "What U Hear" in recording devices
- Or use software like VB-Cable for audio routing

### Linux
- Use PulseAudio monitor devices (automatically detected)
- May need to enable loopback: `pactl load-module module-loopback`

### macOS  
- Use software like BlackHole or Soundflower for audio routing
- Built-in system audio capture may have limitations

## UI Controls

### Caption Window
- **Drag**: Click and drag to move window
- **Right-click**: Context menu with options
  - Hide/Show window
  - Adjust font size
  - Change transparency
  - Quit application

### Auto-hide
- Window automatically hides after 5 seconds of no new captions
- Appears when new speech is detected

## Translation Features

### Natural Language Processing
- Casual Japanese expressions → Natural Chinese equivalents
- NSFW content → Appropriate Chinese translations
- Context-aware translation patterns

### Translation Examples
| Japanese | Chinese | Note |
|----------|---------|------|
| やばい | 糟糕 | Casual expression |
| かわいい | 可爱 | Natural, not formal |
| 愛してる | 爱你 | Intimate expression |
| そうだね | 是啊 | Conversational tone |

## Performance Optimization

### For Low Latency
```bash
# Use tiny model with short chunks
python live_caption.py --model tiny --chunk-duration 0.5
```

### For Better Accuracy
```bash
# Use small model with longer chunks  
python live_caption.py --model small --chunk-duration 1.5
```

### GPU Acceleration
- Automatically uses NVIDIA GPU if available
- Install CUDA-enabled PyTorch for best performance
- Reduces transcription time by 3-5x

## Troubleshooting

### No Audio Captured
1. Check available devices: `python live_caption.py --list-devices`
2. Ensure system audio/loopback device is available
3. On Windows: Enable Stereo Mix in Sound settings
4. On Linux: Check PulseAudio configuration

### Poor Transcription Quality
1. Increase model size: `--model small`
2. Adjust chunk duration: `--chunk-duration 1.5`
3. Ensure good audio quality (clear speech, low background noise)

### High CPU Usage
1. Use smaller model: `--model tiny`
2. Increase chunk duration: `--chunk-duration 2.0`
3. Close other applications

### Translation Issues
1. Check console output for translation errors
2. Internet connection required for some translation models
3. Japanese text must be accurately transcribed first

## Technical Details

### Architecture
```
Audio Capture → Whisper Transcription → Translation → UI Display
     ↓                ↓                    ↓           ↓
System Audio    Japanese Text      Chinese Text   Floating Window
```

### Components
- **audio_capture.py**: System audio capture with sounddevice
- **transcription.py**: Whisper-based Japanese speech-to-text
- **translation.py**: Natural Japanese-Chinese translation
- **caption_ui.py**: Transparent floating window UI
- **live_caption.py**: Main application orchestrator

### Threading Model
- Main thread: UI event loop
- Audio thread: Continuous audio capture
- Transcription thread: Whisper inference
- Translation thread: Text translation
- UI update thread: Caption display

## Advanced Configuration

### Custom Translation Patterns
Edit `translation.py` to add custom Japanese→Chinese patterns:
```python
# In _load_casual_patterns()
r"your_japanese_pattern": "your_chinese_translation"
```

### Audio Settings
Modify audio capture parameters in `audio_capture.py`:
```python
# Adjust sample rate, chunk size, etc.
sample_rate = 16000  # Whisper optimal rate
chunk_duration = 1.0  # Balance latency vs accuracy
```

### UI Customization
Modify `caption_ui.py` for different UI appearance:
```python
# Colors, fonts, positioning, etc.
fg='white'           # Japanese text color
fg='#00ff00'         # Chinese text color (green)
```

## Performance Statistics

The application displays real-time statistics:
- Audio chunks processed per second
- Transcription rate
- Translation rate
- Total runtime

## License

Open source - feel free to modify and distribute.

## Contributing

1. Fork the repository
2. Create feature branch
3. Test with various Japanese audio sources
4. Submit pull request

## Known Limitations

- Requires good quality audio input
- Performance depends on system specs
- Translation quality varies with context
- Some dialects may not transcribe well
- NSFW translation patterns are basic

## Future Improvements

- Support for other language pairs
- Better NSFW translation handling
- Real-time audio filtering/enhancement
- Multiple caption window support  
- Custom translation model training
- Voice activity detection optimization
