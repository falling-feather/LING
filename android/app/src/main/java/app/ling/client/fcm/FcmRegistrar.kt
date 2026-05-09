package app.ling.client.fcm

import android.content.Context
import android.provider.Settings as AndroidSettings
import android.util.Log
import app.ling.client.data.SettingsRepo
import app.ling.client.net.LingClient
import com.google.firebase.messaging.FirebaseMessaging
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import kotlinx.coroutines.suspendCancellableCoroutine
import java.util.concurrent.atomic.AtomicReference
import kotlin.coroutines.resume

/**
 * 负责把 FCM token 注册到 LING 服务端。
 *
 * 调用时机：
 * - App 启动时（`LingApp.onCreate`）
 * - Settings 保存后（baseUrl 或 apiKey 变化时）
 * - FCM 重新派发 token 时（`LingMessagingService.onNewToken`）
 *
 * Firebase 没初始化（用户没放 google-services.json）时，调用会被 try-catch 吞掉，
 * App 仍然可以走轮询拿提醒。
 */
object FcmRegistrar {

    private const val TAG = "FcmRegistrar"
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private val pendingToken = AtomicReference<String?>(null)

    fun markTokenChanged(ctx: Context, token: String) {
        pendingToken.set(token)
        // 异步尝试注册一次；失败忽略，下次启动会再试
        register(ctx)
    }

    fun register(ctx: Context) {
        scope.launch {
            try {
                val repo = SettingsRepo(ctx)
                val s = repo.settings.first()
                if (!s.isConfigured) {
                    Log.d(TAG, "not configured, skip register")
                    return@launch
                }
                val deviceId = ensureDeviceId(ctx, s.deviceId)
                val token = pendingToken.getAndSet(null) ?: fetchToken() ?: run {
                    Log.d(TAG, "no fcm token (firebase not initialized?), skip")
                    return@launch
                }
                if (token.isBlank()) return@launch
                if (token == s.lastRegisteredFcmToken && deviceId == s.deviceId) {
                    Log.d(TAG, "token unchanged, skip")
                    return@launch
                }
                val client = LingClient(s.baseUrl, s.apiKey)
                client.registerDevice(
                    deviceId = deviceId,
                    fcmToken = token,
                    label = android.os.Build.MODEL,
                )
                repo.update {
                    it.copy(deviceId = deviceId, lastRegisteredFcmToken = token)
                }
                Log.i(TAG, "registered device_id=$deviceId token len=${token.length}")
            } catch (t: Throwable) {
                Log.w(TAG, "register failed (will retry next time): ${t.message}")
            }
        }
    }

    private suspend fun fetchToken(): String? = try {
        suspendCancellableCoroutine { cont ->
            FirebaseMessaging.getInstance().token
                .addOnSuccessListener { token ->
                    if (cont.isActive) cont.resume(token)
                }
                .addOnFailureListener { _ ->
                    if (cont.isActive) cont.resume(null)
                }
        }
    } catch (t: Throwable) {
        Log.d(TAG, "FirebaseMessaging.getToken() failed: ${t.message}")
        null
    }

    @Suppress("DEPRECATION")
    private fun ensureDeviceId(ctx: Context, current: String): String {
        if (current.isNotBlank()) return current
        // ANDROID_ID 在不同应用 / 不同用户下会不同，足够稳定且不依赖额外权限
        val raw = AndroidSettings.Secure.getString(
            ctx.contentResolver,
            AndroidSettings.Secure.ANDROID_ID,
        )
        return if (!raw.isNullOrBlank()) "android-$raw" else "android-${System.currentTimeMillis()}"
    }
}
