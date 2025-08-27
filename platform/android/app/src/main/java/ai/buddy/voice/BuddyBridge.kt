package ai.buddy.voice

import kotlinx.coroutines.*
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.util.concurrent.TimeoutException

/**
 * BUDDY Bridge - Voice to Brain Connector
 * 
 * Connects voice input to BUDDY's main intelligence backend.
 * Handles both network and offline fallback responses.
 * 
 * Features:
 * - REST API integration with BUDDY backend
 * - Offline fallback with local intent matching
 * - Timeout handling and retries
 * - Context preservation across requests
 * - Error recovery and graceful degradation
 */
object BuddyBridge {
    
    private var baseUrl = "http://localhost:8082"
    private var apiKey: String? = null
    private var timeout = 10000L // 10 seconds
    private var isOfflineMode = false
    private var retryCount = 3
    
    // Local intent patterns for offline fallback
    private val localIntents = mapOf(
        "greeting" to listOf("hello", "hi", "hey"),
        "time" to listOf("time", "what time", "clock"),
        "help" to listOf("help", "what can you do"),
        "goodbye" to listOf("bye", "goodbye", "see you")
    )
    
    private val localResponses = mapOf(
        "greeting" to "Hello! I'm BUDDY, your AI assistant.",
        "time" to "I'd need to check the time for you.",
        "help" to "I can help with emails, reminders, weather, and more!",
        "goodbye" to "Goodbye! Just say 'Hey Buddy' to chat again.",
        "unknown" to "I didn't quite understand that. Could you try again?"
    )
    
    /**
     * Configure the bridge
     */
    fun configure(
        baseUrl: String,
        apiKey: String? = null,
        timeout: Long = 10000L
    ) {
        this.baseUrl = baseUrl.trimEnd('/')
        this.apiKey = apiKey
        this.timeout = timeout
    }
    
    /**
     * Enable/disable offline mode
     */
    fun setOfflineMode(enabled: Boolean) {
        isOfflineMode = enabled
    }
    
    /**
     * Process text input and get BUDDY's response
     */
    suspend fun processText(text: String, sessionId: String? = null): BuddyResponse {
        return withContext(Dispatchers.IO) {
            try {
                if (isOfflineMode) {
                    processOffline(text)
                } else {
                    processOnline(text, sessionId) ?: processOffline(text)
                }
            } catch (e: Exception) {
                VoiceBus.post(VoiceEvent.Error("Bridge processing failed: ${e.message}"))
                processOffline(text)
            }
        }
    }
    
    /**
     * Process text through BUDDY's online backend
     */
    private suspend fun processOnline(text: String, sessionId: String?): BuddyResponse? {
        return try {
            val response = makeApiRequest(text, sessionId)
            
            // Post successful response event
            VoiceBus.post(VoiceEvent.BuddyResponse(
                text = response.text,
                intent = response.intent,
                sessionId = sessionId
            ))
            
            response
        } catch (e: TimeoutException) {
            VoiceBus.post(VoiceEvent.Error("BUDDY API timeout"))
            null
        } catch (e: Exception) {
            VoiceBus.post(VoiceEvent.Error("BUDDY API error: ${e.message}"))
            null
        }
    }
    
    /**
     * Process text using offline fallback
     */
    private fun processOffline(text: String): BuddyResponse {
        val intent = detectLocalIntent(text)
        val responseText = localResponses[intent] ?: localResponses["unknown"]!!
        
        val response = BuddyResponse(
            text = responseText,
            intent = intent,
            confidence = if (intent != "unknown") 0.7 else 0.3,
            isOffline = true
        )
        
        // Post offline response event
        VoiceBus.post(VoiceEvent.BuddyResponse(
            text = response.text,
            intent = response.intent,
            sessionId = null
        ))
        
        return response
    }
    
    /**
     * Make HTTP request to BUDDY backend
     */
    private suspend fun makeApiRequest(text: String, sessionId: String?): BuddyResponse {
        val url = URL("$baseUrl/chat/universal")
        val connection = url.openConnection() as HttpURLConnection
        
        return try {
            // Configure request
            connection.requestMethod = "POST"
            connection.setRequestProperty("Content-Type", "application/json")
            connection.setRequestProperty("Accept", "application/json")
            apiKey?.let { key ->
                connection.setRequestProperty("Authorization", "Bearer $key")
            }
            connection.connectTimeout = timeout.toInt()
            connection.readTimeout = timeout.toInt()
            connection.doOutput = true
            
            // Build request body
            val requestBody = JSONObject().apply {
                put("message", text)
                put("voice_session", true)
                sessionId?.let { put("session_id", it) }
                put("context", JSONObject().apply {
                    put("source", "voice")
                    put("timestamp", System.currentTimeMillis())
                })
            }
            
            // Send request
            connection.outputStream.use { os ->
                os.write(requestBody.toString().toByteArray())
            }
            
            // Read response
            val responseCode = connection.responseCode
            if (responseCode == 200) {
                val responseText = connection.inputStream.bufferedReader().use { it.readText() }
                parseApiResponse(responseText)
            } else {
                throw RuntimeException("API returned error code: $responseCode")
            }
            
        } finally {
            connection.disconnect()
        }
    }
    
