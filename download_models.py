#!/usr/bin/env python3
"""
Model Download Script for LiveCaption
Downloads and stores models locally to avoid runtime downloads
"""

import os
import sys
import requests
from pathlib import Path
from typing import List, Dict
import json
import time

class ModelDownloader:
    """
    Downloads and manages local model storage for LiveCaption
    """
    
    def __init__(self):
        self.models_dir = Path(__file__).parent / "models"
        self.models_dir.mkdir(exist_ok=True)
        
        # Model configurations
        self.models = {
            "whisper-ja-zh-base": {
                "hf_repo": "Itbanque/whisper-ja-zh-base",
                "files": [
                    "config.json",
                    "preprocessor_config.json",
                    "tokenizer.json", 
                    "tokenizer_config.json",
                    "vocab.json",
                    "merges.txt",
                    "pytorch_model.bin",
                    "generation_config.json"
                ],
                "size_mb": 500,
                "description": "Direct Japanese-Chinese Whisper model (Recommended)"
            }
        }
        
        # Mirror sites for users in restricted regions (China-optimized order)
        self.mirrors = [
            "https://hf-mirror.com",      # Best for China users
            "https://huggingface.co",     # Original site
        ]
    
    def download_file(self, url: str, local_path: Path, description: str = "") -> bool:
        """Download a file with progress indicator"""
        try:
            print(f"Downloading {description}...")
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            local_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(local_path, 'wb') as file:
                downloaded = 0
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        file.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            print(f"\r  Progress: {percent:.1f}% ({downloaded // 1024 // 1024}MB)", end="")
                        
            print(f"\n  ✓ Downloaded {local_path.name}")
            return True
            
        except Exception as e:
            print(f"\n  ✗ Failed to download {local_path.name}: {e}")
            return False
    
    def download_from_huggingface(self, model_name: str, mirror_url: str = None) -> bool:
        """Download model from Hugging Face or mirror"""
        if model_name not in self.models:
            print(f"Unknown model: {model_name}")
            return False
        
        model_info = self.models[model_name]
        repo = model_info["hf_repo"]
        base_url = mirror_url or "https://huggingface.co"
        
        model_dir = self.models_dir / model_name
        model_dir.mkdir(exist_ok=True)
        
        print(f"\nDownloading {model_info['description']}")
        print(f"Repository: {repo}")
        print(f"Mirror: {base_url}")
        print(f"Size: ~{model_info['size_mb']}MB")
        print("-" * 50)
        
        success_count = 0
        total_files = len(model_info["files"])
        
        for filename in model_info["files"]:
            file_url = f"{base_url}/{repo}/resolve/main/{filename}"
            local_path = model_dir / filename
            
            # Skip if file already exists and is not empty
            if local_path.exists() and local_path.stat().st_size > 0:
                print(f"  ✓ {filename} (already exists)")
                success_count += 1
                continue
            
            if self.download_file(file_url, local_path, filename):
                success_count += 1
            else:
                # Try alternative filename for pytorch_model.bin
                if filename == "pytorch_model.bin":
                    alt_url = f"{base_url}/{repo}/resolve/main/model.safetensors"
                    alt_path = model_dir / "model.safetensors"
                    if self.download_file(alt_url, alt_path, "model.safetensors (alternative)"):
                        success_count += 1
        
        success_rate = success_count / total_files
        if success_rate >= 0.8:  # At least 80% of files downloaded
            print(f"\n✓ Model downloaded successfully ({success_count}/{total_files} files)")
            return True
        else:
            print(f"\n✗ Model download incomplete ({success_count}/{total_files} files)")
            return False
    
    def try_all_mirrors(self, model_name: str) -> bool:
        """Try downloading from all available mirrors"""
        for mirror in self.mirrors:
            print(f"\nTrying mirror: {mirror}")
            if self.download_from_huggingface(model_name, mirror):
                return True
            print(f"Mirror {mirror} failed, trying next...")
            time.sleep(2)  # Brief pause between attempts
        
        return False
    
    def download_model(self, model_name: str) -> bool:
        """Download a specific model"""
        if model_name not in self.models:
            print(f"Available models: {', '.join(self.models.keys())}")
            return False
        
        # Check if model already exists
        model_dir = self.models_dir / model_name
        if model_dir.exists():
            required_files = self.models[model_name]["files"]
            existing_files = [f for f in required_files 
                            if (model_dir / f).exists() or (model_dir / "model.safetensors").exists()]
            
            if len(existing_files) >= len(required_files) * 0.8:
                print(f"Model {model_name} already exists locally")
                return True
        
        # Try downloading from mirrors
        return self.try_all_mirrors(model_name)
    
    def download_all_models(self) -> bool:
        """Download all available models"""
        print("Downloading all LiveCaption models...")
        success = True
        
        for model_name in self.models.keys():
            if not self.download_model(model_name):
                success = False
                print(f"Failed to download {model_name}")
        
        return success
    
    def list_models(self):
        """List available models and their status"""
        print("Available Models:")
        print("=" * 50)
        
        for model_name, info in self.models.items():
            model_dir = self.models_dir / model_name
            status = "Not Downloaded"
            
            if model_dir.exists():
                required_files = info["files"]
                existing_files = []
                for filename in required_files:
                    if (model_dir / filename).exists():
                        existing_files.append(filename)
                    elif filename == "pytorch_model.bin" and (model_dir / "model.safetensors").exists():
                        existing_files.append("model.safetensors")
                
                if len(existing_files) >= len(required_files) * 0.8:
                    status = "✓ Downloaded"
                else:
                    status = f"Partial ({len(existing_files)}/{len(required_files)} files)"
            
            print(f"{model_name}")
            print(f"  Description: {info['description']}")
            print(f"  Size: ~{info['size_mb']}MB")
            print(f"  Status: {status}")
            print(f"  Location: {model_dir}")
            print()

def main():
    """Main entry point"""
    downloader = ModelDownloader()
    
    if len(sys.argv) < 2:
        print("LiveCaption Model Downloader")
        print("Usage:")
        print("  python download_models.py list              # List available models")
        print("  python download_models.py all               # Download all models")
        print("  python download_models.py <model_name>      # Download specific model")
        print()
        downloader.list_models()
        return
    
    command = sys.argv[1].lower()
    
    if command == "list":
        downloader.list_models()
    elif command == "all":
        success = downloader.download_all_models()
        if not success:
            print("\n⚠ Some models failed to download. Check your internet connection.")
            print("If you're in China, try using a VPN or download manually.")
            sys.exit(1)
        else:
            print("\n✓ All models downloaded successfully!")
    elif command in downloader.models:
        success = downloader.download_model(command)
        if not success:
            print(f"\n⚠ Failed to download {command}")
            print("Try: python download_models.py list")
            sys.exit(1)
        else:
            print(f"\n✓ Model {command} downloaded successfully!")
    else:
        print(f"Unknown command or model: {command}")
        print("Use 'python download_models.py list' to see available options")
        sys.exit(1)

if __name__ == "__main__":
    main()
