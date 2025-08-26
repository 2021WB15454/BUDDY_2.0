# TFLite Model Assets for BUDDY Flutter NLP Engine

This directory contains TensorFlow Lite models for the advanced NLP engine.

## Required Models

### 1. Intent Classifier (intent_classifier.tflite)
- **Purpose**: Classifies user intents from text input
- **Input**: Text embeddings or tokenized text
- **Output**: Intent classification probabilities
- **Categories**: 21 intent classes (weather, scheduling, etc.)

### 2. Entity Extractor (entity_extractor.tflite)
- **Purpose**: Extracts named entities from text
- **Input**: Text sequences
- **Output**: Entity labels and positions
- **Entities**: Person, location, time, etc.

## Model Generation Options

### Option 1: Train Custom Models
```bash
# Using TensorFlow Lite Model Maker
pip install tflite-model-maker
python train_intent_classifier.py
python train_entity_extractor.py
```

### Option 2: Convert Existing Models
```bash
# Convert from TensorFlow SavedModel
python -m tf2onnx.convert --saved-model saved_model_path --output model.onnx
python convert_to_tflite.py model.onnx
```

### Option 3: Use Pre-trained Models
- Universal Sentence Encoder Lite
- BERT-based models converted to TFLite
- DistilBERT for mobile optimization

## Model Requirements

### Intent Classifier Specifications
- **Input Shape**: [1, sequence_length] or [1, embedding_size]
- **Output Shape**: [1, 21] (21 intent classes)
- **Quantization**: INT8 for mobile optimization
- **Size**: < 10MB recommended

### Entity Extractor Specifications  
- **Input Shape**: [1, sequence_length]
- **Output Shape**: [1, sequence_length, num_entity_types]
- **Quantization**: INT8 for mobile optimization
- **Size**: < 15MB recommended

## Current Status

⚠️ **PLACEHOLDER FILES NEEDED**
The following files need to be provided:
- `intent_classifier.tflite` - Intent classification model
- `entity_extractor.tflite` - Named entity recognition model

## Integration

The models are integrated in:
- `lib/ai/advanced_nlp_engine_tflite.dart` - Main NLP engine
- `lib/ai/context_enhanced.dart` - Context processing
- `lib/ai/integration_bridge.dart` - Engine selection

## Testing

```dart
// Test model loading
final nlpEngine = AdvancedNLPEngineTFLite();
await nlpEngine.initialize();

// Test intent classification
final result = await nlpEngine.classifyIntent("What's the weather today?");
print(result.intent); // Should output: weather_query
```

## Performance Benchmarks

Target performance on mobile devices:
- Intent classification: < 50ms
- Entity extraction: < 100ms
- Memory usage: < 50MB
- Cold start: < 200ms

## Model Training Data

For custom model training, consider:
- **Intent Data**: Conversational AI datasets (ATIS, SNIPS)
- **Entity Data**: CoNLL-2003, OntoNotes 5.0
- **Domain-specific**: BUDDY conversation logs
- **Augmentation**: Paraphrasing, synonym replacement

## Deployment Notes

1. **Model Versioning**: Use semantic versioning for model updates
2. **A/B Testing**: Compare model performance in production
3. **Fallback**: Implement server-side NLP as fallback
4. **Caching**: Cache frequent predictions for performance
5. **Updates**: Over-the-air model updates for improvements
