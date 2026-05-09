package app.ling.client.work

import android.content.Context
import androidx.work.Constraints
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.NetworkType
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import app.ling.client.data.SettingsRepo
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking
import java.util.concurrent.TimeUnit

/** 把周期性 ReminderWorker 注册/更新到 WorkManager。 */
object WorkScheduler {
    private const val UNIQUE_NAME = "reminder-polling"

    fun scheduleOrUpdate(ctx: Context) {
        val minutes = runBlocking {
            runCatching { SettingsRepo(ctx).settings.first().pollIntervalMinutes }
                .getOrDefault(15)
        }.coerceAtLeast(15)

        val constraints = Constraints.Builder()
            .setRequiredNetworkType(NetworkType.CONNECTED)
            .build()

        val request = PeriodicWorkRequestBuilder<ReminderWorker>(
            minutes.toLong(), TimeUnit.MINUTES,
        )
            .setConstraints(constraints)
            .build()

        WorkManager.getInstance(ctx).enqueueUniquePeriodicWork(
            UNIQUE_NAME,
            ExistingPeriodicWorkPolicy.UPDATE,
            request,
        )
    }

    fun cancel(ctx: Context) {
        WorkManager.getInstance(ctx).cancelUniqueWork(UNIQUE_NAME)
    }
}
