package ai.buddy.voice

import android.content.Context
import android.media.*
import kotlinx.coroutines.*
import org.vosk.Model
import org.vosk.Recognizer
import org.json.JSONObject
import java.io.File
import java.util.*

/**
 * BUDDY Vosk Speech-to-Text Engine
 * 
 * Provides real-time streaming speech recognition using Vosk.
 * Optimized for mobile devices with automatic silence detection.
 * 
 * Features:
 * - Streaming recognition with partial results
 * - Automatic session timeout on silence
 * - Multiple language model support
 * - Low latency audio pipeline
 * - Battery optimization
 */
object VoskStt {
    
    private const val SAMPLE_RATE = 16000
    private const val CHANNEL_CONFIG = AudioFormat.CHANNEL_IN_MONO
    private const val AUDIO_FORMAT = AudioFormat.ENCODING_PCM_16BIT
    private const val SILENCE_TIMEOUT_MS = 4000L
    private const val MAX_SESSION_DURATION_MS = 30000L
    
    private var model: Model? = null
    private var recognizer: Recognizer? = null
    private var audioRecord: AudioRecord? = null
    private var job: Job? = null
    private var sessionId: String? = null
    private var isActive = false
    private var lastSpeechTime = 0L
    
    /**
     * Start a new STT session
     */
    fun startSession(context: Context, language: String = "en-US"): Boolean {
        if (isActive) {
            stopSession()
        }
        
        try {
            sessionId = UUID.randomUUID().toString()
            
            // Initialize model and recognizer
            val modelPath = prepareModel(context, language)
            model = Model(modelPath)
            recognizer = Recognizer(model, SAMPLE_RATE.toFloat())
            
            // Initialize audio recording
            val bufferSize = AudioRecord.getMinBufferSize(SAMPLE_RATE, CHANNEL_CONFIG, AUDIO_FORMAT)
            audioRecord = AudioRecord(
                MediaRecorder.AudioSource.VOICE_RECOGNITION,
                SAMPLE_RATE,
                CHANNEL_CONFIG,
                AUDIO_FORMAT,
                bufferSize * 2
            )
            
            if (audioRecord?.state != AudioRecord.STATE_INITIALIZED) {
                throw IllegalStateException("AudioRecord initialization failed")
            }
            
            // Start recording and processing
            audioRecord?.startRecording()
            isActive = true
            lastSpeechTime = System.currentTimeMillis()
            
            VoiceBus.post(VoiceEvent.SttStarted(sessionId!!))
            
            // Start processing loop
            job = CoroutineScope(Dispatchers.Default).launch {
                processAudioStream(context)
            }
            
            return true
            
        } catch (e: Exception) {
            VoiceBus.post(VoiceEvent.Error("STT start failed: ${e.message}"))
            cleanup()
            return false
        }
    }
    
    /**
     * Stop the current STT session
     */
    fun stopSession() {
        if (!isActive) return
        
        isActive = false
        job?.cancel()
        
        audioRecord?.let {
            if (it.recordingState == AudioRecord.RECORDSTATE_RECORDING) {
                it.stop()
            }
            it.release()
        }
        
        // Get final result before cleanup
        recognizer?.let { rec ->
            try {
                val finalResult = rec.finalResult
                parseFinalResult(finalResult)
            } catch (e: Exception) {
                // Ignore final result errors
            }
        }
        
        cleanup()
        
        sessionId?.let { id ->
            VoiceBus.post(VoiceEvent.SttStopped(id))
        }
        sessionId = null
    }
    
    /**
     * Check if STT is currently active
     */
    fun isActive(): Boolean = isActive
    
    /**
     * Get current session ID
     */
    fun getSessionId(): String? = sessionId
    
