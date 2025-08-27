import Foundation
import AVFoundation
import Vosk

/**
 * BUDDY Vosk Speech-to-Text for iOS
 * 
 * Real-time streaming speech recognition using Vosk.
 * Optimized for iOS with automatic silence detection.
 */
final class VoskStt: NSObject, ObservableObject {
    
    // MARK: - Singleton
    
    static let shared = VoskStt()
    
    // MARK: - Properties
    
    private let audioEngine = AVAudioEngine()
    private var recognizer: VoskRecognizer?
    private var model: VoskModel?
    private var currentSessionId: String?
    private var isProcessing = false
    private var lastSpeechTime: Date?
    
    // Configuration
    private let sampleRate: Double = 16000
    private let silenceTimeout: TimeInterval = 4.0
    private let maxSessionDuration: TimeInterval = 30.0
    
    @Published var isActive = false
    @Published var partialResult: String = ""
    @Published var sessionStartTime: Date?
    
    // Callbacks
    var onPartialResult: ((String) -> Void)?
    var onFinalResult: ((String, Double) -> Void)?
    var onSessionEnd: (() -> Void)?
    var onError: ((Error) -> Void)?
    
    // MARK: - Initialization
    
    private override init() {
        super.init()
        configureAudioSession()
    }
    
    // MARK: - Public Methods
    
    func startSession(language: String = "en-US") throws {
        guard !isActive else {
            stopSession()
        }
        
        do {
            // Load model
            try loadModel(language: language)
            
            // Configure audio engine
            try configureAudioEngine()
            
            // Start processing
            currentSessionId = UUID().uuidString
            sessionStartTime = Date()
            lastSpeechTime = Date()
            isActive = true
            isProcessing = true
            
            // Start audio engine
            try audioEngine.start()
            
            // Post event
            VoiceBus.shared.post(.sttStarted(sessionId: currentSessionId!))
            
            // Setup session timeout
            setupSessionTimeout()
            
        } catch {
            cleanup()
            onError?(error)
            VoiceBus.shared.post(.error("STT start failed: \\(error.localizedDescription)"))
            throw error
        }
    }
    
    func stopSession() {
        guard isActive else { return }
        
        isActive = false
        isProcessing = false
        
        // Get final result
        if let recognizer = recognizer {
            do {
                let finalResult = try recognizer.finalResult()
                processFinalResult(finalResult)
            } catch {
                // Ignore final result errors
            }
        }
        
        // Stop audio engine
        audioEngine.stop()
        audioEngine.inputNode.removeTap(onBus: 0)
        
        // Cleanup
        cleanup()
        
        // Post events
        if let sessionId = currentSessionId {
            VoiceBus.shared.post(.sttStopped(sessionId: sessionId))
        }
        
        // Notify callback
        onSessionEnd?()
        
        currentSessionId = nil
        sessionStartTime = nil
        partialResult = ""
    }
    
    func isSessionActive() -> Bool {
        return isActive
    }
    
    func getCurrentSessionId() -> String? {
        return currentSessionId
    }
    
    // MARK: - Private Methods
    
    private func configureAudioSession() {
        do {
            let audioSession = AVAudioSession.sharedInstance()
            
            #if os(iOS)
            try audioSession.setCategory(.playAndRecord, options: [.defaultToSpeaker, .allowBluetooth])
            #elseif os(watchOS)
            try audioSession.setCategory(.playAndRecord)
            #endif
            
            try audioSession.setActive(true)
            
        } catch {
            print("Audio session configuration failed: \\(error)")
        }
    }
    
    private func loadModel(language: String) throws {
        let modelPath = try getModelPath(for: language)
        
        do {
            model = try VoskModel(path: modelPath)
            recognizer = try VoskRecognizer(model: model!, sampleRate: Float(sampleRate))
        } catch {
            throw SttError.modelLoadFailed(error.localizedDescription)
        }
    }
    
    private func getModelPath(for language: String) throws -> String {
        let modelName: String
        
        switch language {
        case "en-US", "en":
            modelName = "en-us"
        case "es-ES", "es":
            modelName = "es"
        case "fr-FR", "fr":
            modelName = "fr"
        case "de-DE", "de":
            modelName = "de"
        default:
            modelName = "en-us"
        }
        
        guard let path = Bundle.main.path(forResource: modelName, ofType: nil, inDirectory: "models") else {
            throw SttError.modelNotFound(modelName)
        }
        
        return path
    }
    
    private func configureAudioEngine() throws {
        let inputNode = audioEngine.inputNode
        let recordingFormat = inputNode.outputFormat(forBus: 0)
        
        // Convert to 16kHz mono
        let desiredFormat = AVAudioFormat(
            standardFormatWithSampleRate: sampleRate,
            channels: 1
        )!
        
        // Install tap
        inputNode.installTap(onBus: 0, bufferSize: 2048, format: recordingFormat) { [weak self] buffer, _ in
            self?.processAudioBuffer(buffer, format: recordingFormat, targetFormat: desiredFormat)
        }
        
        audioEngine.prepare()
    }
    
