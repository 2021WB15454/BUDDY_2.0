import Foundation
import WatchKit
import AVFoundation

/**
 * BUDDY Text-to-Speech for watchOS
 * 
 * Simplified TTS optimized for Apple Watch speaker limitations.
 * Focuses on short, clear responses with haptic feedback.
 */
@available(watchOS 6.0, *)
final class WatchTtsEngine: NSObject, ObservableObject {
    
    // MARK: - Singleton
    
    static let shared = WatchTtsEngine()
    
    // MARK: - Properties
    
    private let synthesizer = AVSpeechSynthesizer()
    @Published var isSpeaking = false
    @Published var currentText: String = ""
    
    // Watch-specific configuration
    private let maxSpeechLength = 100 // Character limit for watch
    private let speechRate: Float = 0.6 // Slightly faster for watch
    private let speechVolume: Float = 0.8
    
    private var speechQueue: [WatchSpeechRequest] = []
    private var currentRequest: WatchSpeechRequest?
    
    // MARK: - Speech Request
    
    struct WatchSpeechRequest {
        let text: String
        let priority: Priority
        let useHaptic: Bool
        let shortForm: Bool
        let onComplete: (() -> Void)?
        
        enum Priority: Int {
            case low = 3
            case normal = 2
            case high = 1
            case urgent = 0
        }
    }
    
    // MARK: - Initialization
    
    private override init() {
        super.init()
        setupSynthesizer()
        configureForWatch()
    }
    
    // MARK: - Public Methods
    
    func speak(_ text: String, useHaptic: Bool = true) {
        speakShort(text, priority: .normal, useHaptic: useHaptic)
    }
    
    func speakShort(
        _ text: String,
        priority: WatchSpeechRequest.Priority = .normal,
        useHaptic: Bool = true,
        onComplete: (() -> Void)? = nil
    ) {
        let shortText = truncateForWatch(text)
        
        let request = WatchSpeechRequest(
            text: shortText,
            priority: priority,
            useHaptic: useHaptic,
            shortForm: true,
            onComplete: onComplete
        )
        
        addToQueue(request)
    }
    
    func speakUrgent(_ text: String) {
        // Clear queue for urgent messages
        stop()
        speechQueue.removeAll()
        
        let request = WatchSpeechRequest(
            text: truncateForWatch(text),
            priority: .urgent,
            useHaptic: true,
            shortForm: true,
            onComplete: nil
        )
        
        addToQueue(request)
    }
    
    func speakTime() {
        let formatter = DateFormatter()
        formatter.timeStyle = .short
        let timeString = formatter.string(from: Date())
        
        speakShort("It's \(timeString)", useHaptic: false)
    }
    
    func speakStatus(_ status: String) {
        let shortStatus = truncateForWatch(status)
        speakShort(shortStatus, priority: .high, useHaptic: true)
    }
    
    func stop() {
        synthesizer.stopSpeaking(at: .immediate)
        isSpeaking = false
        currentText = ""
        currentRequest = nil
        
        WatchVoiceBus.shared.post(.ttsFinished(utteranceId: "stopped"))
    }
    
    func provideFeedback(_ type: FeedbackType) {
        switch type {
        case .success:
            WKInterfaceDevice.current().play(.success)
            speakShort("Done", useHaptic: false)
            
        case .error:
            WKInterfaceDevice.current().play(.failure)
            speakShort("Error", useHaptic: false)
            
        case .listening:
            WKInterfaceDevice.current().play(.click)
            // No speech for listening state
            
        case .processing:
            WKInterfaceDevice.current().play(.start)
            // Brief processing indicator
        }
    }
    
    enum FeedbackType {
        case success
        case error
        case listening
        case processing
    }
    
    // MARK: - Private Methods
    
    private func setupSynthesizer() {
        synthesizer.delegate = self
    }
    
    private func configureForWatch() {
        // Watch-specific audio configuration
        do {
            let audioSession = AVAudioSession.sharedInstance()
            try audioSession.setCategory(.playback, mode: .spokenAudio, options: .defaultToSpeaker)
            try audioSession.setActive(true)
        } catch {
            WatchVoiceBus.shared.post(.error("TTS audio session failed: \(error.localizedDescription)"))
        }
    }
    