    private suspend fun processAudioStream(context: Context) {
        val buffer = ShortArray(1024)
        val sessionStartTime = System.currentTimeMillis()
        
        try {
            while (isActive) {
                // Check for session timeout
                val currentTime = System.currentTimeMillis()
                if (currentTime - sessionStartTime > MAX_SESSION_DURATION_MS) {
                    VoiceBus.post(VoiceEvent.SessionTimeout(sessionId!!))
                    break
                }
                
                // Check for silence timeout
                if (currentTime - lastSpeechTime > SILENCE_TIMEOUT_MS) {
                    VoiceBus.post(VoiceEvent.SilenceDetected(sessionId!!))
                    break
                }
                
                // Read audio data
                val bytesRead = audioRecord?.read(buffer, 0, buffer.size) ?: 0
                if (bytesRead > 0) {
                    // Convert to byte array for Vosk
                    val byteBuffer = ByteArray(bytesRead * 2)
                    for (i in 0 until bytesRead) {
                        val sample = buffer[i]
                        byteBuffer[i * 2] = (sample.toInt() and 0xFF).toByte()
                        byteBuffer[i * 2 + 1] = ((sample.toInt() shr 8) and 0xFF).toByte()
                    }
                    
                    // Process with Vosk
                    recognizer?.let { rec ->
                        if (rec.acceptWaveForm(byteBuffer, bytesRead * 2)) {
                            // Final result available
                            val result = rec.result
                            parseFinalResult(result)
                        } else {
                            // Partial result available
                            val partialResult = rec.partialResult
                            parsePartialResult(partialResult)
                        }
                    }
                } else {
                    delay(10) // Brief pause to prevent tight loop
                }
            }
        } catch (e: Exception) {
            VoiceBus.post(VoiceEvent.Error("STT processing error: ${e.message}"))
        } finally {
            stopSession()
        }
    }
    
    private fun parseFinalResult(jsonResult: String) {
        try {
            val json = JSONObject(jsonResult)
            val text = json.optString("text", "").trim()
            
            if (text.isNotEmpty()) {
                lastSpeechTime = System.currentTimeMillis()
                
                val confidence = json.optDouble("confidence", 0.8)
                VoiceBus.post(VoiceEvent.SttFinalResult(
                    sessionId = sessionId!!,
                    text = text,
                    confidence = confidence
                ))
                
                // Send to BUDDY brain
                BuddyBridge.processText(text, sessionId!!)
            }
        } catch (e: Exception) {
            VoiceBus.post(VoiceEvent.Error("STT result parsing error: ${e.message}"))
        }
    }
    
    private fun parsePartialResult(jsonResult: String) {
        try {
            val json = JSONObject(jsonResult)
            val partial = json.optString("partial", "").trim()
            
            if (partial.isNotEmpty()) {
                lastSpeechTime = System.currentTimeMillis()
                VoiceBus.post(VoiceEvent.SttPartialResult(
                    sessionId = sessionId!!,
                    text = partial
                ))
            }
        } catch (e: Exception) {
            // Ignore partial result parsing errors
        }
    }
    
    private fun prepareModel(context: Context, language: String): String {
        val modelDir = File(context.filesDir, "vosk-models/$language")
        
        if (!modelDir.exists()) {
            // Extract model from assets
            val assetPath = "models/$language"
            extractAssetFolder(context, assetPath, modelDir)
        }
        
        return modelDir.absolutePath
    }
    
    private fun extractAssetFolder(context: Context, assetPath: String, targetDir: File) {
        val assets = context.assets
        
        try {
            val files = assets.list(assetPath) ?: return
            targetDir.mkdirs()
            
            for (file in files) {
                val fullAssetPath = "$assetPath/$file"
                val targetFile = File(targetDir, file)
                
                if (assets.list(fullAssetPath)?.isNotEmpty() == true) {
                    // It's a directory
                    extractAssetFolder(context, fullAssetPath, targetFile)
                } else {
                    // It's a file
                    assets.open(fullAssetPath).use { input ->
                        targetFile.outputStream().use { output ->
                            input.copyTo(output)
                        }
                    }
                }
            }
        } catch (e: Exception) {
            throw RuntimeException("Failed to extract Vosk model: ${e.message}", e)
        }
    }
    
    private fun cleanup() {
        recognizer?.close()
        recognizer = null
        model?.close()
        model = null
        audioRecord = null
    }
}

/**
 * Audio level detection for voice activity
 */
object AudioLevelDetector {
    
    fun calculateRMS(audioData: ShortArray, length: Int): Double {
        var sum = 0.0
        for (i in 0 until length) {
            sum += audioData[i] * audioData[i]
        }
        return kotlin.math.sqrt(sum / length)
    }
    
    fun isSpeech(rms: Double, threshold: Double = 1000.0): Boolean {
        return rms > threshold
    }
}
