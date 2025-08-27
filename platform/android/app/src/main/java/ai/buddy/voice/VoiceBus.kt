package ai.buddy.voice

import android.content.Context
import kotlinx.coroutines.*
import java.util.*
import java.util.concurrent.ConcurrentLinkedQueue

/**
 * BUDDY Voice Event Bus
 * 
 * Lightweight event system for coordinating voice components.
 * Handles communication between wake word, STT, TTS, and BUDDY brain.
 * 
 * Features:
 * - Thread-safe event dispatching
 * - Event filtering and routing
 * - Session management
 * - State tracking
 * - Error handling
 */
object VoiceBus {
    
    private val listeners = mutableMapOf<VoiceEventType, MutableList<(VoiceEvent) -> Unit>>()
    private val eventQueue = ConcurrentLinkedQueue<VoiceEvent>()
    private var processingScope: CoroutineScope? = null
    private var context: Context? = null
    
    // State tracking
    private var currentState = VoiceState.IDLE
    private var currentSessionId: String? = null
    private val sessionHistory = mutableListOf<VoiceSession>()
    
    /**
     * Initialize the voice bus
     */
    fun initialize(context: Context) {
        this.context = context
        processingScope = CoroutineScope(Dispatchers.Main + SupervisorJob())
        
        // Start event processing
        processingScope?.launch {
            processEventQueue()
        }
        
        // Register built-in event handlers
        registerBuiltInHandlers()
    }
    
    /**
     * Post an event to the bus
     */
    fun post(event: VoiceEvent) {
        eventQueue.offer(event)
    }
    
    /**
     * Subscribe to specific event types
     */
    fun subscribe(eventType: VoiceEventType, listener: (VoiceEvent) -> Unit) {
        listeners.getOrPut(eventType) { mutableListOf() }.add(listener)
    }
    
    /**
     * Unsubscribe from events
     */
    fun unsubscribe(eventType: VoiceEventType, listener: (VoiceEvent) -> Unit) {
        listeners[eventType]?.remove(listener)
    }
    
    /**
     * Get current voice state
     */
    fun getCurrentState(): VoiceState = currentState
    
    /**
     * Get current session ID
     */
    fun getCurrentSessionId(): String? = currentSessionId
    
    /**
     * Get session history
     */
    fun getSessionHistory(): List<VoiceSession> = sessionHistory.toList()
    
    private suspend fun processEventQueue() {
        while (true) {
            val event = eventQueue.poll()
            if (event != null) {
                try {
                    handleEvent(event)
                } catch (e: Exception) {
                    post(VoiceEvent.Error("Event processing error: ${e.message}"))
                }
            } else {
                delay(10) // Brief pause when no events
            }
        }
    }
    
    private fun handleEvent(event: VoiceEvent) {
        // Update state based on event
        updateState(event)
        
        // Update session tracking
        updateSession(event)
        
        // Dispatch to registered listeners
        listeners[event.type]?.forEach { listener ->
            try {
                listener(event)
            } catch (e: Exception) {
                // Log listener error but continue processing
            }
        }
        
        // Log important events
        logEvent(event)
    }
    
    private fun updateState(event: VoiceEvent) {
        val newState = when (event.type) {
            VoiceEventType.WAKE_WORD_LISTENING -> VoiceState.LISTENING_FOR_WAKE
            VoiceEventType.WAKE_WORD_DETECTED -> VoiceState.WAKE_DETECTED
            VoiceEventType.STT_STARTED -> VoiceState.STT_ACTIVE
            VoiceEventType.BUDDY_REQUEST -> VoiceState.PROCESSING
            VoiceEventType.TTS_STARTED -> VoiceState.TTS_SPEAKING
            VoiceEventType.TTS_FINISHED -> VoiceState.LISTENING_FOR_WAKE
            VoiceEventType.STT_STOPPED -> VoiceState.LISTENING_FOR_WAKE
            VoiceEventType.WAKE_WORD_STOPPED -> VoiceState.IDLE
            VoiceEventType.ERROR -> VoiceState.ERROR
            else -> currentState
        }
        
        if (newState != currentState) {
            val previousState = currentState
            currentState = newState
            post(VoiceEvent.StateChanged(previousState, newState))
        }
    }
    
