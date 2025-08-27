import Foundation
import WatchKit
import Combine

/**
 * BUDDY Voice Event Bus for watchOS
 * 
 * Simplified event coordination optimized for Apple Watch constraints.
 * Focuses on essential events and battery-efficient processing.
 */
@available(watchOS 6.0, *)
final class WatchVoiceBus: ObservableObject {
    
    // MARK: - Singleton
    
    static let shared = WatchVoiceBus()
    
    // MARK: - Properties
    
    @Published var currentState: WatchVoiceState = .idle
    @Published var sessionActive = false
    @Published var batteryOptimized = false
    
    private var subscriptions: [String: (WatchVoiceEvent) -> Void] = [:]
    private var eventHistory: [WatchVoiceEvent] = []
    private let maxHistorySize = 20 // Reduced for watch memory constraints
    
    private let eventQueue = DispatchQueue(label: "buddy.watch.voice.bus", qos: .userInitiated)
    
    // Watch-specific properties
    private var currentSessionId: String?
    private var lastInteractionTime: Date?
    private let sessionTimeout: TimeInterval = 60.0 // Shorter for watch
    
    // MARK: - Watch Voice State
    
    enum WatchVoiceState: String, CaseIterable {
        case idle = "idle"
        case listening = "listening"
        case processing = "processing"
        case speaking = "speaking"
        case error = "error"
        case batteryConservation = "battery_conservation"
    }
    
    // MARK: - Watch Voice Events
    
    enum WatchVoiceEvent: Equatable {
        // Wake word events
        case wakeWordConfigured
        case wakeWordStarted
        case wakeWordStopped
        case wakeWordDetected(keyword: String)
        case wakeWordTimeout
        
        // STT events (simplified)
        case sttStarted
        case sttResult(text: String)
        case sttFinished
        case sttError(message: String)
        
        // TTS events
        case ttsStarted(utteranceId: String)
        case ttsFinished(utteranceId: String)
        case ttsError(message: String)
        
        // Bridge events
        case responseGenerated(text: String)
        case bridgeError(message: String)
        
        // Session events
        case sessionStarted(sessionId: String)
        case sessionEnded(sessionId: String)
        case sessionTimeout
        
        // Watch-specific events
        case digitalCrownUsed
        case sideButtonPressed
        case complicationTapped
        case batteryLevelChanged(level: Float)
        case powerStateChanged(isLowPower: Bool)
        
        // State events
        case stateChanged(from: WatchVoiceState, to: WatchVoiceState)
        case error(String)
        
        var id: String {
            switch self {
            case .wakeWordConfigured:
                return "wake_word_configured"
            case .wakeWordStarted:
                return "wake_word_started"
            case .wakeWordStopped:
                return "wake_word_stopped"
            case .wakeWordDetected(let keyword):
                return "wake_word_detected_\(keyword)"
            case .wakeWordTimeout:
                return "wake_word_timeout"
            case .sttStarted:
                return "stt_started"
            case .sttResult:
                return "stt_result"
            case .sttFinished:
                return "stt_finished"
            case .sttError:
                return "stt_error"
            case .ttsStarted(let utteranceId):
                return "tts_started_\(utteranceId)"
            case .ttsFinished(let utteranceId):
                return "tts_finished_\(utteranceId)"
            case .ttsError:
                return "tts_error"
            case .responseGenerated:
                return "response_generated"
            case .bridgeError:
                return "bridge_error"
            case .sessionStarted(let sessionId):
                return "session_started_\(sessionId)"
            case .sessionEnded(let sessionId):
                return "session_ended_\(sessionId)"
            case .sessionTimeout:
                return "session_timeout"
            case .digitalCrownUsed:
                return "digital_crown_used"
            case .sideButtonPressed:
                return "side_button_pressed"
            case .complicationTapped:
                return "complication_tapped"
            case .batteryLevelChanged:
                return "battery_level_changed"
            case .powerStateChanged:
                return "power_state_changed"
            case .stateChanged(let from, let to):
                return "state_\(from.rawValue)_to_\(to.rawValue)"
            case .error:
                return "error"
            }
        }
        
        static func == (lhs: WatchVoiceEvent, rhs: WatchVoiceEvent) -> Bool {
            return lhs.id == rhs.id
        }
    }
    
    // MARK: - Initialization
    
    private init() {
        setupWatchSpecificHandling()
        monitorBatteryLevel()
    }
    
    // MARK: - Public Methods
    
    func post(_ event: WatchVoiceEvent) {
        eventQueue.async { [weak self] in
            guard let self = self else { return }
            
            // Add to history (limited for watch)
            self.eventHistory.append(event)
            if self.eventHistory.count > self.maxHistorySize {
                self.eventHistory.removeFirst()
            }
            
            // Handle state changes
            self.handleStateChange(for: event)
            
            // Notify subscribers
            self.notifySubscribers(event)
            
            // Update interaction time
            self.lastInteractionTime = Date()
        }
    }
    
    func subscribe(_ id: String, handler: @escaping (WatchVoiceEvent) -> Void) {
        eventQueue.async { [weak self] in
            self?.subscriptions[id] = handler
        }
    }
    
    func unsubscribe(_ id: String) {
        eventQueue.async { [weak self] in
            self?.subscriptions.removeValue(forKey: id)
        }
    }
    
    func startWatchSession() -> String {
        let sessionId = "watch_\(UUID().uuidString.prefix(8))"
        currentSessionId = sessionId
        
        DispatchQueue.main.async {
            self.sessionActive = true
        }
        
        post(.sessionStarted(sessionId: sessionId))
        
        // Auto-timeout for battery conservation
        DispatchQueue.main.asyncAfter(deadline: .now() + sessionTimeout) {
            if self.currentSessionId == sessionId {
                self.endSession()
            }
        }
        
        return sessionId
    }
    
