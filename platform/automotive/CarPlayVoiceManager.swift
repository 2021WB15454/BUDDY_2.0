import Foundation
import CarPlay

/**
 * BUDDY Voice Manager for CarPlay
 * 
 * Integrates BUDDY voice capabilities with Apple CarPlay.
 * Optimized for automotive safety and hands-free operation.
 */
@available(iOS 12.0, *)
final class CarPlayVoiceManager: NSObject, ObservableObject {
    
    // MARK: - Singleton
    
    static let shared = CarPlayVoiceManager()
    
    // MARK: - Properties
    
    @Published var isConnectedToCarPlay = false
    @Published var hasAudioFocus = false
    @Published var isDriving = false
    
    private var interfaceController: CPInterfaceController?
    private var carPlayWindow: CPWindow?
    private var currentTemplate: CPTemplate?
    
    // Voice session management
    private var voiceSessionActive = false
    private let sessionTimeout: TimeInterval = 60.0 // 1 minute for safety
    private var sessionTimer: Timer?
    
    // MARK: - Initialization
    
    private override init() {
        super.init()
        setupCarPlayNotifications()
    }
    
    // MARK: - CarPlay Connection
    
    func connectToCarPlay(interfaceController: CPInterfaceController, window: CPWindow) {
        self.interfaceController = interfaceController
        self.carPlayWindow = window
        
        isConnectedToCarPlay = true
        
        setupCarPlayInterface()
        
        AutomotiveVoiceBus.shared.post(.carPlayConnected)
    }
    
    func disconnectFromCarPlay() {
        endVoiceSession()
        
        interfaceController = nil
        carPlayWindow = nil
        currentTemplate = nil
        
        isConnectedToCarPlay = false
        
        AutomotiveVoiceBus.shared.post(.carPlayDisconnected)
    }
    
    // MARK: - Voice Session Management
    
    func startVoiceSession() {
        guard isConnectedToCarPlay, !voiceSessionActive else { return }
        
        voiceSessionActive = true
        hasAudioFocus = true
        
        // Request audio focus for voice interaction
        requestAudioFocus()
        
        // Start CarPlay-optimized voice flow
        AutomotiveVoiceBus.shared.post(.voiceSessionStarted)
        
        // Show voice interface
        showVoiceTemplate()
        
        // Start car-specific wake word detection
        CarPlayWakeWordManager.shared.startListening()
        
        // Auto-timeout for safety
        sessionTimer = Timer.scheduledTimer(withTimeInterval: sessionTimeout, repeats: false) { _ in
            self.endVoiceSession()
        }
    }
    
    func endVoiceSession() {
        guard voiceSessionActive else { return }
        
        voiceSessionActive = false
        hasAudioFocus = false
        
        sessionTimer?.invalidate()
        sessionTimer = nil
        
        CarPlayWakeWordManager.shared.stopListening()
        CarPlayTtsEngine.shared.stop()
        
        releaseAudioFocus()
        hideVoiceTemplate()
        
        AutomotiveVoiceBus.shared.post(.voiceSessionEnded)
    }
    
    // MARK: - CarPlay Interface
    
    private func setupCarPlayInterface() {
        let voiceTemplate = createVoiceTemplate()
        interfaceController?.setRootTemplate(voiceTemplate, animated: false, completion: nil)
    }
    
    private func createVoiceTemplate() -> CPTabBarTemplate {
        // Voice tab
        let voiceTab = CPListTemplate(title: "BUDDY Voice", sections: [
            createVoiceSection()
        ])
        voiceTab.tabImage = UIImage(systemName: "mic.fill")
        voiceTab.tabTitle = "Voice"
        
        // Quick actions tab
        let actionsTab = CPListTemplate(title: "Quick Actions", sections: [
            createQuickActionsSection()
        ])
        actionsTab.tabImage = UIImage(systemName: "bolt.fill")
        actionsTab.tabTitle = "Actions"
        
        let tabBarTemplate = CPTabBarTemplate(templates: [voiceTab, actionsTab])
        currentTemplate = tabBarTemplate
        
        return tabBarTemplate
    }
    