    private fun updateSession(event: VoiceEvent) {
        when (event.type) {
            VoiceEventType.WAKE_WORD_DETECTED -> {
                startNewSession()
            }
            VoiceEventType.STT_FINAL_RESULT -> {
                currentSessionId?.let { sessionId ->
                    if (event is VoiceEvent.SttFinalResult) {
                        updateCurrentSession { 
                            it.copy(recognizedText = event.text, confidence = event.confidence)
                        }
                    }
                }
            }
            VoiceEventType.BUDDY_RESPONSE -> {
                currentSessionId?.let { sessionId ->
                    if (event is VoiceEvent.BuddyResponse) {
                        updateCurrentSession {
                            it.copy(
                                responseText = event.text,
                                intent = event.intent,
                                endTime = System.currentTimeMillis()
                            )
                        }
                    }
                }
            }
            VoiceEventType.TTS_FINISHED -> {
                finishCurrentSession()
            }
            else -> { /* No session update needed */ }
        }
    }
    
    private fun startNewSession() {
        currentSessionId = UUID.randomUUID().toString()
        val session = VoiceSession(
            id = currentSessionId!!,
            startTime = System.currentTimeMillis()
        )
        sessionHistory.add(session)
        
        // Keep only last 100 sessions
        if (sessionHistory.size > 100) {
            sessionHistory.removeFirst()
        }
    }
    
    private fun updateCurrentSession(update: (VoiceSession) -> VoiceSession) {
        currentSessionId?.let { sessionId ->
            val index = sessionHistory.indexOfLast { it.id == sessionId }
            if (index >= 0) {
                sessionHistory[index] = update(sessionHistory[index])
            }
        }
    }
    
    private fun finishCurrentSession() {
        updateCurrentSession { it.copy(endTime = System.currentTimeMillis()) }
        currentSessionId = null
    }
    
    private fun registerBuiltInHandlers() {
        // Handle wake word detection
        subscribe(VoiceEventType.WAKE_WORD_DETECTED) { event ->
            // Wake word detected, prepare for STT
            context?.let { ctx ->
                TtsEngine.initialize(ctx)
            }
        }
        
        // Handle STT results
        subscribe(VoiceEventType.STT_FINAL_RESULT) { event ->
            if (event is VoiceEvent.SttFinalResult) {
                // Send to BUDDY brain
                post(VoiceEvent.BuddyRequest(event.text, currentSessionId))
            }
        }
        
        // Handle BUDDY responses
        subscribe(VoiceEventType.BUDDY_RESPONSE) { event ->
            if (event is VoiceEvent.BuddyResponse) {
                // Speak the response
                context?.let { ctx ->
                    TtsEngine.speak(ctx, event.text, sessionId = currentSessionId)
                }
            }
        }
        
        // Handle errors
        subscribe(VoiceEventType.ERROR) { event ->
            if (event is VoiceEvent.Error) {
                handleError(event.message)
            }
        }
        
        // Handle silence detection
        subscribe(VoiceEventType.SILENCE_DETECTED) { event ->
            // Return to wake word listening
            VoskStt.stopSession()
        }
    }
    
    private fun handleError(message: String) {
        // Log error and attempt recovery
        currentState = VoiceState.ERROR
        
        // Attempt to recover by restarting wake word detection
        context?.let { ctx ->
            WakeWordManager.start(ctx)
        }
    }
    
    private fun logEvent(event: VoiceEvent) {
        when (event.type) {
            VoiceEventType.WAKE_WORD_DETECTED,
            VoiceEventType.STT_FINAL_RESULT,
            VoiceEventType.BUDDY_RESPONSE,
            VoiceEventType.ERROR -> {
                // Log important events
                println("VoiceBus: ${event.type} - ${event.timestamp}")
            }
            else -> { /* Skip logging for routine events */ }
        }
    }
    
