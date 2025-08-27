package ai.buddy.wear

import android.content.Context
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import android.os.Vibrator
import android.os.VibrationEffect
import android.os.Build
import kotlinx.coroutines.*
import java.util.*
import java.util.concurrent.ConcurrentLinkedQueue

/**
 * BUDDY Text-to-Speech Engine for Wear OS
 * 
 * Optimized TTS for Android smartwatches with haptic feedback.
 * Handles short responses and battery-efficient speech output.
 */
class WearTtsEngine private constructor() : TextToSpeech.OnInitListener {
    
    companion object {
        @Volatile
        private var INSTANCE: WearTtsEngine? = null
        
        fun getInstance(): WearTtsEngine {
            return INSTANCE ?: synchronized(this) {
                INSTANCE ?: WearTtsEngine().also { INSTANCE = it }
            }
        }
        
        private const val MAX_SPEECH_LENGTH = 80 // Character limit for wear
        private const val SPEECH_RATE = 1.1f // Slightly faster for wear
        private const val SPEECH_PITCH = 1.0f
    }
    
    private var tts: TextToSpeech? = null
    private var vibrator: Vibrator? = null
    private var isInitialized = false
    private var isSpeaking = false
    
    private val speechQueue = ConcurrentLinkedQueue<WearSpeechRequest>()
    private val ttsScope = CoroutineScope(Dispatchers.Main + SupervisorJob())
    
    data class WearSpeechRequest(
        val text: String,
        val priority: Priority,
        val useHaptic: Boolean,
        val shortForm: Boolean,
        val onComplete: (() -> Unit)? = null
    ) {
        enum class Priority(val value: Int) {
            LOW(3),
            NORMAL(2),
            HIGH(1),
            URGENT(0)
        }
    }
    
    fun configure(context: Context) {
        tts = TextToSpeech(context, this)
        vibrator = context.getSystemService(Context.VIBRATOR_SERVICE) as Vibrator
    }
    
