package app.ling.client.notif

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.net.Uri
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import app.ling.client.MainActivity
import app.ling.client.R
import app.ling.client.data.ReminderEvent

object ReminderNotifier {
    const val CHANNEL_ID = "reminders"

    fun ensureChannel(ctx: Context) {
        val nm = ctx.getSystemService(NotificationManager::class.java) ?: return
        if (nm.getNotificationChannel(CHANNEL_ID) != null) return
        val channel = NotificationChannel(
            CHANNEL_ID,
            ctx.getString(R.string.notif_channel_reminders),
            NotificationManager.IMPORTANCE_HIGH,
        ).apply {
            description = ctx.getString(R.string.notif_channel_reminders_desc)
            enableLights(true)
            enableVibration(true)
        }
        nm.createNotificationChannel(channel)
    }

    /** 用 task_id 作为稳定 notification id（同一任务的多次提醒会替换上一条） */
    private fun notifIdFor(taskId: String): Int = taskId.hashCode()

    fun show(ctx: Context, event: ReminderEvent) {
        val title = buildString {
            if (event.overdue) append(ctx.getString(R.string.notif_overdue_prefix))
            append(event.title ?: event.taskId)
        }
        val text = listOfNotNull(
            event.deadline?.let { "截止：$it" },
            event.fireAt?.let { "提醒：$it" },
        ).joinToString(" · ")

        val deepLink = "ling://task/${event.taskId}"
        val intent = Intent(ctx, MainActivity::class.java).apply {
            action = Intent.ACTION_VIEW
            data = Uri.parse(deepLink)
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP)
        }
        val pi = PendingIntent.getActivity(
            ctx,
            event.eventId.hashCode(),
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )

        val notification = NotificationCompat.Builder(ctx, CHANNEL_ID)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentTitle(title)
            .setContentText(text.ifBlank { event.title.orEmpty() })
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setAutoCancel(true)
            .setContentIntent(pi)
            .build()

        // Android 13+ 需要 POST_NOTIFICATIONS 权限；用户没授予时 NotificationManagerCompat.notify 会被静默忽略
        val canNotify = ContextCompat.checkSelfPermission(
            ctx, "android.permission.POST_NOTIFICATIONS"
        ) == android.content.pm.PackageManager.PERMISSION_GRANTED
        if (!canNotify) return

        NotificationManagerCompat.from(ctx).notify(notifIdFor(event.taskId), notification)
    }
}
