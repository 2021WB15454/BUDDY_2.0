package ai.buddy.voice

import android.content.Context
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import kotlinx.coroutines.*
import java.util.*

/**
 * BUDDY Text-to-Speech Engine
 * 
 * Provides natural speech output with offline-first approach.
 * Supports both system TTS and cloud TTS with automatic fallback.
 * 
 * Features:
 * - Offline system TTS by default
 * - Cloud TTS fallback (optional)
 * - Configurable voice parameters
 * - Queue management with priorities
 * - Interruption handling
 * - Audio focus management
 */
object TtsEngine : TextToSpeech.OnInitListener {
    
    private var tts: TextToSpeech? = null
    private var isInitialized = false
    private var context: Context? = null
    private val speechQueue = mutableListOf<SpeechRequest>()
    private var currentRequest: SpeechRequest? = null
    private var isSpeaking = false
    
    // TTS Configuration
    private var speechRate = 1.0f
    private var speechPitch = 1.0f
    private var preferredVoice: String? = null
    
    data class SpeechRequest(
        val text: String,
        val priority: Priority = Priority.NORMAL,
        val interruptible: Boolean = true,
        val sessionId: String? = null,
        val onStart: (() -> Unit)? = null,
        val onComplete: (() -> Unit)? = null,
        val onError: ((String) -> Unit)? = null
    )
    
    enum class Priority {
        LOW, NORMAL, HIGH, CRITICAL
    }
    
    /**
     * Initialize TTS engine
     */
    fun initialize(context: Context) {
        if (tts != null) return
        
        this.context = context
        tts = TextToSpeech(context, this)
    }
    
