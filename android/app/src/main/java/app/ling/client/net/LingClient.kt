package app.ling.client.net

import app.ling.client.data.CaptureRequest
import app.ling.client.data.GenericResponse
import app.ling.client.data.LingSettings
import app.ling.client.data.ReminderEvent
import app.ling.client.data.RescheduleRequest
import app.ling.client.data.SnoozeRequest
import app.ling.client.data.Task
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.IOException
import java.util.concurrent.TimeUnit

/** 与 server/python 暴露的 HTTP API 一一对应。所有请求带 X-API-Key。 */
class LingClient(private val baseUrl: String, private val apiKey: String) {

    private val json = Json {
        ignoreUnknownKeys = true
        explicitNulls = false
    }

    private val client = OkHttpClient.Builder()
        .connectTimeout(8, TimeUnit.SECONDS)
        .readTimeout(15, TimeUnit.SECONDS)
        .writeTimeout(15, TimeUnit.SECONDS)
        .retryOnConnectionFailure(true)
        .build()

    private val mediaJson = "application/json; charset=utf-8".toMediaType()

    private fun urlOf(path: String): String =
        baseUrl.trimEnd('/') + (if (path.startsWith("/")) path else "/$path")

    private fun newRequest(path: String): Request.Builder =
        Request.Builder()
            .url(urlOf(path))
            .header("X-API-Key", apiKey)
            .header("Accept", "application/json")

    @Throws(IOException::class)
    private suspend inline fun <reified T> getJson(path: String): T = withContext(Dispatchers.IO) {
        client.newCall(newRequest(path).get().build()).execute().use { resp ->
            val body = resp.body?.string().orEmpty()
            if (!resp.isSuccessful) throw IOException("HTTP ${resp.code} on GET $path: $body")
            json.decodeFromString(body)
        }
    }

    @Throws(IOException::class)
    private suspend inline fun <reified Req, reified Resp> postJson(path: String, body: Req): Resp =
        withContext(Dispatchers.IO) {
            val payload = json.encodeToString(body).toRequestBody(mediaJson)
            client.newCall(newRequest(path).post(payload).build()).execute().use { resp ->
                val text = resp.body?.string().orEmpty()
                if (!resp.isSuccessful) throw IOException("HTTP ${resp.code} on POST $path: $text")
                if (text.isBlank()) {
                    @Suppress("UNCHECKED_CAST")
                    GenericResponse(ok = true) as Resp
                } else {
                    json.decodeFromString(text)
                }
            }
        }

    @Throws(IOException::class)
    private suspend fun postEmpty(path: String): GenericResponse = withContext(Dispatchers.IO) {
        val payload = "{}".toRequestBody(mediaJson)
        client.newCall(newRequest(path).post(payload).build()).execute().use { resp ->
            val text = resp.body?.string().orEmpty()
            if (!resp.isSuccessful) throw IOException("HTTP ${resp.code} on POST $path: $text")
            if (text.isBlank()) GenericResponse(ok = true)
            else json.decodeFromString(text)
        }
    }

    suspend fun healthz(): Boolean = try {
        withContext(Dispatchers.IO) {
            client.newCall(Request.Builder().url(urlOf("/healthz")).get().build())
                .execute()
                .use { it.isSuccessful }
        }
    } catch (_: Throwable) {
        false
    }

    suspend fun listTasks(): List<Task> = getJson("/tasks")

    suspend fun getTask(id: String): Task = getJson("/tasks/$id")

    suspend fun pendingReminders(limit: Int = 20): List<ReminderEvent> =
        getJson("/reminders/pending?limit=$limit")

    suspend fun completeTask(id: String): GenericResponse = postEmpty("/tasks/$id/complete")

    suspend fun snoozeTask(id: String, minutes: Int): GenericResponse =
        postJson("/tasks/$id/snooze", SnoozeRequest(minutes))

    suspend fun rescheduleTask(id: String, deadlineIso: String): GenericResponse =
        postJson("/tasks/$id/reschedule", RescheduleRequest(deadlineIso))

    suspend fun capture(text: String): GenericResponse =
        postJson("/capture", CaptureRequest(text))

    companion object {
        fun fromSettings(s: LingSettings): LingClient? =
            if (s.isConfigured) LingClient(s.baseUrl, s.apiKey) else null
    }
}
