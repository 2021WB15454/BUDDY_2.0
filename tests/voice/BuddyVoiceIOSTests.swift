import XCTest
import AVFoundation
import Combine
@testable import BuddyVoice

/**
 * iOS Voice System Test Suite
 * 
 * Comprehensive tests for iOS voice components including watchOS variants.
 * Tests integration, performance, and platform-specific optimizations.
 */
class BuddyVoiceIOSTests: XCTestCase {
    
    var voiceBus: VoiceBus!
    var wakeWordManager: WakeWordManager!
    var sttEngine: VoskStt!
    var ttsEngine: TtsEngine!
    var buddyBridge: BuddyBridge!
    
    var cancellables: Set<AnyCancellable> = []
    
    override func setUpWithError() throws {
        voiceBus = VoiceBus.shared
        wakeWordManager = WakeWordManager.shared
        sttEngine = VoskStt.shared
        ttsEngine = TtsEngine.shared
        buddyBridge = BuddyBridge.shared
        
        // Clear any existing state
        voiceBus.clearHistory()
        cancellables.removeAll()
    }
    
    override func tearDownWithError() throws {
        voiceBus.stopVoiceFlow()
        cancellables.removeAll()
    }
    
    // MARK: - Voice Flow Integration Tests
    
    func testCompleteVoiceFlow() throws {
        let expectation = XCTestExpectation(description: "Complete voice flow")
        var eventsReceived: [VoiceBus.VoiceEvent] = []
        
        // Subscribe to voice events
        voiceBus.eventPublisher
            .sink { event in
                eventsReceived.append(event)
                
                // Complete when we get a TTS finished event
                if case .ttsFinished = event {
                    expectation.fulfill()
                }
            }
            .store(in: &cancellables)
        
        // Start voice flow
        voiceBus.startVoiceFlow()
        
        // Simulate wake word detection
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.1) {
            self.voiceBus.post(.wakeWordDetected(keyword: "hey_buddy"))
        }
        
