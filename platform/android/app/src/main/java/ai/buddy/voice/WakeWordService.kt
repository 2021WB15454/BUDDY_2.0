package ai.buddy.voice

import android.app.*
import android.content.*
import android.media.*
import android.os.*
import androidx.core.app.NotificationCompat
import ai.picovoice.porcupine.*
import kotlinx.coroutines.*
import java.util.*

/**
 * BUDDY Wake Word Service
 * 
 * Continuously listens for "Hey Buddy" wake word using Porcupine.
 * Runs as foreground service for reliable background operation.
 * 
 * Features:
 * - Low power wake word detection
 * - Configurable sensitivity
 * - Audio focus management
 * - Battery optimization
 * - Wear OS compatibility
 */
class WakeWordService : Service(), PorcupineManagerCallback {
    
    companion object {
        const val NOTIFICATION_ID = 1001
        const val CHANNEL_ID = "buddy_voice_channel"
        const val ACTION_START = "ai.buddy.voice.START_WAKE_DETECTION"
        const val ACTION_STOP = "ai.buddy.voice.STOP_WAKE_DETECTION"
        const val ACTION_SET_SENSITIVITY = "ai.buddy.voice.SET_SENSITIVITY"
        const val EXTRA_SENSITIVITY = "sensitivity"
        
        private const val WAKE_WORD_KEYWORD = "hey_buddy"
        private const val DEFAULT_SENSITIVITY = 0.6f
    }
    
    private var porcupineManager: PorcupineManager? = null
    private lateinit var audioManager: AudioManager
    private var sensitivity = DEFAULT_SENSITIVITY
    private var isListening = false
    private val scope = CoroutineScope(Dispatchers.Default + SupervisorJob())
    