    private func createVoiceSection() -> CPListSection {
        let startVoiceItem = CPListItem(
            text: "Start Voice Assistant",
            detailText: voiceSessionActive ? "Listening..." : "Tap to activate"
        )
        startVoiceItem.handler = { [weak self] _, completion in
            if self?.voiceSessionActive == true {
                self?.endVoiceSession()
            } else {
                self?.startVoiceSession()
            }
            completion()
        }
        
        let statusItem = CPListItem(
            text: "Status",
            detailText: getStatusText()
        )
        
        return CPListSection(items: [startVoiceItem, statusItem])
    }
    
    private func createQuickActionsSection() -> CPListSection {
        let callItem = CPListItem(text: "Make Call", detailText: "Voice-activated calling")
        callItem.handler = { [weak self] _, completion in
            self?.processQuickAction("make call")
            completion()
        }
        
        let musicItem = CPListItem(text: "Play Music", detailText: "Voice music control")
        musicItem.handler = { [weak self] _, completion in
            self?.processQuickAction("play music")
            completion()
        }
        
        let navigationItem = CPListItem(text: "Navigation", detailText: "Voice navigation")
        navigationItem.handler = { [weak self] _, completion in
            self?.processQuickAction("navigate")
            completion()
        }
        
        return CPListSection(items: [callItem, musicItem, navigationItem])
    }
    
    private func showVoiceTemplate() {
        let voiceActiveTemplate = CPActionSheetTemplate(
            title: "BUDDY Voice Active",
            message: "Listening for your command...",
            actions: [
                CPAlertAction(title: "Stop", style: .cancel) { [weak self] _ in
                    self?.endVoiceSession()
                }
            ]
        )
        
        interfaceController?.presentTemplate(voiceActiveTemplate, animated: true, completion: nil)
    }
    
    private func hideVoiceTemplate() {
        interfaceController?.dismissTemplate(animated: true, completion: nil)
    }
    
    // MARK: - Quick Actions
    
    private func processQuickAction(_ action: String) {
        AutomotiveVoiceBus.shared.post(.quickActionTriggered(action))
        
        // Start voice session for the action
        if !voiceSessionActive {
            startVoiceSession()
        }
        
        // Process with automotive bridge
        CarPlayBuddyBridge.shared.processCarPlayInput(action)
    }
    
    // MARK: - Audio Management
    
    private func requestAudioFocus() {
        do {
            let audioSession = AVAudioSession.sharedInstance()
            try audioSession.setCategory(.playAndRecord, mode: .voiceChat, options: [.defaultToSpeaker, .allowBluetooth])
            try audioSession.setActive(true)
        } catch {
            AutomotiveVoiceBus.shared.post(.error("Failed to request audio focus: \(error.localizedDescription)"))
        }
    }
    
    private func releaseAudioFocus() {
        do {
            let audioSession = AVAudioSession.sharedInstance()
            try audioSession.setActive(false, options: .notifyOthersOnDeactivation)
        } catch {
            AutomotiveVoiceBus.shared.post(.error("Failed to release audio focus: \(error.localizedDescription)"))
        }
    }
    
    // MARK: - Driving State
    
    func setDrivingState(_ isDriving: Bool) {
        self.isDriving = isDriving
        
        if isDriving {
            AutomotiveVoiceBus.shared.post(.drivingModeEnabled)
        } else {
            AutomotiveVoiceBus.shared.post(.drivingModeDisabled)
        }
    }
    
    // MARK: - Status
    
    private func getStatusText() -> String {
        if voiceSessionActive {
            return "Voice session active"
        } else if isConnectedToCarPlay {
            return "CarPlay connected"
        } else {
            return "Not connected"
        }
    }
    