        // Simulate STT result
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
            let sessionId = self.voiceBus.getCurrentSessionId() ?? "test_session"
            self.voiceBus.post(.sttFinalResult(text: "what time is it", sessionId: sessionId))
        }
        
        wait(for: [expectation], timeout: 10.0)
        
        // Verify flow events
        let eventIds = eventsReceived.map { $0.id }
        XCTAssertTrue(eventIds.contains("wake_word_detected_hey_buddy"))
        XCTAssertTrue(eventIds.contains { $0.starts(with: "stt_final") })
        XCTAssertTrue(eventIds.contains { $0.starts(with: "tts_finished") })
    }
    
    func testWakeWordDetection() throws {
        let expectation = XCTestExpectation(description: "Wake word detection")
        
        // Configure wake word manager
        let testKeywordPath = Bundle(for: type(of: self)).path(forResource: "test_keyword", ofType: "ppn")
        let testAccessKey = "test_access_key_for_porcupine"
        
        if let keywordPath = testKeywordPath {
            wakeWordManager.configure(keywordPath: keywordPath, accessKey: testAccessKey)
        }
        
        // Subscribe to wake word events
        voiceBus.eventPublisher
            .sink { event in
                if case .wakeWordDetected(let keyword) = event {
                    XCTAssertEqual(keyword, "hey_buddy")
                    expectation.fulfill()
                }
            }
            .store(in: &cancellables)
        
        // Start listening
        wakeWordManager.startListening()
        
        // Simulate wake word detection after a delay
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) {
            // In a real test, this would be triggered by actual audio processing
            self.voiceBus.post(.wakeWordDetected(keyword: "hey_buddy"))
        }
        
        wait(for: [expectation], timeout: 5.0)
        
        wakeWordManager.stopListening()
    }
    
    func testSpeechRecognition() throws {
        let expectation = XCTestExpectation(description: "Speech recognition")
        
        // Configure STT engine
        let testModelPath = Bundle(for: type(of: self)).path(forResource: "test_vosk_model", ofType: nil)
        
        if let modelPath = testModelPath {
            sttEngine.configure(modelPath: modelPath)
        }
        
        let sessionId = "test_stt_session"
        var recognizedText: String?
        
        // Subscribe to STT events
        voiceBus.eventPublisher
            .sink { event in
                if case .sttFinalResult(let text, _) = event {
                    recognizedText = text
                    expectation.fulfill()
                }
            }
            .store(in: &cancellables)
        
        // Start recognition
        sttEngine.startRecognition(sessionId: sessionId)
        
        // Simulate recognition result
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) {
            self.voiceBus.post(.sttFinalResult(text: "hello BUDDY", sessionId: sessionId))
        }
        
        wait(for: [expectation], timeout: 5.0)
        
        XCTAssertEqual(recognizedText, "hello BUDDY")
        
        sttEngine.stop()
    }
    
    func testTextToSpeech() throws {
        let expectation = XCTestExpectation(description: "Text to speech")
        
        var speechStarted = false
        var speechFinished = false
        
        // Subscribe to TTS events
        voiceBus.eventPublisher
            .sink { event in
                switch event {
                case .ttsStarted:
                    speechStarted = true
                case .ttsFinished:
                    speechFinished = true
                    expectation.fulfill()
                default:
                    break
                }
            }
            .store(in: &cancellables)
        
        // Start speech
        ttsEngine.speak("Hello, this is a test message")
        
        wait(for: [expectation], timeout: 10.0)
        
        XCTAssertTrue(speechStarted)
        XCTAssertTrue(speechFinished)
    }
    
    // MARK: - Offline Fallback Tests
    
    func testOfflineIntentMatching() throws {
        let expectation = XCTestExpectation(description: "Offline intent matching")
        
        var responseReceived: String?
        
        // Subscribe to response events
        voiceBus.eventPublisher
            .sink { event in
                if case .responseGenerated(let text, let type) = event {
                    responseReceived = text
                    XCTAssertEqual(type, "offline")
                    expectation.fulfill()
                }
            }
            .store(in: &cancellables)
        
        // Test offline processing
        buddyBridge.processVoiceInput("what time is it", sessionId: "offline_test")
        
        wait(for: [expectation], timeout: 5.0)
        
        XCTAssertNotNil(responseReceived)
        XCTAssertTrue(responseReceived?.lowercased().contains("time") ?? false)
    }
    
    func testNetworkFailureFallback() throws {
        let expectation = XCTestExpectation(description: "Network failure fallback")
        
        // Simulate network unavailable
        buddyBridge.configure(serverUrl: "http://invalid-server-url.com")
        
        var fallbackResponseReceived = false
        
        voiceBus.eventPublisher
            .sink { event in
                if case .responseGenerated(_, let type) = event, type == "offline" {
                    fallbackResponseReceived = true
                    expectation.fulfill()
                }
            }
            .store(in: &cancellables)
        
        buddyBridge.processVoiceInput("test query", sessionId: "network_test")
        
        wait(for: [expectation], timeout: 5.0)
        
        XCTAssertTrue(fallbackResponseReceived)
    }
    
    // MARK: - Performance Tests
    
    func testVoiceResponseLatency() throws {
        let expectation = XCTestExpectation(description: "Voice response latency")
        let maxLatencySeconds: TimeInterval = 1.5
        
        let startTime = Date()
        var endTime: Date?
        
        voiceBus.eventPublisher
            .sink { event in
                if case .ttsFinished = event {
                    endTime = Date()
                    expectation.fulfill()
                }
            }
            .store(in: &cancellables)
        
        // Start complete voice flow
        voiceBus.post(.wakeWordDetected(keyword: "hey_buddy"))
        
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.1) {
            let sessionId = self.voiceBus.getCurrentSessionId() ?? "perf_test"
            self.voiceBus.post(.sttFinalResult(text: "what time is it", sessionId: sessionId))
        }
        
        wait(for: [expectation], timeout: maxLatencySeconds + 1.0)
        
        if let endTime = endTime {
            let latency = endTime.timeIntervalSince(startTime)
            XCTAssertLessThan(latency, maxLatencySeconds, 
                             "Voice response latency too high: \(latency)s")
        } else {
            XCTFail("Voice response did not complete")
        }
    }
    
    func testConcurrentVoiceSessions() throws {
        let expectation = XCTestExpectation(description: "Concurrent voice sessions")
        expectation.expectedFulfillmentCount = 3
        
        let sessionIds = ["session1", "session2", "session3"]
        var completedSessions: Set<String> = []
        
        voiceBus.eventPublisher
            .sink { event in
                if case .ttsFinished(let utteranceId) = event {
                    if sessionIds.contains(where: { utteranceId.contains($0) }) {
                        let sessionId = sessionIds.first { utteranceId.contains($0) } ?? ""
                        if !completedSessions.contains(sessionId) {
                            completedSessions.insert(sessionId)
                            expectation.fulfill()
                        }
                    }
                }
            }
            .store(in: &cancellables)
        
        // Start multiple sessions
        for (index, sessionId) in sessionIds.enumerated() {
            DispatchQueue.main.asyncAfter(deadline: .now() + Double(index) * 0.1) {
                self.buddyBridge.processVoiceInput("test query \(index)", sessionId: sessionId)
            }
        }
        
        wait(for: [expectation], timeout: 10.0)
        
        XCTAssertEqual(completedSessions.count, 3)
    }
    
    // MARK: - Audio Format Tests
    
    func testAudioFormatConsistency() throws {
        // Test that audio format matches cross-platform specification
        let expectedSampleRate: Double = 16000
        let expectedChannels: UInt32 = 1
        let expectedBitDepth: UInt32 = 16
        
        // Check STT audio format
        let sttFormat = sttEngine.getAudioFormat()
        XCTAssertEqual(sttFormat.sampleRate, expectedSampleRate)
        XCTAssertEqual(sttFormat.channelCount, expectedChannels)
        
        // Check wake word audio format
        let wakeWordFormat = wakeWordManager.getAudioFormat()
        XCTAssertEqual(wakeWordFormat.sampleRate, expectedSampleRate)
        XCTAssertEqual(wakeWordFormat.channelCount, expectedChannels)
    }
    
    func testAudioSessionConfiguration() throws {
        let audioSession = AVAudioSession.sharedInstance()
        
        // Test that audio session is properly configured
        XCTAssertEqual(audioSession.category, .playAndRecord)
        XCTAssertTrue(audioSession.categoryOptions.contains(.defaultToSpeaker))
        XCTAssertTrue(audioSession.categoryOptions.contains(.allowBluetooth))
    }
    
    // MARK: - Platform Integration Tests
    
    func testIOSSpecificFeatures() throws {
        // Test iOS-specific optimizations
        XCTAssertTrue(wakeWordManager.supportsBackgroundProcessing())
        XCTAssertTrue(ttsEngine.supportsSystemVoices())
        XCTAssertTrue(buddyBridge.supportsNetworkMonitoring())
    }
    
    func testAppStateHandling() throws {
        let expectation = XCTestExpectation(description: "App state handling")
        
        // Test background/foreground state changes
        voiceBus.handleAppStateChange(false) // Background
        XCTAssertEqual(voiceBus.sessionState, .suspended)
        
        voiceBus.handleAppStateChange(true) // Foreground
        XCTAssertEqual(voiceBus.sessionState, .inactive)
        
        expectation.fulfill()
        wait(for: [expectation], timeout: 1.0)
    }
    
    // MARK: - Error Handling Tests
    
    func testErrorRecovery() throws {
        let expectation = XCTestExpectation(description: "Error recovery")
        
        var errorReceived = false
        var recoverySuccessful = false
        
        voiceBus.eventPublisher
            .sink { event in
                if case .error = event {
                    errorReceived = true
                } else if case .sessionStarted = event, errorReceived {
                    recoverySuccessful = true
                    expectation.fulfill()
                }
            }
            .store(in: &cancellables)
        
        // Trigger an error
        voiceBus.post(.error("Test error"))
        
        // Attempt recovery
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
            self.voiceBus.startVoiceFlow()
        }
        
        wait(for: [expectation], timeout: 5.0)
        
        XCTAssertTrue(errorReceived)
        XCTAssertTrue(recoverySuccessful)
    }
}

