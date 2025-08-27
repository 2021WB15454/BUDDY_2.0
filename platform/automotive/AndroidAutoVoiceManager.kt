package ai.buddy.automotive

import android.car.Car
import android.car.CarAppFocusManager
import android.car.media.CarAudioManager
import android.content.Context
import android.media.AudioAttributes
import android.media.AudioFocusRequest
import android.media.AudioManager
import android.os.Build
import kotlinx.coroutines.*

/**
 * BUDDY Voice Manager for Android Auto
 * 
 * Handles voice interactions optimized for automotive environment.
 * Integrates with Android Auto APIs and car audio systems.
 */
class AndroidAutoVoiceManager private constructor() {
    
    companion object {
        @Volatile
        private var INSTANCE: AndroidAutoVoiceManager? = null
        
        fun getInstance(): AndroidAutoVoiceManager {
            return INSTANCE ?: synchronized(this) {
                INSTANCE ?: AndroidAutoVoiceManager().also { INSTANCE = it }
            }
        }
        
        private const val VOICE_SESSION_TIMEOUT = 60000L // 1 minute for car safety
    }
    
    private var car: Car? = null
    private var carAudioManager: CarAudioManager? = null
    private var carAppFocusManager: CarAppFocusManager? = null
    private var audioManager: AudioManager? = null
    
    private var isConnectedToCar = false
    private var hasAudioFocus = false
    private var isDriving = false
    
    private val carScope = CoroutineScope(Dispatchers.Main + SupervisorJob())
    
    // Car-specific voice configuration
    private val carAudioAttributes = AudioAttributes.Builder()
        .setUsage(AudioAttributes.USAGE_ASSISTANCE_NAVIGATION_GUIDANCE)
        .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
        .build()
    
    fun connectToCar(context: Context) {
        if (isConnectedToCar) return
        
        try {
            car = Car.createCar(context, object : Car.CarServiceLifecycleListener {
                override fun onLifecycleChanged(car: Car, ready: Boolean) {
                    if (ready) {
                        initializeCarServices(car)
                    } else {
                        disconnectFromCar()
                    }
                }
            })
            
            car?.connect()
            
        } catch (e: Exception) {
            AutomotiveVoiceBus.getInstance().post(
                AutomotiveVoiceBus.AutomotiveVoiceEvent.Error(
                    "Failed to connect to car: ${e.message}"
                )
            )
        }
    }
    
    private fun initializeCarServices(car: Car) {
        try {
            carAudioManager = car.getCarManager(Car.AUDIO_SERVICE) as CarAudioManager
            carAppFocusManager = car.getCarManager(Car.APP_FOCUS_SERVICE) as CarAppFocusManager
            
            isConnectedToCar = true
            
            AutomotiveVoiceBus.getInstance().post(
                AutomotiveVoiceBus.AutomotiveVoiceEvent.CarConnected
            )
            
            // Request app focus for voice assistance
            requestAppFocus()
            
        } catch (e: Exception) {
            AutomotiveVoiceBus.getInstance().post(
                AutomotiveVoiceBus.AutomotiveVoiceEvent.Error(
                    "Failed to initialize car services: ${e.message}"
                )
            )
        }
    }
    
    fun startCarVoiceSession(context: Context) {
        if (!isConnectedToCar) {
            AutomotiveVoiceBus.getInstance().post(
                AutomotiveVoiceBus.AutomotiveVoiceEvent.Error("Not connected to car")
            )
            return
        }
        
        // Request audio focus for voice interaction
        requestAudioFocus(context)
        
        if (hasAudioFocus) {
            // Start car-optimized voice flow
            AutomotiveVoiceBus.getInstance().post(
                AutomotiveVoiceBus.AutomotiveVoiceEvent.VoiceSessionStarted
            )
            
            // Use car-specific wake word detection
            CarWakeWordManager.getInstance().startListening(context)
            
            // Auto-timeout for safety
            carScope.launch {
                delay(VOICE_SESSION_TIMEOUT)
                endCarVoiceSession()
            }
        }
    }
    
    fun endCarVoiceSession() {
        CarWakeWordManager.getInstance().stopListening()
        CarTtsEngine.getInstance().stop()
        
        releaseAudioFocus()
        
        AutomotiveVoiceBus.getInstance().post(
            AutomotiveVoiceBus.AutomotiveVoiceEvent.VoiceSessionEnded
        )
    }
    
