import Foundation
import AVFoundation

/**
 * BUDDY Text-to-Speech Engine for iOS
 * 
 * Provides natural speech output with offline-first approach.
 * Supports both system TTS and cloud TTS integration.
 */
final class TtsEngine: NSObject, ObservableObject {
    
    // MARK: - Singleton
    
    static let shared = TtsEngine()
    
    // MARK: - Properties
    
    private let synthesizer = AVSpeechSynthesizer()
    private var speechQueue: [SpeechRequest] = []
    private var currentRequest: SpeechRequest?
    
    @Published var isSpeaking = false
    @Published var currentText: String = ""
    
    // Configuration
    private var speechRate: Float = 0.5
    private var speechPitch: Float = 1.0
    private var preferredVoice: AVSpeechSynthesisVoice?
    
    // Callbacks
    var onSpeechStarted: (() -> Void)?
    var onSpeechFinished: (() -> Void)?
    var onSpeechError: ((Error) -> Void)?
    
    // MARK: - Speech Request
    
    struct SpeechRequest {
        let text: String
        let priority: Priority
        let interruptible: Bool
        let sessionId: String?
        let onStart: (() -> Void)?
        let onComplete: (() -> Void)?
        let onError: ((Error) -> Void)?
        
        enum Priority: Int, CaseIterable {
            case low = 3
            case normal = 2
            case high = 1
            case critical = 0
        }
    }
    
    // MARK: - Initialization
    
    private override init() {
        super.init()
        setupSynthesizer()
        configureVoice()
    }
    
    // MARK: - Public Methods
    
    func speak(_ text: String, priority: SpeechRequest.Priority = .normal) {
        speak(
            text,
            priority: priority,
            interruptible: true,
            sessionId: nil,
            onStart: nil,
            onComplete: nil,
            onError: nil
        )
    }
    
    func speakShort(_ text: String) {
        speak(
            text,
            priority: .high,
            interruptible: false,
            sessionId: nil,
            onStart: nil,
            onComplete: nil,
            onError: nil
        )
    }
    
    func speak(
        _ text: String,
        priority: SpeechRequest.Priority = .normal,
        interruptible: Bool = true,
        sessionId: String? = nil,
        onStart: (() -> Void)? = nil,
        onComplete: (() -> Void)? = nil,
        onError: ((Error) -> Void)? = nil
    ) {
        let cleanText = cleanTextForSpeech(text)
        guard !cleanText.isEmpty else { return }
        
        let request = SpeechRequest(
            text: cleanText,
            priority: priority,
            interruptible: interruptible,
            sessionId: sessionId,
            onStart: onStart,
            onComplete: onComplete,
            onError: onError
        )
        
        // Handle priority
        switch priority {
        case .critical:
            stop()
            speechQueue.removeAll()
            speechQueue.insert(request, at: 0)
        case .high:
            speechQueue.insert(request, at: 0)
        case .normal, .low:
            speechQueue.append(request)
        }
        
        if !isSpeaking {
            processQueue()
        }
    }
    
    func stop() {
        synthesizer.stopSpeaking(at: .immediate)
        isSpeaking = false
        currentText = ""
        currentRequest = nil
        speechQueue.removeAll()
    }
    
    func interrupt() {
        if currentRequest?.interruptible == true {
            synthesizer.stopSpeaking(at: .immediate)
        }
    }
    
    func setSpeechRate(_ rate: Float) {
        speechRate = max(0.1, min(1.0, rate))
    }
    
    func setSpeechPitch(_ pitch: Float) {
        speechPitch = max(0.5, min(2.0, pitch))
    }
    
    func setVoice(_ voice: AVSpeechSynthesisVoice?) {
        preferredVoice = voice
    }
    
    func getAvailableVoices() -> [AVSpeechSynthesisVoice] {
        return AVSpeechSynthesisVoice.speechVoices()
    }
    
    func getSystemLanguageVoice() -> AVSpeechSynthesisVoice? {
        let systemLanguage = Locale.current.languageCode ?? "en"
        return AVSpeechSynthesisVoice(language: systemLanguage)
    }
    
    // MARK: - Private Methods
    
    private func setupSynthesizer() {
        synthesizer.delegate = self
    }
    
    private func configureVoice() {
        // Set default voice to system language
        if preferredVoice == nil {
            preferredVoice = getSystemLanguageVoice() ?? AVSpeechSynthesisVoice(language: "en-US")
        }
    }
    
    private func processQueue() {
        guard !isSpeaking, !speechQueue.isEmpty else { return }
        
        // Sort by priority
        speechQueue.sort { $0.priority.rawValue < $1.priority.rawValue }
        
        let nextRequest = speechQueue.removeFirst()
        currentRequest = nextRequest
        
        let utterance = AVSpeechUtterance(string: nextRequest.text)
        utterance.voice = preferredVoice
        utterance.rate = speechRate
        utterance.pitchMultiplier = speechPitch
        
        #if os(iOS)
        // iOS-specific utterance configuration
        utterance.preUtteranceDelay = 0.1
        utterance.postUtteranceDelay = 0.1
        #endif
        
        isSpeaking = true
        currentText = nextRequest.text
        
        synthesizer.speak(utterance)
    }
    