    override fun onCreate() {
        super.onCreate()
        audioManager = getSystemService(Context.AUDIO_SERVICE) as AudioManager
        createNotificationChannel()
        VoiceBus.initialize(this)
    }
    
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_START -> startWakeDetection()
            ACTION_STOP -> stopWakeDetection()
            ACTION_SET_SENSITIVITY -> {
                sensitivity = intent.getFloatExtra(EXTRA_SENSITIVITY, DEFAULT_SENSITIVITY)
                if (isListening) {
                    restartWakeDetection()
                }
            }
        }
        return START_STICKY // Restart if killed
    }
    
    override fun onDestroy() {
        stopWakeDetection()
        scope.cancel()
        super.onDestroy()
    }
    
    override fun onBind(intent: Intent?): IBinder? = null
    
    private fun startWakeDetection() {
        if (isListening) return
        
        try {
            // Start foreground service
            startForeground(NOTIFICATION_ID, createNotification("Listening for 'Hey Buddy'"))
            
            // Initialize Porcupine with custom keyword
            val keywordPath = getKeywordPath()
            val accessKey = getAccessKey()
            
            porcupineManager = PorcupineManager.Builder()
                .setAccessKey(accessKey)
                .setKeywordPath(keywordPath)
                .setSensitivity(sensitivity)
                .build(this)
            
            porcupineManager?.start()
            isListening = true
            
            VoiceBus.post(VoiceEvent.WakeWordListening())
            updateNotification("🎤 Listening for 'Hey Buddy'")
            
        } catch (e: Exception) {
            VoiceBus.post(VoiceEvent.Error("Wake word start failed: ${e.message}"))
            stopSelf()
        }
    }
    
    private fun stopWakeDetection() {
        if (!isListening) return
        
        porcupineManager?.stop()
        porcupineManager?.delete()
        porcupineManager = null
        isListening = false
        
        VoiceBus.post(VoiceEvent.WakeWordStopped())
        stopForeground(true)
    }
    
    private fun restartWakeDetection() {
        stopWakeDetection()
        scope.launch {
            delay(100) // Brief pause
            startWakeDetection()
        }
    }
    
    override fun onDetection(keywordIndex: Int) {
        scope.launch {
            try {
                // Wake word detected!
                VoiceBus.post(VoiceEvent.WakeWordDetected(keywordIndex, confidence = 0.8f))
                
                updateNotification("🔥 Wake word detected!")
                
                // Brief confirmation feedback
                TtsEngine.speakShort(this@WakeWordService, "Yes?")
                
                // Start STT session
                delay(500) // Wait for TTS to start
                VoskStt.startSession(this@WakeWordService)
                
            } catch (e: Exception) {
                VoiceBus.post(VoiceEvent.Error("Wake detection handling failed: ${e.message}"))
            }
        }
    }
    
    private fun getKeywordPath(): String {
        // Copy keyword file from assets to files directory
        val fileName = "$WAKE_WORD_KEYWORD.ppn"
        val targetFile = java.io.File(filesDir, fileName)
        
        if (!targetFile.exists()) {
            assets.open("keywords/$fileName").use { input ->
                targetFile.outputStream().use { output ->
                    input.copyTo(output)
                }
            }
        }
        
        return targetFile.absolutePath
    }
    
    private fun getAccessKey(): String {
        // Get Picovoice access key from BuildConfig or assets
        return try {
            // First try BuildConfig
            val buildConfigClass = Class.forName("${packageName}.BuildConfig")
            val field = buildConfigClass.getDeclaredField("PV_ACCESS_KEY")
            field.get(null) as String
        } catch (e: Exception) {
            // Fallback to assets
            assets.open("porcupine_access_key.txt").bufferedReader().use { it.readText().trim() }
        }
    }
    
    private fun createNotificationChannel() {
        val channel = NotificationChannel(
            CHANNEL_ID,
            "BUDDY Voice Assistant",
            NotificationManager.IMPORTANCE_LOW
        ).apply {
            description = "BUDDY voice wake word detection"
            setSound(null, null)
            enableVibration(false)
        }
        
        val manager = getSystemService(NotificationManager::class.java)
        manager.createNotificationChannel(channel)
    }
    
    private fun createNotification(text: String): Notification {
        val stopIntent = Intent(this, WakeWordService::class.java).apply {
            action = ACTION_STOP
        }
        val stopPendingIntent = PendingIntent.getService(
            this, 0, stopIntent, PendingIntent.FLAG_IMMUTABLE
        )
        
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("BUDDY Voice Assistant")
            .setContentText(text)
            .setSmallIcon(android.R.drawable.ic_btn_speak_now)
            .setOngoing(true)
            .setSilent(true)
            .addAction(
                android.R.drawable.ic_media_pause,
                "Stop",
                stopPendingIntent
            )
            .build()
    }
    
    private fun updateNotification(text: String) {
        val notification = createNotification(text)
        val manager = getSystemService(NotificationManager::class.java)
        manager.notify(NOTIFICATION_ID, notification)
    }
}

/**
 * Helper class to start/stop wake word service
 */
object WakeWordManager {
    
    fun start(context: Context, sensitivity: Float = 0.6f) {
        val intent = Intent(context, WakeWordService::class.java).apply {
            action = WakeWordService.ACTION_START
            putExtra(WakeWordService.EXTRA_SENSITIVITY, sensitivity)
        }
        context.startForegroundService(intent)
    }
    
    fun stop(context: Context) {
        val intent = Intent(context, WakeWordService::class.java).apply {
            action = WakeWordService.ACTION_STOP
        }
        context.startService(intent)
    }
    
    fun setSensitivity(context: Context, sensitivity: Float) {
        val intent = Intent(context, WakeWordService::class.java).apply {
            action = WakeWordService.ACTION_SET_SENSITIVITY
            putExtra(WakeWordService.EXTRA_SENSITIVITY, sensitivity)
        }
        context.startService(intent)
    }
    
    fun isRunning(context: Context): Boolean {
        val manager = context.getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager
        @Suppress("DEPRECATION")
        return manager.getRunningServices(Integer.MAX_VALUE)
            .any { it.service.className == WakeWordService::class.java.name }
    }
}