    fun handleCarButton(buttonType: CarButtonType) {
        when (buttonType) {
            CarButtonType.VOICE_COMMAND -> {
                triggerVoiceCommand()
            }
            CarButtonType.MEDIA_NEXT -> {
                // Handle media control through voice
                processCarCommand("next track")
            }
            CarButtonType.MEDIA_PREVIOUS -> {
                processCarCommand("previous track")
            }
            CarButtonType.PHONE -> {
                processCarCommand("make call")
            }
        }
    }
    
    enum class CarButtonType {
        VOICE_COMMAND,
        MEDIA_NEXT,
        MEDIA_PREVIOUS,
        PHONE
    }
    
    private fun triggerVoiceCommand() {
        AutomotiveVoiceBus.getInstance().post(
            AutomotiveVoiceBus.AutomotiveVoiceEvent.CarButtonPressed("voice")
        )
        
        CarWakeWordManager.getInstance().triggerManualWakeWord()
    }
    
    private fun processCarCommand(command: String) {
        AutomotiveVoiceBus.getInstance().post(
            AutomotiveVoiceBus.AutomotiveVoiceEvent.CarCommandReceived(command)
        )
        
        // Process with automotive-optimized bridge
        CarBuddyBridge.getInstance().processCarInput(command)
    }
    
    fun setDrivingState(isDriving: Boolean) {
        this.isDriving = isDriving
        
        if (isDriving) {
            // Enable hands-free mode
            AutomotiveVoiceBus.getInstance().post(
                AutomotiveVoiceBus.AutomotiveVoiceEvent.DrivingModeEnabled
            )
        } else {
            AutomotiveVoiceBus.getInstance().post(
                AutomotiveVoiceBus.AutomotiveVoiceEvent.DrivingModeDisabled
            )
        }
    }
    
    private fun requestAppFocus() {
        carAppFocusManager?.requestAppFocus(
            CarAppFocusManager.APP_FOCUS_TYPE_NAVIGATION,
            object : CarAppFocusManager.OnAppFocusChangedListener {
                override fun onAppFocusChanged(appType: Int, active: Boolean) {
                    // Handle app focus changes
                }
            }
        )
    }
    
    private fun requestAudioFocus(context: Context) {
        audioManager = context.getSystemService(Context.AUDIO_SERVICE) as AudioManager
        
        val focusRequest = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN_TRANSIENT_MAY_DUCK)
                .setAudioAttributes(carAudioAttributes)
                .setOnAudioFocusChangeListener({ focusChange ->
                    handleAudioFocusChange(focusChange)
                })
                .build()
        } else {
            null
        }
        
        val result = if (focusRequest != null && Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            audioManager?.requestAudioFocus(focusRequest)
        } else {
            @Suppress("DEPRECATION")
            audioManager?.requestAudioFocus(
                { focusChange -> handleAudioFocusChange(focusChange) },
                AudioManager.STREAM_MUSIC,
                AudioManager.AUDIOFOCUS_GAIN_TRANSIENT_MAY_DUCK
            )
        }
        
        hasAudioFocus = result == AudioManager.AUDIOFOCUS_REQUEST_GRANTED
    }
    
    private fun releaseAudioFocus() {
        if (hasAudioFocus) {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                // Would need to store the focus request to abandon it
                // audioManager?.abandonAudioFocusRequest(focusRequest)
            } else {
                @Suppress("DEPRECATION")
                audioManager?.abandonAudioFocus { }
            }
            hasAudioFocus = false
        }
    }
    
    private fun handleAudioFocusChange(focusChange: Int) {
        when (focusChange) {
            AudioManager.AUDIOFOCUS_GAIN -> {
                hasAudioFocus = true
                // Resume voice processing if needed
            }
            AudioManager.AUDIOFOCUS_LOSS,
            AudioManager.AUDIOFOCUS_LOSS_TRANSIENT -> {
                hasAudioFocus = false
                // Pause or stop voice processing
                endCarVoiceSession()
            }
            AudioManager.AUDIOFOCUS_LOSS_TRANSIENT_CAN_DUCK -> {
                // Lower volume but continue
            }
        }
    }
    
    fun disconnectFromCar() {
        if (isConnectedToCar) {
            endCarVoiceSession()
            releaseAudioFocus()
            
            car?.disconnect()
            car = null
            carAudioManager = null
            carAppFocusManager = null
            
            isConnectedToCar = false
            
            AutomotiveVoiceBus.getInstance().post(
                AutomotiveVoiceBus.AutomotiveVoiceEvent.CarDisconnected
            )
        }
    }
    
    fun getCarConnectionStatus(): CarConnectionStatus {
        return CarConnectionStatus(
            isConnected = isConnectedToCar,
            hasAudioFocus = hasAudioFocus,
            isDriving = isDriving
        )
    }
    
    data class CarConnectionStatus(
        val isConnected: Boolean,
        val hasAudioFocus: Boolean,
        val isDriving: Boolean
    )
}

