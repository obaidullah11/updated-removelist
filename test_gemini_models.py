"""
Test script to test Google Generative AI (Gemini) models availability.
This script lists all available models and tests model initialization.
"""
import os
import sys
import django
from pathlib import Path

# Set up Django environment
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'removealist_backend.settings')
django.setup()

# Import after Django setup
from django.conf import settings

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("[ERROR] google-generativeai not installed. Install with: pip install google-generativeai")


def test_list_models():
    """List all available Gemini models."""
    if not GEMINI_AVAILABLE:
        print("Cannot test: google-generativeai not available")
        return
    
    api_key = getattr(settings, 'GOOGLE_AI_API_KEY', None)
    
    if not api_key:
        print("[ERROR] GOOGLE_AI_API_KEY not configured in settings")
        return
    
    try:
        print(f"[KEY] Using API key: {api_key[:10]}...{api_key[-4:]}")
        print("\n" + "="*60)
        print("Configuring Google Generative AI...")
        print("="*60)
        
        genai.configure(api_key=api_key)
        
        print("\n[Listing] Listing all available models...")
        print("-"*60)
        
        models = list(genai.list_models())
        
        if not models:
            print("[WARNING] No models found!")
            return
        
        print(f"\n[SUCCESS] Found {len(models)} available model(s):\n")
        
        # Group models by type
        model_groups = {
            'generateContent': [],
            'embedContent': [],
            'other': []
        }
        
        for model in models:
            model_name = model.name.split('/')[-1] if '/' in model.name else model.name
            supported_methods = list(model.supported_generation_methods) if hasattr(model, 'supported_generation_methods') else []
            
            if 'generateContent' in supported_methods:
                model_groups['generateContent'].append((model_name, model, supported_methods))
            elif 'embedContent' in supported_methods:
                model_groups['embedContent'].append((model_name, model, supported_methods))
            else:
                model_groups['other'].append((model_name, model, supported_methods))
        
        # Print models that support generateContent (for text generation)
        if model_groups['generateContent']:
            print("[MODELS] Models supporting generateContent (text generation):")
            print("-"*60)
            for model_name, model, methods in model_groups['generateContent']:
                print(f"  [OK] {model_name}")
                if methods:
                    print(f"     Methods: {', '.join(methods)}")
                print()
        
        # Print embedding models
        if model_groups['embedContent']:
            print("\n[EMBED] Models supporting embedContent (embeddings):")
            print("-"*60)
            for model_name, model, methods in model_groups['embedContent']:
                print(f"  [EMB] {model_name}")
                if methods:
                    print(f"     Methods: {', '.join(methods)}")
                print()
        
        # Print other models
        if model_groups['other']:
            print("\n[OTHER] Other models:")
            print("-"*60)
            for model_name, model, methods in model_groups['other']:
                print(f"  [ALT] {model_name}")
                if methods:
                    print(f"     Methods: {', '.join(methods)}")
                print()
        
        # Test specific models
        print("\n" + "="*60)
        print("Testing model initialization...")
        print("="*60)
        
        test_models = [
            'gemini-2.5-flash',
            'gemini-2.0-flash',
            'gemini-flash-latest',
            'gemini-2.5-pro',
            'gemini-pro-latest',
            'gemini-1.5-flash',
            'gemini-1.5-pro',
            'gemini-1.0-pro',
            'gemini-pro',
        ]
        
        working_models = []
        for model_name in test_models:
            try:
                model = genai.GenerativeModel(model_name)
                print(f"  [OK] {model_name}: Initialized successfully")
                working_models.append(model_name)
            except Exception as e:
                error_msg = str(e)
                if '404' in error_msg or 'not found' in error_msg.lower():
                    print(f"  [FAIL] {model_name}: Not found/not available")
                else:
                    print(f"  [WARN] {model_name}: Error - {error_msg}")
        
        print("\n" + "="*60)
        print("Summary")
        print("="*60)
        print(f"Total models available: {len(models)}")
        print(f"Models supporting generateContent: {len(model_groups['generateContent'])}")
        print(f"Working test models: {len(working_models)}")
        if working_models:
            print(f"[RECOMMENDED] Model: {working_models[0]}")
        print()
        
        # Print all model names as a list (for easy copy-paste)
        print("="*60)
        print("All model names (for reference):")
        print("="*60)
        all_model_names = [m.name.split('/')[-1] if '/' in m.name else m.name for m in models]
        print(all_model_names)
        
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()


def test_model_generation():
    """Test generating content with available models."""
    if not GEMINI_AVAILABLE:
        print("Cannot test: google-generativeai not available")
        return
    
    api_key = getattr(settings, 'GOOGLE_AI_API_KEY', None)
    
    if not api_key:
        print("[ERROR] GOOGLE_AI_API_KEY not configured in settings")
        return
    
    try:
        genai.configure(api_key=api_key)
        
        # Try models in order of preference (newer models first)
        test_models = [
            'gemini-2.5-flash',
            'gemini-2.0-flash',
            'gemini-flash-latest',
            'gemini-2.5-pro',
            'gemini-pro-latest',
            'gemini-1.5-flash',
            'gemini-1.0-pro',
            'gemini-pro'
        ]
        
        print("\n" + "="*60)
        print("Testing content generation...")
        print("="*60)
        
        for model_name in test_models:
            try:
                model = genai.GenerativeModel(model_name)
                print(f"\n[TEST] Testing {model_name}...")
                
                test_prompt = "Say 'Hello, this is a test' in one sentence."
                response = model.generate_content(test_prompt)
                
                print(f"  [SUCCESS] Generation successful!")
                print(f"  [RESPONSE] {response.text}")
                print(f"  [OK] Model {model_name} is working correctly!")
                return True
                
            except Exception as e:
                error_msg = str(e)
                if '404' in error_msg or 'not found' in error_msg.lower():
                    print(f"  [FAIL] {model_name}: Not available")
                else:
                    print(f"  [WARN] {model_name}: Error - {error_msg}")
        
        print("\n[ERROR] None of the test models worked for content generation")
        return False
        
    except Exception as e:
        print(f"[ERROR] Error during generation test: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("="*60)
    print("Google Generative AI (Gemini) Models Test")
    print("="*60)
    print()
    
    # Test 1: List all models
    test_list_models()
    
    # Test 2: Test content generation
    print("\n")
    test_model_generation()
    
    print("\n" + "="*60)
    print("Test completed!")
    print("="*60)