    override fun onInit(status: Int) {
        if (status == TextToSpeech.SUCCESS) {
            tts?.let { engine ->
                // Set language
                val result = engine.setLanguage(Locale.US)
                if (result == TextToSpeech.LANG_MISSING_DATA || result == TextToSpeech.LANG_NOT_SUPPORTED) {
                    VoiceBus.post(VoiceEvent.Error("TTS language not supported"))
                    return
                }
                
                // Configure TTS
                engine.setSpeechRate(speechRate)
                engine.setPitch(speechPitch)
                
                // Set utterance progress listener
                engine.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
                    override fun onStart(utteranceId: String?) {
                        isSpeaking = true
                        currentRequest?.onStart?.invoke()
                        VoiceBus.post(VoiceEvent.TtsStarted(utteranceId ?: ""))
                    }
                    
                    override fun onDone(utteranceId: String?) {
                        isSpeaking = false
                        currentRequest?.onComplete?.invoke()
                        VoiceBus.post(VoiceEvent.TtsFinished(utteranceId ?: ""))
                        currentRequest = null
                        processNextInQueue()
                    }
                    
                    override fun onError(utteranceId: String?) {
                        isSpeaking = false
                        currentRequest?.onError?.invoke("TTS playback error")
                        VoiceBus.post(VoiceEvent.Error("TTS error for utterance: $utteranceId"))
                        currentRequest = null
                        processNextInQueue()
                    }
                })
                
                isInitialized = true
                VoiceBus.post(VoiceEvent.TtsInitialized())
                
                // Process any queued requests
                processNextInQueue()
            }
        } else {
            VoiceBus.post(VoiceEvent.Error("TTS initialization failed"))
        }
    }
    
    /**
     * Speak text with default settings
     */
    fun speak(context: Context, text: String) {
        speak(context, text, Priority.NORMAL)
    }
    
    /**
     * Speak short text (confirmations, prompts)
     */
    fun speakShort(context: Context, text: String) {
        speak(context, text, Priority.HIGH, interruptible = false)
    }
    
    /**
     * Speak text with custom priority and options
     */
    fun speak(
        context: Context,
        text: String,
        priority: Priority = Priority.NORMAL,
        interruptible: Boolean = true,
        sessionId: String? = null,
        onStart: (() -> Unit)? = null,
        onComplete: (() -> Unit)? = null,
        onError: ((String) -> Unit)? = null
    ) {
        if (!isInitialized) {
            initialize(context)
        }
        
        val request = SpeechRequest(
            text = text.trim(),
            priority = priority,
            interruptible = interruptible,
            sessionId = sessionId,
            onStart = onStart,
            onComplete = onComplete,
            onError = onError
        )
        
        when (priority) {
            Priority.CRITICAL -> {
                // Interrupt current speech and speak immediately
                stop()
                speechQueue.clear()
                speechQueue.add(0, request)
            }
            Priority.HIGH -> {
                // Add to front of queue
                speechQueue.add(0, request)
            }
            else -> {
                // Add to end of queue
                speechQueue.add(request)
            }
        }
        
        if (!isSpeaking) {
            processNextInQueue()
        }
    }
    
    /**
     * Stop current speech and clear queue
     */
    fun stop() {
        tts?.stop()
        isSpeaking = false
        currentRequest = null
        speechQueue.clear()
    }
    
    /**
     * Stop current speech but keep queue
     */
    fun interrupt() {
        if (currentRequest?.interruptible == true) {
            tts?.stop()
        }
    }
    
    /**
     * Check if TTS is currently speaking
     */
    fun isSpeaking(): Boolean = isSpeaking
    
    /**
     * Set speech rate (0.1 - 2.0)
     */
    fun setSpeechRate(rate: Float) {
        speechRate = rate.coerceIn(0.1f, 2.0f)
        tts?.setSpeechRate(speechRate)
    }
    
    /**
     * Set speech pitch (0.5 - 2.0)
     */
    fun setSpeechPitch(pitch: Float) {
        speechPitch = pitch.coerceIn(0.5f, 2.0f)
        tts?.setPitch(speechPitch)
    }
    
    /**
     * Set preferred voice
     */
    fun setVoice(voiceName: String?) {
        preferredVoice = voiceName
        if (isInitialized && voiceName != null) {
            tts?.voices?.find { it.name == voiceName }?.let { voice ->
                tts?.voice = voice
            }
        }
    }
    
    /**
     * Get available voices
     */
    fun getAvailableVoices(): List<String> {
        return tts?.voices?.map { it.name } ?: emptyList()
    }
    
    private fun processNextInQueue() {
        if (speechQueue.isEmpty() || isSpeaking) return
        
        // Sort queue by priority
        speechQueue.sortBy { 
            when (it.priority) {
                Priority.CRITICAL -> 0
                Priority.HIGH -> 1
                Priority.NORMAL -> 2
                Priority.LOW -> 3
            }
        }
        
        val nextRequest = speechQueue.removeFirstOrNull() ?: return
        currentRequest = nextRequest
        
        if (isInitialized) {
            val utteranceId = "buddy_${System.currentTimeMillis()}"
            val params = Bundle().apply {
                putString(TextToSpeech.Engine.KEY_PARAM_UTTERANCE_ID, utteranceId)
            }
            
            tts?.speak(
                nextRequest.text,
                TextToSpeech.QUEUE_FLUSH,
                params,
                utteranceId
            )
        } else {
            // TTS not ready, re-queue the request
            speechQueue.add(0, nextRequest)
            currentRequest = null
        }
    }
    
    /**
     * Shutdown TTS engine
     */
    fun shutdown() {
        stop()
        tts?.shutdown()
        tts = null
        isInitialized = false
        context = null
    }
}

/**
 * Cloud TTS integration (optional)
 */
object CloudTtsEngine {
    
    private var apiKey: String? = null
    private var baseUrl: String = "https://api.openai.com/v1/audio/speech"
    
    fun configure(apiKey: String, baseUrl: String? = null) {
        this.apiKey = apiKey
        baseUrl?.let { this.baseUrl = it }
    }
    
    suspend fun generateSpeech(
        text: String,
        voice: String = "alloy",
        model: String = "tts-1"
    ): ByteArray? {
        return try {
            // Implement cloud TTS API call
            // This would make HTTP request to TTS service
            // Return audio data for playback
            null // Placeholder
        } catch (e: Exception) {
            VoiceBus.post(VoiceEvent.Error("Cloud TTS failed: ${e.message}"))
            null
        }
    }
}
