import re
import threading
import queue
import time
from typing import Callable, Optional, Dict, List
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, pipeline

class NaturalJapaneseChinese:
    """
    Natural Japanese to Chinese translation optimized for casual speech,
    including NSFW content with appropriate localization
    """
    
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.translation_queue = queue.Queue()
        self.result_callback: Optional[Callable[[str, str], None]] = None
        self.is_running = False
        self.translation_thread = None
        
        # Cache for common translations to improve speed
        self.translation_cache = {}
        
        # Natural translation patterns for casual/intimate content
        self.casual_patterns = self._load_casual_patterns()
        self.intimate_patterns = self._load_intimate_patterns()
        
        self._load_model()
    
    def _load_model(self):
        """Load lightweight Japanese-Chinese translation model"""
        print("Loading Japanese-Chinese translation model...")
        
        try:
            # Try to use a local model first, fallback to Helsinki-NLP
            model_name = "Helsinki-NLP/opus-mt-ja-zh"
            
            device = "cuda" if torch.cuda.is_available() else "cpu"
            
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
            
            if device == "cuda":
                self.model = self.model.to(device)
            
            # Create translation pipeline for faster inference
            self.translator = pipeline(
                "translation",
                model=self.model,
                tokenizer=self.tokenizer,
                device=0 if device == "cuda" else -1,
                max_length=512,
                do_sample=False,  # Deterministic for consistency
                num_beams=1       # Faster inference
            )
            
            print(f"Translation model loaded on {device}")
            
            # Warm up the model
            self._translate_text("こんにちは")
            print("Translation model warmed up")
            
        except Exception as e:
            print(f"Error loading translation model: {e}")
            # Fallback to rule-based translation
            self.model = None
            print("Using rule-based translation as fallback")
    
    def _load_casual_patterns(self) -> Dict[str, str]:
        """Load patterns for casual Japanese to natural Chinese"""
        return {
            # Common casual expressions
            r"そうだね": "是啊",
            r"そうですね": "是的呢",
            r"やばい": "糟糕",
            r"すごい": "厉害",
            r"かわいい": "可爱",
            r"きれい": "漂亮",
            r"おいしい": "好吃",
            r"つまらない": "无聊",
            r"面白い": "有趣",
            r"大丈夫": "没事",
            r"ありがとう": "谢谢",
            r"ごめん": "抱歉",
            r"お疲れ様": "辛苦了",
            
            # Emotional expressions
            r"うれしい": "开心",
            r"悲しい": "难过",
            r"怒っている": "生气",
            r"びっくり": "吓一跳",
            r"恥ずかしい": "害羞",
            
            # Reactions and interjections
            r"えー": "诶",
            r"へー": "哦",
            r"わー": "哇",
            r"うわー": "哇",
            r"あー": "啊",
            r"うー": "嗯",
            r"んー": "嗯",
            
            # Question patterns
            r"何してる": "在干嘛",
            r"どこに行く": "去哪里",
            r"いつ": "什么时候",
            r"誰": "谁",
            r"なぜ": "为什么",
            r"どうして": "为什么",
        }
    
    def _load_intimate_patterns(self) -> Dict[str, str]:
        """Load patterns for intimate/NSFW content with natural Chinese equivalents"""
        return {
            # Intimate expressions (keeping natural/casual tone)
            r"好き": "喜欢",
            r"愛してる": "爱你",
            r"会いたい": "想见你",
            r"寂しい": "寂寞",
            r"欲しい": "想要",
            r"触って": "摸摸",
            r"キス": "亲亲",
            r"抱いて": "抱抱",
            
            # Casual intimate terms
            r"かっこいい": "帅",
            r"セクシー": "性感",
            r"魅力的": "有魅力",
            
            # Natural reactions for intimate content
            r"気持ちいい": "舒服",
            r"いい感じ": "感觉不错",
            r"ドキドキ": "心跳加速",
            
            # Common NSFW terms (natural translation)
            r"エッチ": "色色",
            r"いやらしい": "下流",
            r"恥ずかしい": "羞羞",
        }
    
    def _apply_natural_patterns(self, japanese_text: str) -> str:
        """Apply natural translation patterns before model translation"""
        text = japanese_text
        
        # Apply casual patterns
        for jp_pattern, zh_replacement in self.casual_patterns.items():
            text = re.sub(jp_pattern, zh_replacement, text, flags=re.IGNORECASE)
        
        # Apply intimate patterns  
        for jp_pattern, zh_replacement in self.intimate_patterns.items():
            text = re.sub(jp_pattern, zh_replacement, text, flags=re.IGNORECASE)
        
        return text
    
    def _post_process_translation(self, chinese_text: str) -> str:
        """Post-process translation to make it more natural"""
        text = chinese_text.strip()
        
        # Remove common translation artifacts
        text = re.sub(r'^.*?>', '', text)  # Remove model prefix
        text = re.sub(r'<.*?>', '', text)  # Remove XML tags
        
        # Make more conversational
        replacements = {
            "您": "你",          # Use casual "you"
            "請": "请",          # Simplified politeness
            "非常": "很",        # More casual "very"
            "十分": "很",        # More casual "very"
            "極其": "特别",      # More casual "extremely"
            "因此": "所以",      # More casual "therefore"
            "然而": "但是",      # More casual "however"
            "並且": "而且",      # More casual "and"
        }
        
        for formal, casual in replacements.items():
            text = text.replace(formal, casual)
        
        # Clean up extra spaces and punctuation
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        return text
    
    def _translate_text(self, japanese_text: str) -> str:
        """Translate Japanese text to natural Chinese"""
        if not japanese_text.strip():
            return ""
        
        # Check cache first
        cache_key = japanese_text.strip()
        if cache_key in self.translation_cache:
            return self.translation_cache[cache_key]
        
        try:
            # Apply natural patterns first
            preprocessed_text = self._apply_natural_patterns(japanese_text)
            
            # If model is available, use it
            if self.model is not None:
                result = self.translator(preprocessed_text, max_length=512)
                chinese_text = result[0]['translation_text']
            else:
                # Fallback: use preprocessed text if it was significantly changed
                if preprocessed_text != japanese_text:
                    chinese_text = preprocessed_text
                else:
                    # Simple fallback translation
                    chinese_text = f"[翻译] {japanese_text}"
            
            # Post-process for naturalness
            final_text = self._post_process_translation(chinese_text)
            
            # Cache the result
            self.translation_cache[cache_key] = final_text
            
            # Limit cache size
            if len(self.translation_cache) > 1000:
                # Remove oldest entries
                keys_to_remove = list(self.translation_cache.keys())[:100]
                for key in keys_to_remove:
                    del self.translation_cache[key]
            
            return final_text
            
        except Exception as e:
            print(f"Translation error: {e}")
            return japanese_text  # Return original if translation fails
    
    def _translation_worker(self):
        """Worker thread for translation processing"""
        while self.is_running:
            try:
                # Get Japanese text from queue
                japanese_text = self.translation_queue.get(timeout=0.1)
                
                # Translate
                start_time = time.time()
                chinese_text = self._translate_text(japanese_text)
                translation_time = time.time() - start_time
                
                # Call result callback
                if chinese_text and self.result_callback:
                    print(f"Translation ({translation_time:.2f}s): {japanese_text} -> {chinese_text}")
                    self.result_callback(japanese_text, chinese_text)
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error in translation worker: {e}")
    
    def set_result_callback(self, callback: Callable[[str, str], None]):
        """Set callback function to receive translation results (japanese, chinese)"""
        self.result_callback = callback
    
    def translate(self, japanese_text: str):
        """Add Japanese text for translation"""
        if not self.is_running or not japanese_text.strip():
            return
        
        try:
            # Non-blocking add to queue
            self.translation_queue.put_nowait(japanese_text.strip())
        except queue.Full:
            # Drop oldest translation if queue is full
            try:
                self.translation_queue.get_nowait()
                self.translation_queue.put_nowait(japanese_text.strip())
            except queue.Empty:
                pass
    
    def start(self):
        """Start translation service"""
        if self.is_running:
            return
        
        self.is_running = True
        self.translation_thread = threading.Thread(target=self._translation_worker)
        self.translation_thread.start()
        print("Japanese-Chinese translation service started")
    
    def stop(self):
        """Stop translation service"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        if self.translation_thread:
            self.translation_thread.join(timeout=3.0)
        
        print("Japanese-Chinese translation service stopped")

# Test function
if __name__ == "__main__":
    def test_translation_callback(japanese, chinese):
        print(f"JP: {japanese}")
        print(f"ZH: {chinese}")
        print("-" * 40)
    
    translator = NaturalJapaneseChinese()
    translator.set_result_callback(test_translation_callback)
    
    try:
        translator.start()
        
        # Test translations
        test_phrases = [
            "こんにちは",
            "元気ですか",
            "やばい、すごく面白い",
            "かわいい女の子",
            "お疲れ様でした",
            "愛してるよ",
            "会いたいな"
        ]
        
        for phrase in test_phrases:
            translator.translate(phrase)
            time.sleep(1)
        
        time.sleep(3)  # Wait for processing
        
    except KeyboardInterrupt:
        translator.stop()
        print("Stopped translation test")
