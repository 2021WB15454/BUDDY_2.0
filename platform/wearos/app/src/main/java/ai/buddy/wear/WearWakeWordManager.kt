package ai.buddy.wear

import android.content.Context
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.os.PowerManager
import androidx.wear.ambient.AmbientModeSupport
import kotlinx.coroutines.*
import java.util.concurrent.atomic.AtomicBoolean

/**
 * BUDDY Wake Word Manager for Wear OS
 * 
 * Optimized wake word detection for Android smartwatches.
 * Handles ambient mode, battery conservation, and wrist gestures.
 */
class WearWakeWordManager private constructor() {
    
    companion object {
        @Volatile
        private var INSTANCE: WearWakeWordManager? = null
        
        fun getInstance(): WearWakeWordManager {
            return INSTANCE ?: synchronized(this) {
                INSTANCE ?: WearWakeWordManager().also { INSTANCE = it }
            }
        }
        
        private const val SAMPLE_RATE = 16000
        private const val CHANNEL_CONFIG = AudioFormat.CHANNEL_IN_MONO
        private const val AUDIO_FORMAT = AudioFormat.ENCODING_PCM_16BIT
        private const val BUFFER_SIZE = 1600 // 100ms at 16kHz
        
        // Wear OS specific settings
        private const val MAX_LISTENING_DURATION = 30000L // 30 seconds
        private const val COOLDOWN_PERIOD = 5000L // 5 seconds
        private const val BATTERY_THRESHOLD = 20 // 20%
    }
    
    private var audioRecord: AudioRecord? = null
    private var isListening = AtomicBoolean(false)
    private var isConfigured = false
    
    private val listeningScope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private var listeningJob: Job? = null
    
    private var lastTriggerTime = 0L
    private var lastBatteryCheck = 0L
    
    // Wear OS specific components
    private var powerManager: PowerManager? = null
    private var ambientModeSupport: AmbientModeSupport? = null
    private var isInAmbientMode = false
    
    // Simple keyword detection buffer
    private val audioBuffer = FloatArray(BUFFER_SIZE * 4) // 4 buffer cycles
    private var bufferIndex = 0
    
    fun configure(context: Context) {
        if (isConfigured) return
        
        try {
            powerManager = context.getSystemService(Context.POWER_SERVICE) as PowerManager
            
            val minBufferSize = AudioRecord.getMinBufferSize(
                SAMPLE_RATE,
                CHANNEL_CONFIG,
                AUDIO_FORMAT
            )
            
            audioRecord = AudioRecord(
                MediaRecorder.AudioSource.MIC,
                SAMPLE_RATE,
                CHANNEL_CONFIG,
                AUDIO_FORMAT,
                maxOf(BUFFER_SIZE * 2, minBufferSize)
            )
            
            isConfigured = true
            WearVoiceBus.getInstance().post(WearVoiceBus.WearVoiceEvent.WakeWordConfigured)
            
        } catch (e: SecurityException) {
            WearVoiceBus.getInstance().post(
                WearVoiceBus.WearVoiceEvent.Error("Microphone permission required")
            )
        } catch (e: Exception) {
            WearVoiceBus.getInstance().post(
                WearVoiceBus.WearVoiceEvent.Error("Wake word configuration failed: ${e.message}")
            )
        }
    }
    
    fun startListening(context: Context) {
        if (!isConfigured || isListening.get()) return
        
        // Check cooldown period
        val currentTime = System.currentTimeMillis()
        if (currentTime - lastTriggerTime < COOLDOWN_PERIOD) {
            return
        }
        
        // Check battery level
        if (!checkBatteryLevel(context)) {
            WearVoiceBus.getInstance().post(
                WearVoiceBus.WearVoiceEvent.Error("Low battery - wake word disabled")
            )
            return
        }
        
        // Don't start in ambient mode unless explicitly allowed
        if (isInAmbientMode && !shouldListenInAmbientMode()) {
            return
        }
        
        try {
            audioRecord?.startRecording()
            isListening.set(true)
            
            listeningJob = listeningScope.launch {
                processAudioStream()
            }
            
            // Auto-stop after max duration
            listeningScope.launch {
                delay(MAX_LISTENING_DURATION)
                stopListening()
            }
            
            WearVoiceBus.getInstance().post(WearVoiceBus.WearVoiceEvent.WakeWordStarted)
            
        } catch (e: Exception) {
            WearVoiceBus.getInstance().post(
                WearVoiceBus.WearVoiceEvent.Error("Failed to start wake word detection: ${e.message}")
            )
        }
    }
    