    func endSession() {
        guard let sessionId = currentSessionId else { return }
        
        currentSessionId = nil
        
        DispatchQueue.main.async {
            self.sessionActive = false
        }
        
        post(.sessionEnded(sessionId: sessionId))
        setState(.idle)
    }
    
    func setState(_ newState: WatchVoiceState) {
        let oldState = currentState
        
        DispatchQueue.main.async {
            self.currentState = newState
        }
        
        if oldState != newState {
            post(.stateChanged(from: oldState, to: newState))
        }
    }
    
    func handleWatchInteraction(_ type: WatchInteractionType) {
        switch type {
        case .digitalCrown:
            post(.digitalCrownUsed)
            WatchWakeWordManager.shared.handleDigitalCrownInteraction()
            
        case .sideButton:
            post(.sideButtonPressed)
            WatchWakeWordManager.shared.handleSideButtonPress()
            
        case .complication:
            post(.complicationTapped)
            startQuickVoiceFlow()
            
        case .force_touch:
            // Handle force touch for additional options
            break
        }
    }
    
    enum WatchInteractionType {
        case digitalCrown
        case sideButton
        case complication
        case force_touch
    }
    
    // MARK: - Private Methods
    
    private func setupWatchSpecificHandling() {
        subscribe("watch_coordinator") { [weak self] event in
            self?.handleWatchSpecificEvent(event)
        }
    }
    
    private func handleStateChange(for event: WatchVoiceEvent) {
        let newState: WatchVoiceState?
        
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
            
        case .powerStateChanged(let isLowPower):
            newState = isLowPower ? .batteryConservation : .idle
            
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
    
    private func notifySubscribers(_ event: WatchVoiceEvent) {
        for (_, handler) in subscriptions {
            handler(event)
        }
    }
    
    private func handleWatchSpecificEvent(_ event: WatchVoiceEvent) {
        switch event {
        case .wakeWordDetected:
            if !sessionActive {
                _ = startWatchSession()
            }
            
        case .sttResult(let text):
            // Process with watch-optimized bridge
            WatchBuddyBridge.shared.processWatchInput(text)
            
        case .responseGenerated(let text):
            WatchTtsEngine.shared.speakWatchOptimizedResponse(text)
            
        case .batteryLevelChanged(let level):
            handleBatteryLevelChange(level)
            
        case .powerStateChanged(let isLowPower):
            handlePowerStateChange(isLowPower)
            
        default:
            break
        }
    }
    
    private func monitorBatteryLevel() {
        Timer.scheduledTimer(withTimeInterval: 30.0, repeats: true) { _ in
            let batteryLevel = WKInterfaceDevice.current().batteryLevel
            if batteryLevel != -1.0 {
                self.post(.batteryLevelChanged(level: batteryLevel))
            }
        }
    }
    
    private func handleBatteryLevelChange(_ level: Float) {
        DispatchQueue.main.async {
            self.batteryOptimized = level < 0.3
        }
        
        if level < 0.2 {
            // Enter battery conservation mode
            setState(.batteryConservation)
            endSession()
            WatchWakeWordManager.shared.stopListening()
        }
    }
    
    private func handlePowerStateChange(_ isLowPower: Bool) {
        if isLowPower {
            setState(.batteryConservation)
            endSession()
        }
    }
    
    private func startQuickVoiceFlow() {
        guard currentState == .idle else { return }
        
        _ = startWatchSession()
        WatchTtsEngine.shared.provideFeedback(.listening)
        
        // Start simplified listening
        WatchWakeWordManager.shared.startListening()
    }
}

// MARK: - Watch Interface Integration

@available(watchOS 6.0, *)
extension WatchVoiceBus {
    
    func getStatusText() -> String {
        switch currentState {
        case .idle:
            return sessionActive ? "Ready" : "Tap to start"
        case .listening:
            return "Listening..."
        case .processing:
            return "Processing..."
        case .speaking:
            return "Speaking..."
        case .error:
            return "Error"
        case .batteryConservation:
            return "Battery save"
        }
    }
    
    func getStatusColor() -> String {
        switch currentState {
        case .idle:
            return "gray"
        case .listening:
            return "blue"
        case .processing:
            return "orange"
        case .speaking:
            return "green"
        case .error:
            return "red"
        case .batteryConservation:
            return "yellow"
        }
    }
    
    func shouldShowActiveIndicator() -> Bool {
        return sessionActive && currentState != .idle
    }
    
    func getDebugInfo() -> [String: Any] {
        return [
            "state": currentState.rawValue,
            "sessionActive": sessionActive,
            "batteryOptimized": batteryOptimized,
            "eventCount": eventHistory.count,
            "lastInteraction": lastInteractionTime?.timeIntervalSinceNow ?? 0
        ]
    }
}

// MARK: - Complications Support

@available(watchOS 6.0, *)
extension WatchVoiceBus {
    
    func getComplicationDisplayName() -> String {
        return sessionActive ? "BUDDY 🎤" : "BUDDY"
    }
    
    func getComplicationShortText() -> String {
        switch currentState {
        case .idle:
            return "Ready"
        case .listening:
            return "🎤"
        case .processing:
            return "⚡"
        case .speaking:
            return "🔊"
        case .error:
            return "❌"
        case .batteryConservation:
            return "🔋"
        }
    }
    
    func getComplicationColor() -> String {
        return getStatusColor()
    }
}
