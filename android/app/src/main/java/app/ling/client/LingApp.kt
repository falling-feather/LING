package app.ling.client

import android.app.Application
import androidx.work.Configuration
import app.ling.client.notif.ReminderNotifier
import app.ling.client.work.WorkScheduler

class LingApp : Application(), Configuration.Provider {

    override fun onCreate() {
        super.onCreate()
        ReminderNotifier.ensureChannel(this)
        // 启动后第一时间登记 / 更新一次后台轮询
        WorkScheduler.scheduleOrUpdate(this)
    }

    // WorkManager 默认从这里取配置
    override val workManagerConfiguration: Configuration
        get() = Configuration.Builder()
            .setMinimumLoggingLevel(android.util.Log.INFO)
            .build()
}
