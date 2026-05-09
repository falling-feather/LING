package app.ling.client.data

import android.content.Context
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.intPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

/** App 设置；用 DataStore Preferences 持久化 */
data class LingSettings(
    val baseUrl: String = "",
    val apiKey: String = "",
    val pollIntervalMinutes: Int = 15,
    val notificationsEnabled: Boolean = true,
) {
    val isConfigured: Boolean get() = baseUrl.isNotBlank() && apiKey.isNotBlank()
}

private val Context.dataStore by preferencesDataStore(name = "ling_settings")

object SettingsKeys {
    val BASE_URL = stringPreferencesKey("base_url")
    val API_KEY = stringPreferencesKey("api_key")
    val POLL_MIN = intPreferencesKey("poll_interval_minutes")
    val NOTIF_ENABLED = booleanPreferencesKey("notif_enabled")
}

class SettingsRepo(private val context: Context) {

    val settings: Flow<LingSettings> = context.dataStore.data.map { prefs ->
        LingSettings(
            baseUrl = prefs[SettingsKeys.BASE_URL].orEmpty().trim().trimEnd('/'),
            apiKey = prefs[SettingsKeys.API_KEY].orEmpty().trim(),
            pollIntervalMinutes = prefs[SettingsKeys.POLL_MIN] ?: 15,
            notificationsEnabled = prefs[SettingsKeys.NOTIF_ENABLED] ?: true,
        )
    }

    suspend fun update(transform: (LingSettings) -> LingSettings) {
        context.dataStore.edit { prefs ->
            val current = LingSettings(
                baseUrl = prefs[SettingsKeys.BASE_URL].orEmpty(),
                apiKey = prefs[SettingsKeys.API_KEY].orEmpty(),
                pollIntervalMinutes = prefs[SettingsKeys.POLL_MIN] ?: 15,
                notificationsEnabled = prefs[SettingsKeys.NOTIF_ENABLED] ?: true,
            )
            val next = transform(current)
            prefs[SettingsKeys.BASE_URL] = next.baseUrl.trim().trimEnd('/')
            prefs[SettingsKeys.API_KEY] = next.apiKey.trim()
            prefs[SettingsKeys.POLL_MIN] = next.pollIntervalMinutes.coerceAtLeast(15)
            prefs[SettingsKeys.NOTIF_ENABLED] = next.notificationsEnabled
        }
    }
}
