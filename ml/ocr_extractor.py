import cv2
import numpy as np
from paddleocr import PaddleOCR
from pyzbar import pyzbar
from PIL import Image
import os
import json

class AdvancedEventExtractor:
    """
    Advanced OCR extractor using PaddleOCR for better accuracy
    + QR code detection for automatic registration link extraction
    """
    def __init__(self):
        print("🚀 Initializing PaddleOCR (this may take a moment)...")
        # Initialize PaddleOCR with English support
        # use_angle_cls=True helps with rotated text
        # use_gpu=False for CPU (set to True if you have CUDA GPU)
        self.ocr = PaddleOCR(use_angle_cls=True, lang='en', use_gpu=False, show_log=False)
        print("✅ PaddleOCR Ready!")
    
    def preprocess_image(self, image_path):
        """
        Preprocess image for better OCR accuracy
        - Convert to grayscale
        - Denoise
        - Enhance contrast
        """
        img = cv2.imread(image_path)
        
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Denoise
        denoised = cv2.fastNlMeansDenoising(gray)
        
        # Enhance contrast using CLAHE
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced = clahe.apply(denoised)
        
        # Save preprocessed image temporarily
        temp_path = image_path.replace('.jpg', '_processed.jpg').replace('.png', '_processed.png')
        cv2.imwrite(temp_path, enhanced)
        
        return temp_path
    
    def detect_qr_codes(self, image_path):
        """
        Detect and decode QR codes in the image
        Returns list of URLs found in QR codes
        """
        try:
            # Read image
            image = cv2.imread(image_path)
            
            # Detect QR codes
            qr_codes = pyzbar.decode(image)
            
            urls = []
            for qr in qr_codes:
                # Decode the QR code data
                data = qr.data.decode('utf-8')
                
                # Check if it's a URL
                if data.startswith('http://') or data.startswith('https://'):
                    urls.append(data)
                    print(f"  🔗 Found QR code URL: {data[:50]}...")
            
            return urls
        except Exception as e:
            print(f"  ⚠️  QR detection error: {e}")
            return []
    
    def extract_text(self, image_path):
        """
        Extract text from image using PaddleOCR
        Returns cleaned text string
        """
        try:
            # Preprocess image for better accuracy
            processed_path = self.preprocess_image(image_path)
            
            # Run OCR
            result = self.ocr.ocr(processed_path, cls=True)
            
            # Clean up temporary file
            if os.path.exists(processed_path):
                os.remove(processed_path)
            
            # Extract text from results
            if result and result[0]:
                text_lines = []
                for line in result[0]:
                    # line[1][0] contains the text
                    text_lines.append(line[1][0])
                
                full_text = " ".join(text_lines)
                return full_text
            
            return ""
            
        except Exception as e:
            print(f"  ⚠️  OCR error for {image_path}: {e}")
            return ""

def process_scraped_images():
    """
    Process all scraped images with PaddleOCR + QR detection
    """
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    input_file = os.path.join(data_dir, "scraped_data.json")
    output_file = os.path.join(data_dir, "extracted_events.json")
    
    if not os.path.exists(input_file):
        print("❌ No scraped data found. Run the scraper first!")
        return
    
    with open(input_file, 'r', encoding='utf-8') as f:
        scraped_data = json.load(f)
    
    extractor = AdvancedEventExtractor()
    extracted_events = []
    
    print(f"\n🔍 Processing {len(scraped_data)} posts with PaddleOCR + QR detection...")
    print("⚡ This is MUCH faster than EasyOCR!\n")
    
    for idx, post in enumerate(scraped_data, 1):
        print(f"[{idx}/{len(scraped_data)}] Processing {post['username']}...")
        
        image_path = post.get("image_path")
        caption = post.get("caption", "")
        
        # Extract QR codes first (for registration links)
        qr_urls = []
        if image_path and os.path.exists(image_path):
            qr_urls = extractor.detect_qr_codes(image_path)
        
        # Extract text from image using PaddleOCR
        ocr_text = ""
        if image_path and os.path.exists(image_path):
            ocr_text = extractor.extract_text(image_path)
        
        # Combine caption AND OCR text
        full_content = f"{caption}\n{ocr_text}".strip()
        
        # Use first QR URL as registration link if found
        registration_link = qr_urls[0] if qr_urls else None
        
        extracted_events.append({
            "username": post["username"],
            "post_url": post.get("post_url"),
            "image_path": image_path,
            "profile_pic_url": post.get("profile_pic_url"),
            "caption": caption,
            "ocr_text": ocr_text,
            "full_content": full_content,
            "registration_link": registration_link,  # Auto-detected from QR!
            "qr_urls": qr_urls  # All QR URLs found
        })
    
    # Save extracted data
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(extracted_events, f, indent=4, ensure_ascii=False)
    
    qr_count = sum(1 for e in extracted_events if e.get('registration_link'))
    
    print(f"\n✅ PaddleOCR Extraction complete!")
    print(f"   Processed: {len(extracted_events)} posts")
    print(f"   QR codes detected: {qr_count} registration links")
    print(f"   Saved to: {output_file}")
    print(f"\n🎉 Now run: python -m ml.nlp_processor")
    print(f"   Then run: python reset_db.py")

if __name__ == "__main__":
    process_scraped_images()
