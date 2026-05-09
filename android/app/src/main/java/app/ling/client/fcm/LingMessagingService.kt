package app.ling.client.fcm

import android.util.Log
import app.ling.client.data.ReminderEvent
import app.ling.client.notif.ReminderNotifier
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage

/** 接收 FCM 数据消息并转成系统通知。 */
class LingMessagingService : FirebaseMessagingService() {

    override fun onNewToken(token: String) {
        super.onNewToken(token)
        Log.i(TAG, "new fcm token (len=${token.length})")
        // 实际注册由 FcmRegistrar.register(...) 在 App 启动 / Settings 保存时调用；
        // 这里只标记一次"token 已变更"，下次 register 会用新值。
        FcmRegistrar.markTokenChanged(applicationContext, token)
    }

    override fun onMessageReceived(message: RemoteMessage) {
        super.onMessageReceived(message)
        val data = message.data
        val event = ReminderEvent(
            eventId = data["event_id"].orEmpty().ifBlank { "fcm-${System.currentTimeMillis()}" },
            taskId = data["task_id"].orEmpty(),
            title = message.notification?.title ?: data["title"],
            deadline = data["deadline"]?.takeIf { it.isNotBlank() },
            fireAt = data["fire_at"]?.takeIf { it.isNotBlank() },
            overdue = data["overdue"] == "1" || data["overdue"] == "true",
        )
        if (event.taskId.isBlank()) {
            Log.w(TAG, "ignore fcm message without task_id: $data")
            return
        }
        ReminderNotifier.ensureChannel(applicationContext)
        ReminderNotifier.show(applicationContext, event)
    }

    companion object {
        private const val TAG = "LingMessagingService"
    }
}