    fun stopListening() {
        if (!isListening.get()) return
        
        isListening.set(false)
        listeningJob?.cancel()
        
        try {
            audioRecord?.stop()
        } catch (e: Exception) {
            // Ignore stop errors
        }
        
        WearVoiceBus.getInstance().post(WearVoiceBus.WearVoiceEvent.WakeWordStopped)
    }
    
    fun triggerManualWakeWord() {
        lastTriggerTime = System.currentTimeMillis()
        
        // Provide haptic feedback
        // Note: Haptic feedback would be implemented with Vibrator service
        
        WearVoiceBus.getInstance().post(
            WearVoiceBus.WearVoiceEvent.WakeWordDetected("manual")
        )
    }
    
    fun handleWristGesture() {
        // Handle wrist twist/raise gesture as wake word trigger
        if (!isListening.get()) {
            triggerManualWakeWord()
        }
    }
    
    fun setAmbientMode(isAmbient: Boolean) {
        isInAmbientMode = isAmbient
        
        if (isAmbient && isListening.get()) {
            // Stop listening in ambient mode to save battery
            stopListening()
        }
    }
    
    private suspend fun processAudioStream() {
        val audioData = ShortArray(BUFFER_SIZE)
        
        while (isListening.get() && !currentCoroutineContext().job.isCancelled) {
            try {
                val bytesRead = audioRecord?.read(audioData, 0, BUFFER_SIZE) ?: 0
                
                if (bytesRead > 0) {
                    processAudioBuffer(audioData, bytesRead)
                }
                
                // Small delay to prevent excessive CPU usage
                delay(10)
                
            } catch (e: Exception) {
                if (isListening.get()) {
                    WearVoiceBus.getInstance().post(
                        WearVoiceBus.WearVoiceEvent.Error("Audio processing error: ${e.message}")
                    )
                }
                break
            }
        }
    }
    
    private fun processAudioBuffer(audioData: ShortArray, length: Int) {
        // Convert to float and calculate energy
        val energy = audioData.take(length)
            .map { it.toFloat() / Short.MAX_VALUE }
            .map { it * it }
            .average()
            .toFloat()
        
        // Add to circular buffer
        for (i in 0 until length) {
            audioBuffer[bufferIndex] = audioData[i].toFloat() / Short.MAX_VALUE
            bufferIndex = (bufferIndex + 1) % audioBuffer.size
        }
        
        // Simple voice activity detection
        if (energy > 0.01f) { // Threshold for voice activity
            detectSimpleKeyword(energy)
        }
    }
    
    private fun detectSimpleKeyword(energy: Float) {
        // Simplified keyword detection for Wear OS
        // In production, this would use a lightweight keyword model
        
        if (energy > 0.02f) { // Voice detected with sufficient energy
            handlePotentialKeyword()
        }
    }
    
    private fun handlePotentialKeyword() {
        lastTriggerTime = System.currentTimeMillis()
        
        WearVoiceBus.getInstance().post(
            WearVoiceBus.WearVoiceEvent.WakeWordDetected("hey_buddy")
        )
        
        // Auto-stop listening after detection
        stopListening()
    }
    
    private fun checkBatteryLevel(context: Context): Boolean {
        val currentTime = System.currentTimeMillis()
        
        // Check battery level every 30 seconds
        if (currentTime - lastBatteryCheck < 30000) {
            return true // Assume OK if recently checked
        }
        
        lastBatteryCheck = currentTime
        
        val batteryManager = context.getSystemService(Context.BATTERY_SERVICE) as android.os.BatteryManager
        val batteryLevel = batteryManager.getIntProperty(android.os.BatteryManager.BATTERY_PROPERTY_CAPACITY)
        
        return batteryLevel > BATTERY_THRESHOLD
    }
    
    private fun shouldListenInAmbientMode(): Boolean {
        // Only listen in ambient mode if battery is high
        return false // Conservative approach for battery life
    }
    
    fun cleanup() {
        stopListening()
        listeningJob?.cancel()
        audioRecord?.release()
        audioRecord = null
        isConfigured = false
    }
}

/**
 * Extension for Wear OS specific optimizations
 */
class WearWakeWordOptimizer {
    
    companion object {
        fun optimizeForWearOS(manager: WearWakeWordManager, context: Context) {
            // Register for ambient mode changes
            // Register for wrist gesture detection
            // Setup battery optimization
        }
        
        fun handleScreenState(isScreenOn: Boolean, manager: WearWakeWordManager) {
            if (!isScreenOn) {
                // Screen off - consider stopping wake word detection
                manager.stopListening()
            }
        }
        
        fun handlePowerSaveMode(isPowerSaveMode: Boolean, manager: WearWakeWordManager) {
            if (isPowerSaveMode) {
                manager.stopListening()
            }
        }
    }
}