    private func cleanTextForSpeech(_ text: String) -> String {
        return text
            .replacingOccurrences(of: #"[\\[\\](){}]"#, with: "", options: .regularExpression)
            .replacingOccurrences(of: #"\\s+"#, with: " ", options: .regularExpression)
            .replacingOccurrences(of: "&", with: "and")
            .replacingOccurrences(of: "@", with: "at")
            .trimmingCharacters(in: .whitespacesAndNewlines)
    }
    
    private func handleSpeechStarted() {
        isSpeaking = true
        currentRequest?.onStart?()
        onSpeechStarted?()
        
        VoiceBus.shared.post(.ttsStarted(utteranceId: currentRequest?.sessionId ?? ""))
    }
    
    private func handleSpeechFinished() {
        isSpeaking = false
        currentText = ""
        
        let completedRequest = currentRequest
        currentRequest = nil
        
        completedRequest?.onComplete?()
        onSpeechFinished?()
        
        VoiceBus.shared.post(.ttsFinished(utteranceId: completedRequest?.sessionId ?? ""))
        
        // Process next in queue
        processQueue()
    }
    
    private func handleSpeechError(_ error: Error) {
        isSpeaking = false
        currentText = ""
        
        currentRequest?.onError?(error)
        onSpeechError?(error)
        
        VoiceBus.shared.post(.error("TTS error: \\(error.localizedDescription)"))
        
        currentRequest = nil
        processQueue()
    }
}

// MARK: - AVSpeechSynthesizerDelegate

extension TtsEngine: AVSpeechSynthesizerDelegate {
    
    func speechSynthesizer(_ synthesizer: AVSpeechSynthesizer, didStart utterance: AVSpeechUtterance) {
        handleSpeechStarted()
    }
    
    func speechSynthesizer(_ synthesizer: AVSpeechSynthesizer, didFinish utterance: AVSpeechUtterance) {
        handleSpeechFinished()
    }
    
    func speechSynthesizer(_ synthesizer: AVSpeechSynthesizer, didCancel utterance: AVSpeechUtterance) {
        handleSpeechFinished()
    }
    
    func speechSynthesizer(_ synthesizer: AVSpeechSynthesizer, didPause utterance: AVSpeechUtterance) {
        // Handle pause if needed
    }
    
    func speechSynthesizer(_ synthesizer: AVSpeechSynthesizer, didContinue utterance: AVSpeechUtterance) {
        // Handle continue if needed
    }
    
    func speechSynthesizer(_ synthesizer: AVSpeechSynthesizer, willSpeakRangeOfSpeechString characterRange: NSRange, utterance: AVSpeechUtterance) {
        // Handle character range highlighting if needed
    }
}

// MARK: - Cloud TTS Integration

extension TtsEngine {
    
    func speakWithCloudTts(
        _ text: String,
        voice: String = "alloy",
        model: String = "tts-1",
        priority: SpeechRequest.Priority = .normal
    ) {
        Task {
            do {
                let audioData = try await CloudTtsEngine.shared.generateSpeech(
                    text: text,
                    voice: voice,
                    model: model
                )
                
                if let audioData = audioData {
                    await playAudioData(audioData)
                } else {
                    // Fallback to system TTS
                    speak(text, priority: priority)
                }
            } catch {
                // Fallback to system TTS
                speak(text, priority: priority)
            }
        }
    }
    
    @MainActor
    private func playAudioData(_ data: Data) async {
        do {
            let audioPlayer = try AVAudioPlayer(data: data)
            audioPlayer.delegate = self
            audioPlayer.play()
            
            isSpeaking = true
            VoiceBus.shared.post(.ttsStarted(utteranceId: "cloud_tts"))
            
        } catch {
            VoiceBus.shared.post(.error("Cloud TTS playback failed: \\(error.localizedDescription)"))
        }
    }
}

// MARK: - AVAudioPlayerDelegate

extension TtsEngine: AVAudioPlayerDelegate {
    
    func audioPlayerDidFinishPlaying(_ player: AVAudioPlayer, successfully flag: Bool) {
        isSpeaking = false
        VoiceBus.shared.post(.ttsFinished(utteranceId: "cloud_tts"))
        processQueue()
    }
    
    func audioPlayerDecodeErrorDidOccur(_ player: AVAudioPlayer, error: Error?) {
        isSpeaking = false
        if let error = error {
            VoiceBus.shared.post(.error("Audio playback error: \\(error.localizedDescription)"))
        }
        processQueue()
    }
}

// MARK: - Cloud TTS Engine

final class CloudTtsEngine {
    
    static let shared = CloudTtsEngine()
    
    private var apiKey: String?
    private var baseUrl = "https://api.openai.com/v1/audio/speech"
    
    private init() {}
    
    func configure(apiKey: String, baseUrl: String? = nil) {
        self.apiKey = apiKey
        if let baseUrl = baseUrl {
            self.baseUrl = baseUrl
        }
    }
    
    func generateSpeech(
        text: String,
        voice: String = "alloy",
        model: String = "tts-1"
    ) async throws -> Data? {
        
        guard let apiKey = apiKey else {
            throw TtsError.apiKeyMissing
        }
        
        guard let url = URL(string: baseUrl) else {
            throw TtsError.invalidUrl
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("Bearer \\(apiKey)", forHTTPHeaderField: "Authorization")
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let requestBody = [
            "model": model,
            "input": text,
            "voice": voice,
            "response_format": "mp3"
        ]
        
        request.httpBody = try JSONSerialization.data(withJSONObject: requestBody)
        
        let (data, response) = try await URLSession.shared.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw TtsError.requestFailed
        }
        
        return data
    }
}

// MARK: - Error Types

enum TtsError: Error, LocalizedError {
    case apiKeyMissing
    case invalidUrl
    case requestFailed
    case audioPlaybackFailed
    
    var errorDescription: String? {
        switch self {
        case .apiKeyMissing:
            return "TTS API key is missing"
        case .invalidUrl:
            return "Invalid TTS API URL"
        case .requestFailed:
            return "TTS API request failed"
        case .audioPlaybackFailed:
            return "Audio playback failed"
        }
    }
}
