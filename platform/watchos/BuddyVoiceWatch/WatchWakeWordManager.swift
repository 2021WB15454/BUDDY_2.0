import Foundation
import WatchKit
import AVFoundation

/**
 * BUDDY Wake Word Manager for watchOS
 * 
 * Simplified wake word detection optimized for Apple Watch constraints.
 * Focuses on battery efficiency and quick interactions.
 */
@available(watchOS 6.0, *)
final class WatchWakeWordManager: NSObject, ObservableObject {
    
    // MARK: - Singleton
    
    static let shared = WatchWakeWordManager()
    
    // MARK: - Properties
    
    @Published var isListening = false
    @Published var lastDetection: Date?
    
    private var audioEngine: AVAudioEngine?
    private var inputNode: AVAudioInputNode?
    private var isConfigured = false
    
    // Watch-specific configuration
    private let maxListeningDuration: TimeInterval = 30.0 // Battery conservation
    private let cooldownPeriod: TimeInterval = 5.0 // Prevent rapid triggers
    private var listeningTimer: Timer?
    private var lastTriggerTime: Date?
    
    // Simplified keyword detection
    private let targetKeywords = ["hey", "buddy", "ok", "watch"]
    private var audioBuffer: [Float] = []
    private let bufferSize = 4096
    
    // MARK: - Initialization
    
    private override init() {
        super.init()
        setupAudioSession()
    }
    
    // MARK: - Public Methods
    
    func configure() {
        guard !isConfigured else { return }
        
        do {
            audioEngine = AVAudioEngine()
            guard let audioEngine = audioEngine else { return }
            
            inputNode = audioEngine.inputNode
            isConfigured = true
            
            WatchVoiceBus.shared.post(.wakeWordConfigured)
            
        } catch {
            WatchVoiceBus.shared.post(.error("Wake word configuration failed: \(error.localizedDescription)"))
        }
    }
    
    func startListening() {
        guard isConfigured, !isListening else { return }
        
        // Check cooldown period
        if let lastTrigger = lastTriggerTime,
           Date().timeIntervalSince(lastTrigger) < cooldownPeriod {
            return
        }
        
        // Battery conservation check
        let batteryLevel = WKInterfaceDevice.current().batteryLevel
        if batteryLevel < 0.2 && batteryLevel != -1.0 {
            WatchVoiceBus.shared.post(.error("Low battery - wake word disabled"))
            return
        }
        
        do {
            try startAudioEngine()
            isListening = true
            
            // Auto-stop after max duration
            listeningTimer = Timer.scheduledTimer(withTimeInterval: maxListeningDuration, repeats: false) { _ in
                self.stopListening()
            }
            
            WatchVoiceBus.shared.post(.wakeWordStarted)
            
        } catch {
            WatchVoiceBus.shared.post(.error("Failed to start wake word detection: \(error.localizedDescription)"))
        }
    }
    
    func stopListening() {
        guard isListening else { return }
        
        audioEngine?.stop()
        listeningTimer?.invalidate()
        listeningTimer = nil
        
        isListening = false
        WatchVoiceBus.shared.post(.wakeWordStopped)
    }
    
    func triggerManualWakeWord() {
        // Allow manual trigger via Digital Crown or button
        lastDetection = Date()
        lastTriggerTime = Date()
        
        // Provide haptic feedback
        WKInterfaceDevice.current().play(.click)
        
        WatchVoiceBus.shared.post(.wakeWordDetected(keyword: "manual"))
    }
    
    // MARK: - Private Methods
    
    private func setupAudioSession() {
        do {
            let audioSession = AVAudioSession.sharedInstance()
            try audioSession.setCategory(.record, mode: .measurement, options: .defaultToSpeaker)
            try audioSession.setActive(true)
        } catch {
            print("Audio session setup failed: \(error)")
        }
    }
    