    /**
     * Parse API response JSON
     */
    private fun parseApiResponse(jsonText: String): BuddyResponse {
        val json = JSONObject(jsonText)
        
        return BuddyResponse(
            text = json.optString("response", "I didn't get a response from BUDDY."),
            intent = json.optString("intent"),
            confidence = json.optDouble("confidence", 0.8),
            actions = parseActions(json.optJSONArray("actions")),
            metadata = parseMetadata(json.optJSONObject("metadata")),
            isOffline = false
        )
    }
    
    /**
     * Parse actions from API response
     */
    private fun parseActions(actionsJson: org.json.JSONArray?): List<BuddyAction> {
        if (actionsJson == null) return emptyList()
        
        val actions = mutableListOf<BuddyAction>()
        for (i in 0 until actionsJson.length()) {
            val actionJson = actionsJson.optJSONObject(i)
            if (actionJson != null) {
                actions.add(BuddyAction(
                    type = actionJson.optString("type", "unknown"),
                    payload = actionJson.optJSONObject("payload")?.toString() ?: "{}"
                ))
            }
        }
        return actions
    }
    
    /**
     * Parse metadata from API response
     */
    private fun parseMetadata(metadataJson: JSONObject?): Map<String, Any> {
        if (metadataJson == null) return emptyMap()
        
        val metadata = mutableMapOf<String, Any>()
        metadataJson.keys().forEach { key ->
            metadata[key] = metadataJson.get(key)
        }
        return metadata
    }
    
    /**
     * Detect intent from text using local patterns
     */
    private fun detectLocalIntent(text: String): String {
        val lowerText = text.lowercase()
        
        for ((intent, keywords) in localIntents) {
            if (keywords.any { keyword -> lowerText.contains(keyword) }) {
                return intent
            }
        }
        
        return "unknown"
    }
    
    /**
     * Test connection to BUDDY backend
     */
    suspend fun testConnection(): Boolean {
        return try {
            val url = URL("$baseUrl/health")
            val connection = url.openConnection() as HttpURLConnection
            connection.requestMethod = "GET"
            connection.connectTimeout = 5000
            connection.readTimeout = 5000
            
            val responseCode = connection.responseCode
            connection.disconnect()
            
            responseCode == 200
        } catch (e: Exception) {
            false
        }
    }
    
    /**
     * Get backend status information
     */
    suspend fun getBackendStatus(): BackendStatus {
        return try {
            val isOnline = testConnection()
            BackendStatus(
                isOnline = isOnline,
                baseUrl = baseUrl,
                lastCheck = System.currentTimeMillis(),
                isOfflineMode = isOfflineMode
            )
        } catch (e: Exception) {
            BackendStatus(
                isOnline = false,
                baseUrl = baseUrl,
                lastCheck = System.currentTimeMillis(),
                isOfflineMode = isOfflineMode,
                error = e.message
            )
        }
    }
}

/**
 * BUDDY response data class
 */
data class BuddyResponse(
    val text: String,
    val intent: String? = null,
    val confidence: Double = 0.8,
    val actions: List<BuddyAction> = emptyList(),
    val metadata: Map<String, Any> = emptyMap(),
    val isOffline: Boolean = false
)

/**
 * BUDDY action data class
 */
data class BuddyAction(
    val type: String,
    val payload: String
)

/**
 * Backend status data class
 */
data class BackendStatus(
    val isOnline: Boolean,
    val baseUrl: String,
    val lastCheck: Long,
    val isOfflineMode: Boolean,
    val error: String? = null
)

/**
 * Voice-specific utilities
 */
object VoiceUtils {
    
    /**
     * Clean text for better TTS pronunciation
     */
    fun cleanTextForSpeech(text: String): String {
        return text
            .replace(Regex("[\\[\\](){}]"), "") // Remove brackets
            .replace(Regex("\\s+"), " ") // Normalize whitespace
            .replace("&", "and") // Replace ampersand
            .replace("@", "at") // Replace @ symbol
            .trim()
    }
    
    /**
     * Estimate speech duration
     */
    fun estimateSpeechDuration(text: String, wordsPerMinute: Int = 150): Long {
        val wordCount = text.split("\\s+".toRegex()).size
        return (wordCount * 60_000L) / wordsPerMinute // milliseconds
    }
    
    /**
     * Check if text is suitable for voice response
     */
    fun isVoiceFriendly(text: String): Boolean {
        return text.length <= 500 && // Not too long
               !text.contains(Regex("[\\[\\]{}()]+")) && // No complex formatting
               text.split("\\s+".toRegex()).size <= 100 // Max 100 words
    }
}