    override fun onInit(status: Int) {
        if (status == TextToSpeech.SUCCESS) {
            tts?.let { ttsEngine ->
                val result = ttsEngine.setLanguage(Locale.getDefault())
                
                if (result == TextToSpeech.LANG_MISSING_DATA || result == TextToSpeech.LANG_NOT_SUPPORTED) {
                    // Fallback to English
                    ttsEngine.setLanguage(Locale.ENGLISH)
                }
                
                ttsEngine.setSpeechRate(SPEECH_RATE)
                ttsEngine.setPitch(SPEECH_PITCH)
                
                // Set up utterance progress listener
                ttsEngine.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
                    override fun onStart(utteranceId: String?) {
                        isSpeaking = true
                        WearVoiceBus.getInstance().post(
                            WearVoiceBus.WearVoiceEvent.TtsStarted(utteranceId ?: "")
                        )
                    }
                    
                    override fun onDone(utteranceId: String?) {
                        isSpeaking = false
                        WearVoiceBus.getInstance().post(
                            WearVoiceBus.WearVoiceEvent.TtsFinished(utteranceId ?: "")
                        )
                        processQueue()
                    }
                    
                    override fun onError(utteranceId: String?) {
                        isSpeaking = false
                        WearVoiceBus.getInstance().post(
                            WearVoiceBus.WearVoiceEvent.TtsError("TTS error for utterance: $utteranceId")
                        )
                        processQueue()
                    }
                })
                
                isInitialized = true
                WearVoiceBus.getInstance().post(WearVoiceBus.WearVoiceEvent.TtsConfigured)
            }
        } else {
            WearVoiceBus.getInstance().post(
                WearVoiceBus.WearVoiceEvent.Error("TTS initialization failed")
            )
        }
    }
    
    fun speak(text: String, useHaptic: Boolean = true) {
        speakShort(text, WearSpeechRequest.Priority.NORMAL, useHaptic)
    }
    
    fun speakShort(
        text: String,
        priority: WearSpeechRequest.Priority = WearSpeechRequest.Priority.NORMAL,
        useHaptic: Boolean = true,
        onComplete: (() -> Unit)? = null
    ) {
        val shortText = truncateForWear(text)
        
        val request = WearSpeechRequest(
            text = shortText,
            priority = priority,
            useHaptic = useHaptic,
            shortForm = true,
            onComplete = onComplete
        )
        
        addToQueue(request)
    }
    
    fun speakUrgent(text: String) {
        // Clear queue for urgent messages
        stop()
        speechQueue.clear()
        
        val request = WearSpeechRequest(
            text = truncateForWear(text),
            priority = WearSpeechRequest.Priority.URGENT,
            useHaptic = true,
            shortForm = true
        )
        
        addToQueue(request)
    }
    
    fun speakTime() {
        val currentTime = Calendar.getInstance()
        val hour = currentTime.get(Calendar.HOUR_OF_DAY)
        val minute = currentTime.get(Calendar.MINUTE)
        
        val timeString = if (minute == 0) {
            "$hour o'clock"
        } else {
            "$hour $minute"
        }
        
        speakShort("It's $timeString", useHaptic = false)
    }
    
    fun speakStatus(status: String) {
        val shortStatus = truncateForWear(status)
        speakShort(shortStatus, WearSpeechRequest.Priority.HIGH, useHaptic = true)
    }
    
    fun stop() {
        tts?.stop()
        isSpeaking = false
    }
    
    fun provideFeedback(type: FeedbackType) {
        when (type) {
            FeedbackType.SUCCESS -> {
                provideHapticFeedback(HapticPattern.SUCCESS)
                speakShort("Done", useHaptic = false)
            }
            FeedbackType.ERROR -> {
                provideHapticFeedback(HapticPattern.ERROR)
                speakShort("Error", useHaptic = false)
            }
            FeedbackType.LISTENING -> {
                provideHapticFeedback(HapticPattern.CLICK)
                // No speech for listening state
            }
            FeedbackType.PROCESSING -> {
                provideHapticFeedback(HapticPattern.PROCESSING)
                // Brief processing indicator
            }
        }
    }
    
    enum class FeedbackType {
        SUCCESS,
        ERROR,
        LISTENING,
        PROCESSING
    }
    
    private enum class HapticPattern(val pattern: LongArray) {
        CLICK(longArrayOf(0, 50)),
        SUCCESS(longArrayOf(0, 100, 50, 100)),
        ERROR(longArrayOf(0, 200, 100, 200)),
        PROCESSING(longArrayOf(0, 50, 50, 50))
    }
    
    private fun addToQueue(request: WearSpeechRequest) {
        // Insert based on priority
        if (request.priority == WearSpeechRequest.Priority.URGENT) {
            // For urgent, we need to restructure the queue
            val tempList = mutableListOf<WearSpeechRequest>()
            while (speechQueue.isNotEmpty()) {
                tempList.add(speechQueue.poll())
            }
            speechQueue.offer(request)
            tempList.forEach { speechQueue.offer(it) }
        } else {
            speechQueue.offer(request)
        }
        
        if (!isSpeaking) {
            processQueue()
        }
    }
    
    private fun processQueue() {
        if (!isInitialized || isSpeaking || speechQueue.isEmpty()) return
        
        val nextRequest = speechQueue.poll() ?: return
        
        // Provide haptic feedback if requested
        if (nextRequest.useHaptic) {
            provideHapticFeedback(HapticPattern.CLICK)
        }
        
        val params = Bundle().apply {
            putString(TextToSpeech.Engine.KEY_PARAM_UTTERANCE_ID, nextRequest.text)
        }
        
        val result = tts?.speak(nextRequest.text, TextToSpeech.QUEUE_FLUSH, params, nextRequest.text)
        
        if (result != TextToSpeech.SUCCESS) {
            WearVoiceBus.getInstance().post(
                WearVoiceBus.WearVoiceEvent.TtsError("Failed to speak: ${nextRequest.text}")
            )
            // Try next in queue
            ttsScope.launch {
                delay(100)
                processQueue()
            }
        }
    }
    
    private fun truncateForWear(text: String): String {
        val cleaned = text.trim()
        
        if (cleaned.length <= MAX_SPEECH_LENGTH) {
            return cleaned
        }
        
        // Truncate and add indicator
        val truncated = cleaned.substring(0, MAX_SPEECH_LENGTH - 3)
        return "$truncated..."
    }
    
    private fun provideHapticFeedback(pattern: HapticPattern) {
        vibrator?.let { vib ->
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                val effect = VibrationEffect.createWaveform(pattern.pattern, -1)
                vib.vibrate(effect)
            } else {
                @Suppress("DEPRECATION")
                vib.vibrate(pattern.pattern, -1)
            }
        }
    }
    
    fun speakWearOptimizedResponse(response: String) {
        val optimized = optimizeForWear(response)
        speakShort(optimized, WearSpeechRequest.Priority.NORMAL, useHaptic = true)
    }
    
    private fun optimizeForWear(text: String): String {
        // Common response optimizations for wear
        val replacements = mapOf(
            "I can help you with" to "I can help with",
            "Let me check that for you" to "Checking",
            "Here's what I found" to "Found",
            "I'm sorry, but" to "Sorry,",
            "Unfortunately" to "Sorry,",
            "Please wait while I" to "Processing",
            "According to" to "Per",
            "The current time is" to "It's",
            "Today's date is" to "Today is"
        )
        
        var optimized = text
        replacements.forEach { (long, short) ->
            optimized = optimized.replace(long, short, ignoreCase = true)
        }
        
        return truncateForWear(optimized)
    }
    
    fun getQuickResponses(): List<String> {
        return listOf(
            "OK",
            "Got it",
            "Done",
            "Yes",
            "No",
            "Maybe",
            "Later",
            "Help"
        )
    }
    
    fun speakQuickResponse(response: String) {
        speakShort(response, WearSpeechRequest.Priority.HIGH, useHaptic = true)
    }
    
    fun getStatusForComplication(): String {
        return when {
            isSpeaking -> "Speaking"
            speechQueue.isNotEmpty() -> "Queued"
            else -> "Ready"
        }
    }
    
    fun hasQueuedSpeech(): Boolean = speechQueue.isNotEmpty()
    fun getQueueCount(): Int = speechQueue.size
    
    fun cleanup() {
        stop()
        tts?.shutdown()
        tts = null
        isInitialized = false
    }
}