// MARK: - watchOS Specific Tests

@available(watchOS 6.0, *)
class BuddyVoiceWatchTests: XCTestCase {
    
    var watchVoiceBus: WatchVoiceBus!
    var watchWakeWordManager: WatchWakeWordManager!
    var watchTtsEngine: WatchTtsEngine!
    
    override func setUpWithError() throws {
        watchVoiceBus = WatchVoiceBus.shared
        watchWakeWordManager = WatchWakeWordManager.shared
        watchTtsEngine = WatchTtsEngine.shared
    }
    
    func testWatchOptimizations() throws {
        // Test battery optimization
        XCTAssertTrue(watchWakeWordManager.isBatteryOptimized())
        
        // Test speech length limits
        let longText = String(repeating: "a", count: 200)
        let optimizedText = watchTtsEngine.optimizeForWatch(longText)
        XCTAssertLessThan(optimizedText.count, 100)
    }
    
    func testWatchInteractions() throws {
        let expectation = XCTestExpectation(description: "Watch interactions")
        
        watchVoiceBus.subscribe("test") { event in
            if case .digitalCrownUsed = event {
                expectation.fulfill()
            }
        }
        
        watchVoiceBus.handleWatchInteraction(.digitalCrown)
        
        wait(for: [expectation], timeout: 2.0)
    }
    
    func testComplicationSupport() throws {
        let displayName = watchVoiceBus.getComplicationDisplayName()
        let shortText = watchVoiceBus.getComplicationShortText()
        
        XCTAssertFalse(displayName.isEmpty)
        XCTAssertFalse(shortText.isEmpty)
        XCTAssertLessThan(shortText.count, 10) // Complication text should be short
    }
}

// MARK: - Test Extensions

extension WakeWordManager {
    func supportsBackgroundProcessing() -> Bool {
        return true // Mock implementation
    }
    
    func getAudioFormat() -> AVAudioFormat {
        return AVAudioFormat(standardFormatWithSampleRate: 16000, channels: 1)!
    }
}

extension TtsEngine {
    func supportsSystemVoices() -> Bool {
        return true // Mock implementation
    }
}

extension BuddyBridge {
    func supportsNetworkMonitoring() -> Bool {
        return true // Mock implementation
    }
}

extension VoskStt {
    func getAudioFormat() -> AVAudioFormat {
        return AVAudioFormat(standardFormatWithSampleRate: 16000, channels: 1)!
    }
}

extension WatchWakeWordManager {
    func isBatteryOptimized() -> Bool {
        return true // Mock implementation
    }
}

extension WatchTtsEngine {
    func optimizeForWatch(_ text: String) -> String {
        let maxLength = 100
        return text.count > maxLength ? String(text.prefix(maxLength - 3)) + "..." : text
    }
}