    private func processAudioBuffer(_ buffer: AVAudioPCMBuffer, format: AVAudioFormat, targetFormat: AVAudioFormat) {
        guard isProcessing, let recognizer = recognizer else { return }
        
        // Convert format if needed
        let convertedBuffer: AVAudioPCMBuffer
        if format.sampleRate != targetFormat.sampleRate || format.channelCount != targetFormat.channelCount {
            guard let converter = AVAudioConverter(from: format, to: targetFormat),
                  let convertedBuf = AVAudioPCMBuffer(pcmFormat: targetFormat, frameCapacity: buffer.frameCapacity) else {
                return
            }
            
            var error: NSError?
            let status = converter.convert(to: convertedBuf, error: &error) { _, outStatus in
                outStatus.pointee = .haveData
                return buffer
            }
            
            guard status == .haveData else { return }
            convertedBuffer = convertedBuf
        } else {
            convertedBuffer = buffer
        }
        
        // Convert to Data
        guard let channelData = convertedBuffer.int16ChannelData?[0] else { return }
        let frameLength = Int(convertedBuffer.frameLength)
        let data = Data(bytes: channelData, count: frameLength * MemoryLayout<Int16>.size)
        
        // Process with Vosk
        do {
            if try recognizer.acceptWaveform(data: data) {
                let result = try recognizer.result()
                DispatchQueue.main.async {
                    self.processFinalResult(result)
                }
            } else {
                let partial = try recognizer.partialResult()
                DispatchQueue.main.async {
                    self.processPartialResult(partial)
                }
            }
        } catch {
            DispatchQueue.main.async {
                self.onError?(error)
                VoiceBus.shared.post(.error("STT processing error: \\(error.localizedDescription)"))
            }
        }
    }
    
    private func processPartialResult(_ jsonResult: String) {
        if let partial = extractText(from: jsonResult, key: "partial"), !partial.isEmpty {
            lastSpeechTime = Date()
            partialResult = partial
            onPartialResult?(partial)
            
            if let sessionId = currentSessionId {
                VoiceBus.shared.post(.sttPartialResult(sessionId: sessionId, text: partial))
            }
        }
    }
    
    private func processFinalResult(_ jsonResult: String) {
        if let text = extractText(from: jsonResult, key: "text"), !text.isEmpty {
            lastSpeechTime = Date()
            
            let confidence = extractConfidence(from: jsonResult)
            onFinalResult?(text, confidence)
            
            if let sessionId = currentSessionId {
                VoiceBus.shared.post(.sttFinalResult(sessionId: sessionId, text: text, confidence: confidence))
                
                // Send to BUDDY brain
                BuddyBridge.shared.processText(text, sessionId: sessionId)
            }
        }
    }
    
    private func extractText(from jsonString: String, key: String) -> String? {
        guard let data = jsonString.data(using: .utf8),
              let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let text = json[key] as? String else {
            return nil
        }
        return text.trimmingCharacters(in: .whitespacesAndNewlines)
    }
    
    private func extractConfidence(from jsonString: String) -> Double {
        guard let data = jsonString.data(using: .utf8),
              let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let confidence = json["confidence"] as? Double else {
            return 0.8 // Default confidence
        }
        return confidence
    }
    
    private func setupSessionTimeout() {
        DispatchQueue.global().asyncAfter(deadline: .now() + maxSessionDuration) { [weak self] in
            guard let self = self, self.isActive else { return }
            
            DispatchQueue.main.async {
                if let sessionId = self.currentSessionId {
                    VoiceBus.shared.post(.sessionTimeout(sessionId: sessionId))
                }
                self.stopSession()
            }
        }
        
        // Silence detection timer
        startSilenceDetection()
    }
    
    private func startSilenceDetection() {
        DispatchQueue.global().async { [weak self] in
            while self?.isActive == true {
                Thread.sleep(forTimeInterval: 1.0) // Check every second
                
                guard let self = self,
                      let lastSpeech = self.lastSpeechTime else { continue }
                
                if Date().timeIntervalSince(lastSpeech) > self.silenceTimeout {
                    DispatchQueue.main.async {
                        if let sessionId = self.currentSessionId {
                            VoiceBus.shared.post(.silenceDetected(sessionId: sessionId))
                        }
                        self.stopSession()
                    }
                    break
                }
            }
        }
    }
    
    private func cleanup() {
        recognizer?.close()
        recognizer = nil
        model?.close()
        model = nil
    }
}

// MARK: - Error Types

enum SttError: Error, LocalizedError {
    case modelNotFound(String)
    case modelLoadFailed(String)
    case audioEngineError(String)
    case permissionDenied
    
    var errorDescription: String? {
        switch self {
        case .modelNotFound(let model):
            return "Speech model not found: \\(model)"
        case .modelLoadFailed(let message):
            return "Failed to load speech model: \\(message)"
        case .audioEngineError(let message):
            return "Audio engine error: \\(message)"
        case .permissionDenied:
            return "Microphone permission denied"
        }
    }
}
