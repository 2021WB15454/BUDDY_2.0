import Foundation
import Porcupine

/**
 * BUDDY Wake Word Manager for iOS
 * 
 * Handles wake word detection using Porcupine engine.
 * Optimized for iOS background processing and battery life.
 */
final class WakeWordManager: NSObject, ObservableObject {
    
    // MARK: - Properties
    
    private var porcupineManager: PorcupineManager?
    private let accessKey: String
    private let keywordPath: String
    private var sensitivity: Float = 0.6
    
    @Published var isListening = false
    @Published var lastDetectionTime: Date?
    
    // Callbacks
    var onWakeWordDetected: ((Int, Float) -> Void)?
    var onError: ((Error) -> Void)?
    
    // MARK: - Initialization
    
    init(accessKey: String, keywordPath: String) {
        self.accessKey = accessKey
        self.keywordPath = keywordPath
        super.init()
    }
    
    convenience init() {
        let accessKey = WakeWordManager.loadAccessKey()
        let keywordPath = WakeWordManager.keywordPath(for: "hey_buddy")
        self.init(accessKey: accessKey, keywordPath: keywordPath)
    }
    
    // MARK: - Public Methods
    
    func start() throws {
        guard !isListening else { return }
        
        do {
            porcupineManager = try PorcupineManager(
                accessKey: accessKey,
                keywordPaths: [keywordPath],
                sensitivities: [sensitivity],
                onDetection: { [weak self] keywordIndex in
                    self?.handleWakeWordDetection(keywordIndex: keywordIndex)
                }
            )
            
            try porcupineManager?.start()
            isListening = true
            
            // Post event to VoiceBus
            VoiceBus.shared.post(.wakeWordListening)
            
        } catch {
            onError?(error)
            VoiceBus.shared.post(.error("Wake word start failed: \\(error.localizedDescription)"))
            throw error
        }
    }
    
    func stop() {
        guard isListening else { return }
        
        porcupineManager?.stop()
        porcupineManager = nil
        isListening = false
        
        VoiceBus.shared.post(.wakeWordStopped)
    }
    
    func setSensitivity(_ value: Float) {
        sensitivity = max(0.0, min(1.0, value))
        
        if isListening {
            // Restart with new sensitivity
            stop()
            try? start()
        }
    }
    
    // MARK: - Private Methods
    
    private func handleWakeWordDetection(keywordIndex: Int) {
        lastDetectionTime = Date()
        
        // Calculate confidence (Porcupine doesn't provide this directly)
        let confidence: Float = 0.8
        
        // Notify callbacks
        onWakeWordDetected?(keywordIndex, confidence)
        
        // Post to event bus
        VoiceBus.shared.post(.wakeWordDetected(keywordIndex: keywordIndex, confidence: confidence))
        
        // Provide haptic feedback
        #if os(iOS)
        let impactFeedback = UIImpactFeedbackGenerator(style: .medium)
        impactFeedback.impactOccurred()
        #endif
        
        // Brief audio confirmation
        TtsEngine.shared.speakShort("Yes?")
        
        // Start STT session
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
            VoskStt.shared.startSession()
        }
    }
    
    // MARK: - Static Helpers
    
    private static func loadAccessKey() -> String {
        // Try to load from Info.plist first
        if let accessKey = Bundle.main.object(forInfoDictionaryKey: "PV_ACCESS_KEY") as? String,
           !accessKey.isEmpty {
            return accessKey
        }
        
        // Try to load from porcupine_access_key.txt in bundle
        if let path = Bundle.main.path(forResource: "porcupine_access_key", ofType: "txt"),
           let key = try? String(contentsOfFile: path).trimmingCharacters(in: .whitespacesAndNewlines),
           !key.isEmpty {
            return key
        }
        
        // Fallback - this should be configured in production
        fatalError("Porcupine access key not found. Please add PV_ACCESS_KEY to Info.plist or include porcupine_access_key.txt in bundle.")
    }
    
    private static func keywordPath(for keyword: String) -> String {
        guard let path = Bundle.main.path(forResource: keyword, ofType: "ppn") else {
            fatalError("Keyword file '\\(keyword).ppn' not found in bundle")
        }
        return path
    }
}

#if os(iOS)
import UIKit

// MARK: - iOS-specific extensions

extension WakeWordManager {
    
    func handleAppStateChanges() {
        NotificationCenter.default.addObserver(
            self,
            selector: #selector(appWillEnterForeground),
            name: UIApplication.willEnterForegroundNotification,
            object: nil
        )
        
        NotificationCenter.default.addObserver(
            self,
            selector: #selector(appDidEnterBackground),
            name: UIApplication.didEnterBackgroundNotification,
            object: nil
        )
    }
    
    @objc private func appWillEnterForeground() {
        // Resume wake word detection when app becomes active
        if !isListening {
            try? start()
        }
    }
    
    @objc private func appDidEnterBackground() {
        // Keep running in background if audio background mode is enabled
        // iOS will automatically manage this based on app capabilities
    }
}

#elseif os(watchOS)
import WatchKit

// MARK: - watchOS-specific extensions

extension WakeWordManager {
    
    func configureForWatch() {
        // Shorter sessions for watch
        sensitivity = 0.7 // Higher sensitivity for watch
        
        // Monitor wrist detection
        if #available(watchOS 6.0, *) {
            NotificationCenter.default.addObserver(
                self,
                selector: #selector(wristStateChanged),
                name: .WKExtensionDeviceWristStateDidChange,
                object: nil
            )
        }
    }
    
    @objc private func wristStateChanged() {
        if #available(watchOS 6.0, *) {
            let device = WKInterfaceDevice.current()
            if device.wristState == .onWrist && !isListening {
                try? start()
            } else if device.wristState == .offWrist && isListening {
                stop()
            }
        }
    }
}

#endif

// MARK: - Error Types

enum WakeWordError: Error, LocalizedError {
    case initializationFailed(String)
    case accessKeyMissing
    case keywordFileMissing(String)
    case audioPermissionDenied
    
    var errorDescription: String? {
        switch self {
        case .initializationFailed(let message):
            return "Wake word initialization failed: \\(message)"
        case .accessKeyMissing:
            return "Porcupine access key is missing"
        case .keywordFileMissing(let keyword):
            return "Keyword file missing: \\(keyword)"
        case .audioPermissionDenied:
            return "Microphone permission denied"
        }
    }
}