    // MARK: - Notifications
    
    private func setupCarPlayNotifications() {
        NotificationCenter.default.addObserver(
            forName: UIApplication.didEnterBackgroundNotification,
            object: nil,
            queue: .main
        ) { _ in
            // Handle background state
        }
        
        NotificationCenter.default.addObserver(
            forName: UIApplication.willEnterForegroundNotification,
            object: nil,
            queue: .main
        ) { _ in
            // Handle foreground state
        }
    }
}

// MARK: - CarPlay Wake Word Manager

@available(iOS 12.0, *)
final class CarPlayWakeWordManager: NSObject {
    
    static let shared = CarPlayWakeWordManager()
    
    private var isListening = false
    
    func startListening() {
        guard !isListening else { return }
        
        isListening = true
        
        // Use regular wake word manager with CarPlay-specific configuration
        WakeWordManager.shared.startListening()
        
        AutomotiveVoiceBus.shared.post(.wakeWordStarted)
    }
    
    func stopListening() {
        guard isListening else { return }
        
        isListening = false
        WakeWordManager.shared.stopListening()
        
        AutomotiveVoiceBus.shared.post(.wakeWordStopped)
    }
    
    func triggerManualWakeWord() {
        AutomotiveVoiceBus.shared.post(.wakeWordDetected("manual_carplay"))
    }
}

// MARK: - CarPlay TTS Engine

@available(iOS 12.0, *)
final class CarPlayTtsEngine: NSObject {
    
    static let shared = CarPlayTtsEngine()
    
    func speakCarPlayOptimized(_ text: String) {
        let carOptimizedText = optimizeForCarPlay(text)
        TtsEngine.shared.speak(carOptimizedText, priority: .high)
    }
    
    private func optimizeForCarPlay(_ text: String) -> String {
        // CarPlay-specific text optimizations
        let carPlayReplacements = [
            "Please": "",
            "Thank you": "Thanks", 
            "I'm going to": "I'll",
            "You can": "You can now",
            "Would you like": "Want to"
        ]
        
        var optimized = text
        for (long, short) in carPlayReplacements {
            optimized = optimized.replacingOccurrences(of: long, with: short)
        }
        
        return optimized.trimmingCharacters(in: .whitespacesAndNewlines)
    }
    
    func stop() {
        TtsEngine.shared.stop()
    }
}

// MARK: - CarPlay Buddy Bridge

@available(iOS 12.0, *)
final class CarPlayBuddyBridge: NSObject {
    
    static let shared = CarPlayBuddyBridge()
    
    func processCarPlayInput(_ input: String) {
        // Add CarPlay context to the input
        let carPlayContextInput = "In CarPlay: \(input)"
        
        BuddyBridge.shared.processVoiceInput(carPlayContextInput, sessionId: "carplay_session")
    }
}

// MARK: - Automotive Voice Bus

final class AutomotiveVoiceBus: ObservableObject {
    
    static let shared = AutomotiveVoiceBus()
    
    enum AutomotiveVoiceEvent {
        case carPlayConnected
        case carPlayDisconnected
        case voiceSessionStarted
        case voiceSessionEnded
        case wakeWordStarted
        case wakeWordStopped
        case wakeWordDetected(String)
        case quickActionTriggered(String)
        case drivingModeEnabled
        case drivingModeDisabled
        case error(String)
    }
    
    private var subscribers: [String: (AutomotiveVoiceEvent) -> Void] = [:]
    
    func post(_ event: AutomotiveVoiceEvent) {
        DispatchQueue.main.async {
            for (_, handler) in self.subscribers {
                handler(event)
            }
        }
    }
    
    func subscribe(_ id: String, handler: @escaping (AutomotiveVoiceEvent) -> Void) {
        subscribers[id] = handler
    }
    
    func unsubscribe(_ id: String) {
        subscribers.removeValue(forKey: id)
    }
}
