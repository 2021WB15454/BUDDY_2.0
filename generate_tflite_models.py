#!/usr/bin/env python3
"""
BUDDY TFLite Model Generator
Creates placeholder TensorFlow Lite models for Flutter NLP engine testing
"""

import tensorflow as tf
import numpy as np
import os
from pathlib import Path

# Model configurations
INTENT_CLASSES = [
    "weather_query", "schedule_meeting", "send_message", "play_music", 
    "set_reminder", "search_web", "get_directions", "call_contact",
    "check_calendar", "book_flight", "order_food", "translation",
    "calculate", "tell_joke", "news_update", "control_smart_home",
    "fitness_tracking", "meditation", "shopping", "banking", "general_chat"
]

ENTITY_TYPES = [
    "PERSON", "LOCATION", "ORGANIZATION", "TIME", "DATE", "MONEY", 
    "QUANTITY", "EMAIL", "PHONE", "URL"
]

def create_intent_classifier_model():
    """Create a simple intent classification model"""
    print("🔧 Creating intent classifier model...")
    
    # Simple dense network for intent classification
    model = tf.keras.Sequential([
        tf.keras.layers.Input(shape=(128,), name='input_embeddings'),  # Text embeddings
        tf.keras.layers.Dense(64, activation='relu'),
        tf.keras.layers.Dropout(0.3),
        tf.keras.layers.Dense(32, activation='relu'),
        tf.keras.layers.Dense(len(INTENT_CLASSES), activation='softmax', name='intent_output')
    ])
    
    model.compile(
        optimizer='adam',
        loss='categorical_crossentropy',
        metrics=['accuracy']
    )
    
    # Generate some dummy training data for model creation
    X_dummy = np.random.rand(100, 128).astype(np.float32)
    y_dummy = tf.keras.utils.to_categorical(np.random.randint(0, len(INTENT_CLASSES), 100))
    
    # Brief training to initialize weights
    model.fit(X_dummy, y_dummy, epochs=1, verbose=0)
    
    return model

def create_entity_extractor_model():
    """Create a simple named entity recognition model"""
    print("🔧 Creating entity extractor model...")
    
    # Simple LSTM-based NER model
    sequence_length = 50
    vocab_size = 1000
    
    model = tf.keras.Sequential([
        tf.keras.layers.Input(shape=(sequence_length,), name='input_tokens'),
        tf.keras.layers.Embedding(vocab_size, 64, mask_zero=True),
        tf.keras.layers.LSTM(64, return_sequences=True),
        tf.keras.layers.Dropout(0.3),
        tf.keras.layers.Dense(32, activation='relu'),
        tf.keras.layers.Dense(len(ENTITY_TYPES), activation='softmax', name='entity_output')
    ])
    
    model.compile(
        optimizer='adam',
        loss='categorical_crossentropy',
        metrics=['accuracy']
    )
    
    # Generate dummy training data
    X_dummy = np.random.randint(0, vocab_size, (100, sequence_length))
    y_dummy = tf.keras.utils.to_categorical(
        np.random.randint(0, len(ENTITY_TYPES), (100, sequence_length, 1)).reshape(100, sequence_length)
    )
    
    # Brief training to initialize weights
    model.fit(X_dummy, y_dummy, epochs=1, verbose=0)
    
    return model

def convert_to_tflite(model, model_name, output_path):
    """Convert Keras model to TensorFlow Lite format"""
    print(f"📦 Converting {model_name} to TFLite...")
    
    # Create TFLite converter
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    
    # Optimization settings for mobile deployment
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    converter.target_spec.supported_types = [tf.float16]  # Use float16 for smaller size
    
    # Convert model
    tflite_model = converter.convert()
    
    # Save to file
    model_path = output_path / f"{model_name}.tflite"
    with open(model_path, 'wb') as f:
        f.write(tflite_model)
    
    # Print model info
    model_size = len(tflite_model) / (1024 * 1024)  # Size in MB
    print(f"✅ {model_name}.tflite created ({model_size:.2f} MB)")
    
    return model_path

def create_model_metadata(output_path):
    """Create metadata files for the models"""
    print("📄 Creating model metadata...")
    
    # Intent classifier metadata
    intent_metadata = {
        "name": "Intent Classifier",
        "version": "1.0.0",
        "description": "Classifies user intents from text input",
        "input_shape": [1, 128],
        "output_shape": [1, len(INTENT_CLASSES)],
        "classes": INTENT_CLASSES,
        "preprocessing": "Text should be converted to 128-dimensional embeddings",
        "postprocessing": "Apply softmax to get probability distribution"
    }
    
    # Entity extractor metadata  
    entity_metadata = {
        "name": "Entity Extractor",
        "version": "1.0.0", 
        "description": "Extracts named entities from tokenized text",
        "input_shape": [1, 50],
        "output_shape": [1, 50, len(ENTITY_TYPES)],
        "entity_types": ENTITY_TYPES,
        "preprocessing": "Text should be tokenized to max 50 tokens",
        "postprocessing": "Apply softmax per token for entity classification"
    }
    
    # Save metadata as JSON
    import json
    
    with open(output_path / "intent_classifier_metadata.json", 'w') as f:
        json.dump(intent_metadata, f, indent=2)
    
    with open(output_path / "entity_extractor_metadata.json", 'w') as f:
        json.dump(entity_metadata, f, indent=2)
    
    print("✅ Model metadata created")

def main():
    """Main function to generate TFLite models"""
    print("🚀 BUDDY TFLite Model Generator")
    print("=" * 50)
    
    # Set up output directory
    output_path = Path("apps/mobile_flutter/assets/models")
    output_path.mkdir(parents=True, exist_ok=True)
    
    try:
        # Create models
        intent_model = create_intent_classifier_model()
        entity_model = create_entity_extractor_model()
        
        # Convert to TFLite
        intent_path = convert_to_tflite(intent_model, "intent_classifier", output_path)
        entity_path = convert_to_tflite(entity_model, "entity_extractor", output_path)
        
        # Create metadata
        create_model_metadata(output_path)
        
        print("\n🎉 TFLite Model Generation Complete!")
        print("=" * 50)
        print(f"📁 Models saved to: {output_path}")
        print(f"📊 Intent Classifier: {intent_path}")
        print(f"📊 Entity Extractor: {entity_path}")
        print("\n📋 Next Steps:")
        print("1. Test models in Flutter app")
        print("2. Replace with production-trained models")
        print("3. Optimize for your specific use case")
        print("4. Implement model versioning and updates")
        
    except Exception as e:
        print(f"❌ Error generating models: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
