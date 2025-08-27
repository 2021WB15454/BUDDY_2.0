import Foundation
import Network

/**
 * BUDDY Bridge for iOS
 * 
 * Connects voice input to BUDDY's backend intelligence.
 * Handles online/offline scenarios with local intent matching.
 */
final class BuddyBridge: ObservableObject {
    
    // MARK: - Singleton
    
    static let shared = BuddyBridge()
    
    // MARK: - Properties
    
    @Published var isOnline = false
    @Published var lastResponse: String = ""
    @Published var processingQuery = false
    
    private let networkMonitor = NWPathMonitor()
    private let monitorQueue = DispatchQueue(label: "buddy.network.monitor")
    
    // Configuration
    private var buddyServerUrl = "http://localhost:8080"
    private var apiTimeout: TimeInterval = 10.0
    private var retryAttempts = 3
    
    // Local intent matching
    private var localIntents: [String: [String: Any]] = [:]
    private let offlineResponses = [
        "greeting": [
            "Hello! I'm BUDDY, your AI assistant.",
            "Hi there! How can I help you today?",
            "Good to see you! What can I do for you?"
        ],
        "time": [
            "Let me check the time for you.",
            "Here's the current time."
        ],
        "offline": [
            "I'm currently offline, but I can still help with basic tasks.",
            "Network connection unavailable. Using offline mode.",
            "I'm working offline right now, but I'm still here to help!"
        ],
        "error": [
            "I'm sorry, I didn't understand that.",
            "Could you please repeat that?",
            "I'm having trouble understanding. Could you try again?"
        ]
    ]
    
    // MARK: - Initialization
    
    private init() {
        setupNetworkMonitoring()
        loadLocalIntents()
    }
    
    // MARK: - Public Methods
    
    func configure(serverUrl: String, timeout: TimeInterval = 10.0) {
        buddyServerUrl = serverUrl
        apiTimeout = timeout
    }
    
    func processVoiceInput(_ text: String, sessionId: String) {
        processingQuery = true
        
        Task {
            do {
                let response = try await processInput(text, sessionId: sessionId)
                
                await MainActor.run {
                    self.lastResponse = response
                    self.processingQuery = false
                    
                    VoiceBus.shared.post(.responseGenerated(text: response, type: "voice"))
                }
                
            } catch {
                await MainActor.run {
                    let fallbackResponse = self.getOfflineResponse(for: text)
                    self.lastResponse = fallbackResponse
                    self.processingQuery = false
                    
                    VoiceBus.shared.post(.bridgeError(message: error.localizedDescription))
                    VoiceBus.shared.post(.responseGenerated(text: fallbackResponse, type: "offline"))
                }
            }
        }
    }
    
    func testConnection() async -> Bool {
        do {
            let response = try await makeRequest(to: "/health", method: "GET", body: nil)
            return response != nil
        } catch {
            return false
        }
    }
    
    // MARK: - Private Methods
    
    private func processInput(_ text: String, sessionId: String) async throws -> String {
        // First try local intent matching
        if let localResponse = tryLocalIntentMatching(text) {
            return localResponse
        }
        
        // If online, try server processing
        if isOnline {
            do {
                return try await processWithServer(text, sessionId: sessionId)
            } catch {
                // Fallback to offline response
                return getOfflineResponse(for: text)
            }
        } else {
            // Offline mode
            return getOfflineResponse(for: text)
        }
    }
    
    private func processWithServer(_ text: String, sessionId: String) async throws -> String {
        let requestBody = [
            "query": text,
            "sessionId": sessionId,
            "platform": "ios",
            "timestamp": Date().timeIntervalSince1970
        ]
        
        guard let responseData = try await makeRequest(
            to: "/api/voice/process",
            method: "POST",
            body: requestBody
        ) else {
            throw BridgeError.noResponse
        }
        
        guard let response = try JSONSerialization.jsonObject(with: responseData) as? [String: Any],
              let responseText = response["response"] as? String else {
            throw BridgeError.invalidResponse
        }
        
        // Track intent if provided
        if let intent = response["intent"] as? String,
           let confidence = response["confidence"] as? Float {
            VoiceBus.shared.post(.intentRecognized(intent: intent, confidence: confidence))
        }
        
        return responseText
    }
    
    private func tryLocalIntentMatching(_ text: String) -> String? {
        let lowercaseText = text.lowercased()
        
        // Simple intent patterns
        if lowercaseText.contains("hello") || lowercaseText.contains("hi") || lowercaseText.contains("hey") {
            return getRandomResponse(for: "greeting")
        }
        
        if lowercaseText.contains("time") || lowercaseText.contains("clock") {
            let formatter = DateFormatter()
            formatter.timeStyle = .short
            let timeString = formatter.string(from: Date())
            return "The current time is \\(timeString)."
        }
        
        if lowercaseText.contains("date") || lowercaseText.contains("today") {
            let formatter = DateFormatter()
            formatter.dateStyle = .full
            let dateString = formatter.string(from: Date())
            return "Today is \\(dateString)."
        }
        
        if lowercaseText.contains("weather") {
            return "I'd need an internet connection to check the weather for you."
        }
        
        if lowercaseText.contains("email") {
            return "I'd need to connect to your email service to help with that."
        }
        
        if lowercaseText.contains("remind") || lowercaseText.contains("reminder") {
            return "I can help with reminders when connected to the server."
        }
        
        return nil
    }
    
