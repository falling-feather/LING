package app.ling.client.work

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import app.ling.client.data.SettingsRepo
import app.ling.client.net.LingClient
import app.ling.client.notif.ReminderNotifier
import kotlinx.coroutines.flow.first

/** 周期性轮询 /reminders/pending，把每条事件转成系统通知 */
class ReminderWorker(
    appContext: Context,
    params: WorkerParameters,
) : CoroutineWorker(appContext, params) {

    override suspend fun doWork(): Result {
        val settings = SettingsRepo(applicationContext).settings.first()
        if (!settings.isConfigured || !settings.notificationsEnabled) return Result.success()

        val client = LingClient.fromSettings(settings) ?: return Result.success()
        ReminderNotifier.ensureChannel(applicationContext)

        val events = try {
            client.pendingReminders(limit = 20)
        } catch (_: Throwable) {
            // 网络错误时让 WorkManager 走重试，避免错过提醒
            return Result.retry()
        }

        events.forEach { ReminderNotifier.show(applicationContext, it) }
        return Result.success()
    }
}
