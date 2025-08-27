import Foundation
import Combine

/**
 * BUDDY Voice Event Bus for iOS
 * 
 * Thread-safe event distribution system for voice components.
 * Coordinates voice flow between wake word, STT, TTS, and bridge.
 */
final class VoiceBus: ObservableObject {
    
    // MARK: - Singleton
    
    static let shared = VoiceBus()
    
    // MARK: - Properties
    
    private let eventQueue = DispatchQueue(label: "buddy.voice.bus", qos: .userInitiated)
    private var subscriptions: [String: (VoiceEvent) -> Void] = [:]
    private var eventHistory: [VoiceEvent] = []
    private let maxHistorySize = 100
    
    @Published var currentState: VoiceState = .idle
    @Published var sessionState: SessionState = .inactive
    
    // Event publishing
    private let eventSubject = PassthroughSubject<VoiceEvent, Never>()
    var eventPublisher: AnyPublisher<VoiceEvent, Never> {
        eventSubject.eraseToAnyPublisher()
    }
    
    // Session tracking
    private var currentSessionId: String?
    private var sessionStartTime: Date?
    
    // MARK: - Voice State
    
    enum VoiceState: String, CaseIterable {
        case idle = "idle"
        case listening = "listening"
        case processing = "processing"
        case speaking = "speaking"
        case error = "error"
    }
    
    enum SessionState: String, CaseIterable {
        case inactive = "inactive"
        case active = "active"
        case suspended = "suspended"
    }
    
    // MARK: - Voice Events
    
    enum VoiceEvent: Equatable {
        // Wake word events
        case wakeWordDetected(keyword: String)
        case wakeWordTimeout
        
        // STT events
        case sttStarted(sessionId: String)
        case sttPartialResult(text: String, sessionId: String)
        case sttFinalResult(text: String, sessionId: String)
        case sttFinished(sessionId: String)
        case sttError(message: String)
        
        // TTS events
        case ttsStarted(utteranceId: String)
        case ttsFinished(utteranceId: String)
        case ttsError(message: String)
        
        // Bridge events
        case intentRecognized(intent: String, confidence: Float)
        case responseGenerated(text: String, type: String)
        case bridgeError(message: String)
        
        // Session events
        case sessionStarted(sessionId: String)
        case sessionEnded(sessionId: String)
        case sessionTimeout(sessionId: String)
        
        // State events
        case stateChanged(from: VoiceState, to: VoiceState)
        case error(String)
        
        var id: String {
            switch self {
            case .wakeWordDetected(let keyword):
                return "wake_word_detected_\\(keyword)"
            case .wakeWordTimeout:
                return "wake_word_timeout"
            case .sttStarted(let sessionId):
                return "stt_started_\\(sessionId)"
            case .sttPartialResult(_, let sessionId):
                return "stt_partial_\\(sessionId)"
            case .sttFinalResult(_, let sessionId):
                return "stt_final_\\(sessionId)"
            case .sttFinished(let sessionId):
                return "stt_finished_\\(sessionId)"
            case .sttError:
                return "stt_error"
            case .ttsStarted(let utteranceId):
                return "tts_started_\\(utteranceId)"
            case .ttsFinished(let utteranceId):
                return "tts_finished_\\(utteranceId)"
            case .ttsError:
                return "tts_error"
            case .intentRecognized(let intent, _):
                return "intent_\\(intent)"
            case .responseGenerated:
                return "response_generated"
            case .bridgeError:
                return "bridge_error"
            case .sessionStarted(let sessionId):
                return "session_started_\\(sessionId)"
            case .sessionEnded(let sessionId):
                return "session_ended_\\(sessionId)"
            case .sessionTimeout(let sessionId):
                return "session_timeout_\\(sessionId)"
            case .stateChanged(let from, let to):
                return "state_\\(from.rawValue)_to_\\(to.rawValue)"
            case .error:
                return "error"
            }
        }
        
        static func == (lhs: VoiceEvent, rhs: VoiceEvent) -> Bool {
            return lhs.id == rhs.id
        }
    }
    
    // MARK: - Initialization
    
    private init() {
        setupEventHandling()
    }
    
    // MARK: - Public Methods
    
    func post(_ event: VoiceEvent) {
        eventQueue.async { [weak self] in
            guard let self = self else { return }
            
            // Add to history
            self.eventHistory.append(event)
            if self.eventHistory.count > self.maxHistorySize {
                self.eventHistory.removeFirst()
            }
            
            // Handle state changes
            self.handleStateChange(for: event)
            
            // Notify subscribers
            self.notifySubscribers(event)
            
            // Publish event
            DispatchQueue.main.async {
                self.eventSubject.send(event)
            }
        }
    }
    
    func subscribe(_ id: String, handler: @escaping (VoiceEvent) -> Void) {
        eventQueue.async { [weak self] in
            self?.subscriptions[id] = handler
        }
    }
    
    func unsubscribe(_ id: String) {
        eventQueue.async { [weak self] in
            self?.subscriptions.removeValue(forKey: id)
        }
    }
    
    func startSession() -> String {
        let sessionId = UUID().uuidString
        currentSessionId = sessionId
        sessionStartTime = Date()
        
        DispatchQueue.main.async {
            self.sessionState = .active
        }
        
        post(.sessionStarted(sessionId: sessionId))
        return sessionId
    }
    
    func endSession() {
        guard let sessionId = currentSessionId else { return }
        
        currentSessionId = nil
        sessionStartTime = nil
        
        DispatchQueue.main.async {
            self.sessionState = .inactive
        }
        
        post(.sessionEnded(sessionId: sessionId))
        setState(.idle)
    }
    
