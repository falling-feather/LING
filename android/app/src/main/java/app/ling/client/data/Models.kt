package app.ling.client.data

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

/** 与服务端 GET /tasks 单条返回结构一致 */
@Serializable
data class Task(
    val id: String,
    val title: String,
    val status: String,
    val deadline: String? = null,
    val notes: String? = null,
    @SerialName("updated_at") val updatedAt: String? = null,
)

/** 服务端 GET /reminders/pending 单条事件 */
@Serializable
data class ReminderEvent(
    @SerialName("event_id") val eventId: String,
    @SerialName("task_id") val taskId: String,
    val title: String? = null,
    val deadline: String? = null,
    @SerialName("fire_at") val fireAt: String? = null,
    val overdue: Boolean = false,
    val type: String = "reminder",
    val state: String = "pending",
    @SerialName("created_at") val createdAt: String? = null,
)

@Serializable
data class CaptureRequest(val text: String)

@Serializable
data class SnoozeRequest(val minutes: Int)

@Serializable
data class RescheduleRequest(val deadline: String)

@Serializable
data class GenericResponse(
    val ok: Boolean = false,
    @SerialName("git_sha") val gitSha: String? = null,
    val appended: String? = null,
)

@Serializable
data class RegisterDeviceRequest(
    @SerialName("device_id") val deviceId: String,
    @SerialName("fcm_token") val fcmToken: String,
    val platform: String = "android",
    val label: String? = null,
)

@Serializable
data class UnregisterDeviceRequest(
    @SerialName("device_id") val deviceId: String,
)
