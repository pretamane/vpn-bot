import sys
import os
import importlib.util

def load_module_from_path(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

def extract_tid():
    ocr_path = '/home/ubuntu/vpn-bot/src/services/ocr_service.py'
    image_path = '/home/ubuntu/vpn-bot/tests/KBZ-Pay-Slip-Sample.jpeg'
    
    if not os.path.exists(ocr_path):
        print(f"Error: {ocr_path} not found")
        return
        
    if not os.path.exists(image_path):
        print(f"Error: {image_path} not found")
        return

    try:
        print(f"Loading OCRService from {ocr_path}...")
        ocr_module = load_module_from_path('ocr_service', ocr_path)
        OCRService = ocr_module.OCRService
    except Exception as e:
        print(f"Failed to load module: {e}")
        return

    print(f"Extracting text from {image_path}...")
    try:
        ocr = OCRService()
        text = ocr.extract_text(image_path)
        print("--- Extracted Text ---")
        for line in text:
            print(line)
        print("----------------------")
    except Exception as e:
        print(f"Extraction failed: {e}")

if __name__ == "__main__":
    extract_tid()