    private func startAudioEngine() throws {
        guard let audioEngine = audioEngine,
              let inputNode = inputNode else {
            throw WakeWordError.engineNotConfigured
        }
        
        let recordingFormat = inputNode.outputFormat(forBus: 0)
        
        inputNode.installTap(onBus: 0, bufferSize: 1024, format: recordingFormat) { [weak self] buffer, _ in
            self?.processAudioBuffer(buffer)
        }
        
        try audioEngine.start()
    }
    
    private func processAudioBuffer(_ buffer: AVAudioPCMBuffer) {
        guard let floatChannelData = buffer.floatChannelData else { return }
        
        let frameLength = Int(buffer.frameLength)
        let samples = Array(UnsafeBufferPointer(start: floatChannelData[0], count: frameLength))
        
        // Simple energy-based detection for watchOS
        let energy = samples.map { $0 * $0 }.reduce(0, +) / Float(samples.count)
        
        if energy > 0.01 { // Threshold for voice activity
            detectSimpleKeyword(samples)
        }
    }
    
    private func detectSimpleKeyword(_ samples: [Float]) {
        // Simplified keyword detection using energy patterns
        // In production, this would use a lightweight keyword model
        
        audioBuffer.append(contentsOf: samples)
        
        if audioBuffer.count > bufferSize {
            audioBuffer.removeFirst(audioBuffer.count - bufferSize)
        }
        
        // Simple pattern matching (placeholder for actual keyword detection)
        if audioBuffer.count >= bufferSize {
            let averageEnergy = audioBuffer.map { abs($0) }.reduce(0, +) / Float(audioBuffer.count)
            
            if averageEnergy > 0.02 { // Voice detected
                handlePotentialKeyword()
            }
        }
    }
    
    private func handlePotentialKeyword() {
        // In a real implementation, this would be more sophisticated
        lastDetection = Date()
        lastTriggerTime = Date()
        
        // Provide haptic feedback
        WKInterfaceDevice.current().play(.success)
        
        WatchVoiceBus.shared.post(.wakeWordDetected(keyword: "hey_buddy"))
        
        // Auto-stop listening after detection
        stopListening()
    }
}

// MARK: - Error Types

enum WakeWordError: Error {
    case engineNotConfigured
    case permissionDenied
    case batteryTooLow
    
    var localizedDescription: String {
        switch self {
        case .engineNotConfigured:
            return "Audio engine not configured"
        case .permissionDenied:
            return "Microphone permission denied"
        case .batteryTooLow:
            return "Battery too low for wake word detection"
        }
    }
}

// MARK: - Watch-Specific Extensions

@available(watchOS 6.0, *)
extension WatchWakeWordManager {
    
    func configureForWatch() {
        // Watch-specific optimizations
        configure()
        
        // Monitor battery level
        NotificationCenter.default.addObserver(
            forName: NSNotification.Name.NSProcessInfoPowerStateDidChange,
            object: nil,
            queue: .main
        ) { _ in
            self.handlePowerStateChange()
        }
    }
    
    private func handlePowerStateChange() {
        let batteryLevel = WKInterfaceDevice.current().batteryLevel
        
        if batteryLevel < 0.2 && batteryLevel != -1.0 && isListening {
            stopListening()
            WatchVoiceBus.shared.post(.error("Stopping wake word detection - low battery"))
        }
    }
    
    func handleDigitalCrownInteraction() {
        // Use Digital Crown as manual trigger
        if !isListening {
            triggerManualWakeWord()
        }
    }
    
    func handleSideButtonPress() {
        // Use side button as quick trigger
        triggerManualWakeWord()
    }
}

// MARK: - Complications Support

@available(watchOS 6.0, *)
extension WatchWakeWordManager {
    
    func getComplicationDisplayName() -> String {
        return isListening ? "BUDDY 🎤" : "BUDDY"
    }
    
    func getComplicationShortText() -> String {
        return isListening ? "Listening" : "Ready"
    }
    
    func shouldShowComplication() -> Bool {
        return isConfigured
    }
}
