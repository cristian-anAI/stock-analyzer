#!/usr/bin/env python3
"""
Create and test Ollama trading model
"""

import subprocess
import os
from pathlib import Path


def check_ollama():
    """Check if Ollama is available"""
    try:
        result = subprocess.run(['ollama', '--version'], capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except:
        return False


def create_model():
    """Create the trading model"""
    modelfile_path = Path("books/Modelfile-libros-trading")
    
    if not modelfile_path.exists():
        print(f"Modelfile not found: {modelfile_path}")
        return False
    
    print("Creating libros-trading:8b model...")
    try:
        result = subprocess.run([
            'ollama', 'create', 'libros-trading:8b', 
            '-f', str(modelfile_path)
        ], capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print("Model created successfully!")
            return True
        else:
            print(f"Model creation failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"Error creating model: {e}")
        return False


def test_model():
    """Test the model"""
    print("Testing model...")
    try:
        result = subprocess.run([
            'ollama', 'run', 'libros-trading:8b', 
            "What is the Kelly formula?"
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("Model test passed!")
            print("Response:", result.stdout[:200] + "...")
            return True
        else:
            print(f"Test failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"Test error: {e}")
        return False


def main():
    print("Testing Ollama Trading Model Setup")
    print("=" * 40)
    
    if not check_ollama():
        print("Ollama not found. Please install from https://ollama.ai/")
        return False
    
    print("Ollama is available")
    
    if not create_model():
        return False
    
    if not test_model():
        return False
    
    print("\nSUCCESS! Model ready for use:")
    print("ollama run libros-trading:8b \"How should I fix my SHORT strategy?\"")
    
    return True


if __name__ == "__main__":
    main()