    func suspendSession() {
        DispatchQueue.main.async {
            self.sessionState = .suspended
        }
    }
    
    func resumeSession() {
        DispatchQueue.main.async {
            self.sessionState = .active
        }
    }
    
    func getCurrentSessionId() -> String? {
        return currentSessionId
    }
    
    func setState(_ newState: VoiceState) {
        let oldState = currentState
        
        DispatchQueue.main.async {
            self.currentState = newState
        }
        
        if oldState != newState {
            post(.stateChanged(from: oldState, to: newState))
        }
    }
    
    func getEventHistory() -> [VoiceEvent] {
        return eventQueue.sync {
            return eventHistory
        }
    }
    
    func clearHistory() {
        eventQueue.async { [weak self] in
            self?.eventHistory.removeAll()
        }
    }
    
    // MARK: - Private Methods
    
    private func setupEventHandling() {
        // Subscribe to own events for cross-component coordination
        subscribe("voice_bus_coordinator") { [weak self] event in
            self?.handleCrossComponentCoordination(event)
        }
    }
    
    private func handleStateChange(for event: VoiceEvent) {
        let newState: VoiceState?
        
        switch event {
        case .wakeWordDetected:
            newState = .listening
            
        case .sttStarted:
            newState = .processing
            
        case .sttFinished, .sttError:
            newState = .idle
            
        case .ttsStarted:
            newState = .speaking
            
        case .ttsFinished, .ttsError:
            newState = .idle
            
        case .error:
            newState = .error
            
        default:
            newState = nil
        }
        
        if let newState = newState {
            DispatchQueue.main.async {
                self.currentState = newState
            }
        }
    }
    
    private func notifySubscribers(_ event: VoiceEvent) {
        for (_, handler) in subscriptions {
            handler(event)
        }
    }
    
    private func handleCrossComponentCoordination(_ event: VoiceEvent) {
        switch event {
        case .wakeWordDetected:
            // Start listening session
            if sessionState == .inactive {
                _ = startSession()
            }
            
        case .sttFinalResult(let text, let sessionId):
            // Process the recognized text
            BuddyBridge.shared.processVoiceInput(text, sessionId: sessionId)
            
        case .responseGenerated(let text, _):
            // Speak the response
            TtsEngine.shared.speak(text, priority: .normal)
            
        case .sessionTimeout, .sttError, .bridgeError:
            // End session on errors or timeout
            endSession()
            
        default:
            break
        }
    }
}

// MARK: - Voice Flow Coordinator

extension VoiceBus {
    
    func startVoiceFlow() {
        guard sessionState != .active else { return }
        
        setState(.listening)
        _ = startSession()
        
        // Start wake word detection if not already running
        WakeWordManager.shared.startListening()
    }
    
    func stopVoiceFlow() {
        setState(.idle)
        endSession()
        
        // Stop all voice components
        WakeWordManager.shared.stopListening()
        VoskStt.shared.stop()
        TtsEngine.shared.stop()
    }
    
    func handleVoiceInterruption() {
        // Handle when user speaks while TTS is playing
        if currentState == .speaking {
            TtsEngine.shared.interrupt()
            setState(.listening)
            
            if let sessionId = currentSessionId {
                VoskStt.shared.startRecognition(sessionId: sessionId)
            }
        }
    }
    
    func handleAppStateChange(_ isActive: Bool) {
        if isActive {
            if sessionState == .suspended {
                resumeSession()
            }
        } else {
            if sessionState == .active {
                suspendSession()
            }
        }
    }
}

// MARK: - Debugging and Monitoring

extension VoiceBus {
    
    func printDebugInfo() {
        print("=== BUDDY Voice Bus Debug Info ===")
        print("Current State: \\(currentState)")
        print("Session State: \\(sessionState)")
        print("Session ID: \\(currentSessionId ?? "none")")
        print("Subscribers: \\(subscriptions.count)")
        print("Event History: \\(eventHistory.count) events")
        
        if !eventHistory.isEmpty {
            print("Last 5 events:")
            for event in eventHistory.suffix(5) {
                print("  - \\(event.id)")
            }
        }
        print("=====================================")
    }
    
    func getDebugInfo() -> [String: Any] {
        return [
            "currentState": currentState.rawValue,
            "sessionState": sessionState.rawValue,
            "sessionId": currentSessionId ?? "none",
            "subscriberCount": subscriptions.count,
            "eventHistoryCount": eventHistory.count,
            "lastEvents": eventHistory.suffix(5).map { $0.id }
        ]
    }
}

// MARK: - Platform Integration

#if os(iOS)
extension VoiceBus {
    
    func configureForIOS() {
        // iOS-specific voice bus configuration
        NotificationCenter.default.addObserver(
            forName: UIApplication.willEnterForegroundNotification,
            object: nil,
            queue: .main
        ) { _ in
            self.handleAppStateChange(true)
        }
        
        NotificationCenter.default.addObserver(
            forName: UIApplication.didEnterBackgroundNotification,
            object: nil,
            queue: .main
        ) { _ in
            self.handleAppStateChange(false)
        }
    }
}
#endif

#if os(watchOS)
extension VoiceBus {
    
    func configureForWatchOS() {
        // watchOS-specific configuration
        // Simplified event handling for watch constraints
        subscribe("watch_simplifier") { event in
            // Filter events for watch relevance
            switch event {
            case .wakeWordDetected, .sttFinalResult, .responseGenerated:
                // These are relevant for watch
                break
            default:
                // Skip less relevant events
                return
            }
        }
    }
}
#endif