    /**
     * Shutdown the voice bus
     */
    fun shutdown() {
        processingScope?.cancel()
        listeners.clear()
        eventQueue.clear()
        sessionHistory.clear()
        currentSessionId = null
        currentState = VoiceState.IDLE
    }
}

/**
 * Voice event definitions
 */
sealed class VoiceEvent(val type: VoiceEventType, val timestamp: Long = System.currentTimeMillis()) {
    
    // Wake word events
    class WakeWordListening : VoiceEvent(VoiceEventType.WAKE_WORD_LISTENING)
    class WakeWordDetected(val keywordIndex: Int, val confidence: Float) : VoiceEvent(VoiceEventType.WAKE_WORD_DETECTED)
    class WakeWordStopped : VoiceEvent(VoiceEventType.WAKE_WORD_STOPPED)
    
    // STT events
    class SttStarted(val sessionId: String) : VoiceEvent(VoiceEventType.STT_STARTED)
    class SttPartialResult(val sessionId: String, val text: String) : VoiceEvent(VoiceEventType.STT_PARTIAL_RESULT)
    class SttFinalResult(val sessionId: String, val text: String, val confidence: Double) : VoiceEvent(VoiceEventType.STT_FINAL_RESULT)
    class SttStopped(val sessionId: String) : VoiceEvent(VoiceEventType.STT_STOPPED)
    
    // TTS events
    class TtsInitialized : VoiceEvent(VoiceEventType.TTS_INITIALIZED)
    class TtsStarted(val utteranceId: String) : VoiceEvent(VoiceEventType.TTS_STARTED)
    class TtsFinished(val utteranceId: String) : VoiceEvent(VoiceEventType.TTS_FINISHED)
    
    // Session events
    class SilenceDetected(val sessionId: String) : VoiceEvent(VoiceEventType.SILENCE_DETECTED)
    class SessionTimeout(val sessionId: String) : VoiceEvent(VoiceEventType.SESSION_TIMEOUT)
    
    // BUDDY events
    class BuddyRequest(val text: String, val sessionId: String?) : VoiceEvent(VoiceEventType.BUDDY_REQUEST)
    class BuddyResponse(val text: String, val intent: String?, val sessionId: String?) : VoiceEvent(VoiceEventType.BUDDY_RESPONSE)
    
    // State events
    class StateChanged(val previousState: VoiceState, val newState: VoiceState) : VoiceEvent(VoiceEventType.STATE_CHANGED)
    
    // Error events
    class Error(val message: String) : VoiceEvent(VoiceEventType.ERROR)
}

/**
 * Voice event types
 */
enum class VoiceEventType {
    // Wake word
    WAKE_WORD_LISTENING,
    WAKE_WORD_DETECTED,
    WAKE_WORD_STOPPED,
    
    // STT
    STT_STARTED,
    STT_PARTIAL_RESULT,
    STT_FINAL_RESULT,
    STT_STOPPED,
    
    // TTS
    TTS_INITIALIZED,
    TTS_STARTED,
    TTS_FINISHED,
    
    // Session
    SILENCE_DETECTED,
    SESSION_TIMEOUT,
    
    // BUDDY
    BUDDY_REQUEST,
    BUDDY_RESPONSE,
    
    // State
    STATE_CHANGED,
    
    // Error
    ERROR
}

/**
 * Voice system states
 */
enum class VoiceState {
    IDLE,
    LISTENING_FOR_WAKE,
    WAKE_DETECTED,
    STT_ACTIVE,
    PROCESSING,
    TTS_SPEAKING,
    ERROR
}

/**
 * Voice session data
 */
data class VoiceSession(
    val id: String,
    val startTime: Long,
    val endTime: Long? = null,
    val recognizedText: String? = null,
    val responseText: String? = null,
    val intent: String? = null,
    val confidence: Double? = null
) {
    val duration: Long? get() = endTime?.let { it - startTime }
    val isComplete: Boolean get() = endTime != null
}