    private func addToQueue(_ request: WatchSpeechRequest) {
        // Insert based on priority
        if request.priority == .urgent {
            speechQueue.insert(request, at: 0)
        } else {
            speechQueue.append(request)
        }
        
        if !isSpeaking {
            processQueue()
        }
    }
    
    private func processQueue() {
        guard !isSpeaking, !speechQueue.isEmpty else { return }
        
        // Sort by priority
        speechQueue.sort { $0.priority.rawValue < $1.priority.rawValue }
        
        let nextRequest = speechQueue.removeFirst()
        currentRequest = nextRequest
        
        // Provide haptic feedback if requested
        if nextRequest.useHaptic {
            WKInterfaceDevice.current().play(.click)
        }
        
        let utterance = AVSpeechUtterance(string: nextRequest.text)
        utterance.rate = speechRate
        utterance.volume = speechVolume
        
        // Use system voice optimized for watch
        if let voice = AVSpeechSynthesisVoice(language: Locale.current.languageCode ?? "en") {
            utterance.voice = voice
        }
        
        isSpeaking = true
        currentText = nextRequest.text
        
        WatchVoiceBus.shared.post(.ttsStarted(utteranceId: nextRequest.text))
        
        synthesizer.speak(utterance)
    }
    
    private func truncateForWatch(_ text: String) -> String {
        let cleaned = text.trimmingCharacters(in: .whitespacesAndNewlines)
        
        if cleaned.count <= maxSpeechLength {
            return cleaned
        }
        
        // Truncate and add indicator
        let truncated = String(cleaned.prefix(maxSpeechLength - 3))
        return truncated + "..."
    }
    
    private func handleSpeechFinished() {
        isSpeaking = false
        currentText = ""
        
        let completedRequest = currentRequest
        currentRequest = nil
        
        completedRequest?.onComplete?()
        
        WatchVoiceBus.shared.post(.ttsFinished(utteranceId: completedRequest?.text ?? ""))
        
        // Process next in queue
        processQueue()
    }
}

// MARK: - AVSpeechSynthesizerDelegate

@available(watchOS 6.0, *)
extension WatchTtsEngine: AVSpeechSynthesizerDelegate {
    
    func speechSynthesizer(_ synthesizer: AVSpeechSynthesizer, didStart utterance: AVSpeechUtterance) {
        // Speech started
    }
    
    func speechSynthesizer(_ synthesizer: AVSpeechSynthesizer, didFinish utterance: AVSpeechUtterance) {
        handleSpeechFinished()
    }
    
    func speechSynthesizer(_ synthesizer: AVSpeechSynthesizer, didCancel utterance: AVSpeechUtterance) {
        handleSpeechFinished()
    }
}

// MARK: - Watch-Specific Responses

@available(watchOS 6.0, *)
extension WatchTtsEngine {
    
    func speakWatchOptimizedResponse(_ response: String) {
        // Convert responses to watch-friendly format
        let optimized = optimizeForWatch(response)
        speakShort(optimized, priority: .normal, useHaptic: true)
    }
    
    private func optimizeForWatch(_ text: String) -> String {
        // Common response optimizations for watch
        let replacements = [
            "I can help you with": "I can help with",
            "Let me check that for you": "Checking",
            "Here's what I found": "Found",
            "I'm sorry, but": "Sorry,",
            "Unfortunately": "Sorry,",
            "Please wait while I": "Processing",
            "According to": "Per",
            "The current time is": "It's",
            "Today's date is": "Today is"
        ]
        
        var optimized = text
        for (long, short) in replacements {
            optimized = optimized.replacingOccurrences(of: long, with: short)
        }
        
        return truncateForWatch(optimized)
    }
    
    func getQuickResponses() -> [String] {
        return [
            "OK",
            "Got it",
            "Done",
            "Yes",
            "No",
            "Maybe",
            "Later",
            "Help"
        ]
    }
    
    func speakQuickResponse(_ response: String) {
        speakShort(response, priority: .high, useHaptic: true)
    }
}

// MARK: - Complications Integration

@available(watchOS 6.0, *)
extension WatchTtsEngine {
    
    func getStatusForComplication() -> String {
        if isSpeaking {
            return "Speaking"
        } else if !speechQueue.isEmpty {
            return "Queued"
        } else {
            return "Ready"
        }
    }
    
    func hasQueuedSpeech() -> Bool {
        return !speechQueue.isEmpty
    }
    
    func getQueueCount() -> Int {
        return speechQueue.count
    }
}