    private func getOfflineResponse(for text: String) -> String {
        // Try local intent first
        if let localResponse = tryLocalIntentMatching(text) {
            return localResponse
        }
        
        // Default offline response
        let responses = offlineResponses["offline"] ?? ["I'm working offline right now."]
        return responses.randomElement() ?? "I'm currently offline but still here to help."
    }
    
    private func getRandomResponse(for intent: String) -> String {
        guard let responses = offlineResponses[intent] as? [String] else {
            return "I'm here to help!"
        }
        return responses.randomElement() ?? responses.first ?? "I'm here to help!"
    }
    
    private func makeRequest(
        to endpoint: String,
        method: String,
        body: [String: Any]?
    ) async throws -> Data? {
        
        guard let url = URL(string: buddyServerUrl + endpoint) else {
            throw BridgeError.invalidUrl
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = method
        request.timeoutInterval = apiTimeout
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        if let body = body {
            request.httpBody = try JSONSerialization.data(withJSONObject: body)
        }
        
        let (data, response) = try await URLSession.shared.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse else {
            throw BridgeError.invalidResponse
        }
        
        guard httpResponse.statusCode == 200 else {
            throw BridgeError.serverError(httpResponse.statusCode)
        }
        
        return data
    }
    
    private func setupNetworkMonitoring() {
        networkMonitor.pathUpdateHandler = { [weak self] path in
            DispatchQueue.main.async {
                self?.isOnline = path.status == .satisfied
            }
        }
        networkMonitor.start(queue: monitorQueue)
    }
    
    private func loadLocalIntents() {
        // Load local intents from bundle if available
        guard let url = Bundle.main.url(forResource: "intents", withExtension: "json"),
              let data = try? Data(contentsOf: url),
              let intents = try? JSONSerialization.jsonObject(with: data) as? [String: [String: Any]] else {
            return
        }
        
        localIntents = intents
    }
}

// MARK: - Error Types

enum BridgeError: Error, LocalizedError {
    case invalidUrl
    case noResponse
    case invalidResponse
    case serverError(Int)
    case networkUnavailable
    
    var errorDescription: String? {
        switch self {
        case .invalidUrl:
            return "Invalid server URL"
        case .noResponse:
            return "No response from server"
        case .invalidResponse:
            return "Invalid response format"
        case .serverError(let code):
            return "Server error: \\(code)"
        case .networkUnavailable:
            return "Network unavailable"
        }
    }
}

// MARK: - Voice Processing Extensions

extension BuddyBridge {
    
    func processQuickCommand(_ command: String) async -> String {
        switch command.lowercased() {
        case "status":
            return "BUDDY is \\(isOnline ? "online" : "offline") and ready to help."
            
        case "ping":
            if isOnline {
                let isReachable = await testConnection()
                return isReachable ? "Server is reachable." : "Server is not responding."
            } else {
                return "Currently offline."
            }
            
        case "help":
            return """
            I can help you with:
            - Time and date information
            - Basic conversations
            - Server connectivity when online
            - Task management and reminders
            Just speak naturally and I'll do my best to help!
            """
            
        default:
            return await processInput(command, sessionId: UUID().uuidString)
        }
    }
    
    func getCapabilities() -> [String] {
        var capabilities = [
            "Voice conversation",
            "Time and date queries",
            "Basic task assistance"
        ]
        
        if isOnline {
            capabilities.append(contentsOf: [
                "Weather information",
                "Email assistance",
                "Advanced task management",
                "Web search",
                "Smart home control"
            ])
        }
        
        return capabilities
    }
}

// MARK: - Session Management

extension BuddyBridge {
    
    func startConversationSession() -> String {
        let sessionId = UUID().uuidString
        
        VoiceBus.shared.post(.sessionStarted(sessionId: sessionId))
        
        // Send session start to server if online
        if isOnline {
            Task {
                try? await makeRequest(
                    to: "/api/session/start",
                    method: "POST",
                    body: ["sessionId": sessionId, "platform": "ios"]
                )
            }
        }
        
        return sessionId
    }
    
    func endConversationSession(_ sessionId: String) {
        VoiceBus.shared.post(.sessionEnded(sessionId: sessionId))
        
        // Send session end to server if online
        if isOnline {
            Task {
                try? await makeRequest(
                    to: "/api/session/end",
                    method: "POST",
                    body: ["sessionId": sessionId]
                )
            }
        }
    }
}

// MARK: - Platform Integration

#if os(iOS)
extension BuddyBridge {
    
    func configureForIOS() {
        // iOS-specific configuration
        NotificationCenter.default.addObserver(
            forName: UIApplication.willEnterForegroundNotification,
            object: nil,
            queue: .main
        ) { _ in
            Task {
                _ = await self.testConnection()
            }
        }
    }
}
#endif

#if os(watchOS)
extension BuddyBridge {
    
    func configureForWatchOS() {
        // Simplified processing for watchOS
        // Prioritize quick responses and local processing
    }
}
#endif