/**
 * Car-specific Wake Word Manager
 */
class CarWakeWordManager private constructor() {
    
    companion object {
        @Volatile
        private var INSTANCE: CarWakeWordManager? = null
        
        fun getInstance(): CarWakeWordManager {
            return INSTANCE ?: synchronized(this) {
                INSTANCE ?: CarWakeWordManager().also { INSTANCE = it }
            }
        }
    }
    
    private var isListening = false
    
    fun startListening(context: Context) {
        if (isListening) return
        
        isListening = true
        
        // Use regular wake word manager with car-specific configuration
        val wakeWordManager = ai.buddy.voice.WakeWordService.getInstance()
        // Configure for car environment (higher threshold, noise cancellation)
        
        AutomotiveVoiceBus.getInstance().post(
            AutomotiveVoiceBus.AutomotiveVoiceEvent.WakeWordStarted
        )
    }
    
    fun stopListening() {
        if (!isListening) return
        
        isListening = false
        
        AutomotiveVoiceBus.getInstance().post(
            AutomotiveVoiceBus.AutomotiveVoiceEvent.WakeWordStopped
        )
    }
    
    fun triggerManualWakeWord() {
        AutomotiveVoiceBus.getInstance().post(
            AutomotiveVoiceBus.AutomotiveVoiceEvent.WakeWordDetected("manual_car")
        )
    }
}

/**
 * Car-specific TTS Engine
 */
class CarTtsEngine private constructor() {
    
    companion object {
        @Volatile
        private var INSTANCE: CarTtsEngine? = null
        
        fun getInstance(): CarTtsEngine {
            return INSTANCE ?: synchronized(this) {
                INSTANCE ?: CarTtsEngine().also { INSTANCE = it }
            }
        }
    }
    
    fun speakCarOptimized(text: String) {
        // Use regular TTS engine with car-specific optimizations
        val ttsEngine = ai.buddy.voice.TtsEngine.getInstance()
        
        // Optimize text for driving context
        val carOptimizedText = optimizeForCar(text)
        
        ttsEngine.speak(carOptimizedText, ai.buddy.voice.TtsEngine.Priority.HIGH)
    }
    
    private fun optimizeForCar(text: String): String {
        // Car-specific text optimizations
        val carReplacements = mapOf(
            "Please" to "",
            "Thank you" to "Thanks",
            "I'm going to" to "I'll",
            "You can" to "You can now",
            "Would you like" to "Want to"
        )
        
        var optimized = text
        carReplacements.forEach { (long, short) ->
            optimized = optimized.replace(long, short, ignoreCase = true)
        }
        
        return optimized.trim()
    }
    
    fun stop() {
        ai.buddy.voice.TtsEngine.getInstance().stop()
    }
}

/**
 * Car-specific Buddy Bridge
 */
class CarBuddyBridge private constructor() {
    
    companion object {
        @Volatile
        private var INSTANCE: CarBuddyBridge? = null
        
        fun getInstance(): CarBuddyBridge {
            return INSTANCE ?: synchronized(this) {
                INSTANCE ?: CarBuddyBridge().also { INSTANCE = it }
            }
        }
    }
    
    fun processCarInput(input: String) {
        // Use regular bridge with car-specific processing
        val bridge = ai.buddy.voice.BuddyBridge.getInstance()
        
        // Add car context to the input
        val carContextInput = "In car: $input"
        
        bridge.processVoiceInput(carContextInput, "car_session")
    }
}
