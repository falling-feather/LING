package app.ling.client.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import app.ling.client.R
import app.ling.client.data.SettingsRepo
import app.ling.client.net.LingClient
import app.ling.client.work.WorkScheduler
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen() {
    val ctx = LocalContext.current
    val repo = remember { SettingsRepo(ctx) }
    val current by repo.settings.collectAsState(initial = null)
    val scope = rememberCoroutineScope()
    val snackbar = remember { SnackbarHostState() }

    var baseUrl by remember { mutableStateOf("") }
    var apiKey by remember { mutableStateOf("") }
    var pollMin by remember { mutableStateOf("15") }
    var notifEnabled by remember { mutableStateOf(true) }

    // 把 DataStore 当前值同步到表单
    LaunchedEffect(current?.baseUrl, current?.apiKey, current?.pollIntervalMinutes, current?.notificationsEnabled) {
        current?.let {
            baseUrl = it.baseUrl
            apiKey = it.apiKey
            pollMin = it.pollIntervalMinutes.toString()
            notifEnabled = it.notificationsEnabled
        }
    }

    Scaffold(
        topBar = { TopAppBar(title = { Text(stringResource(R.string.settings_title)) }) },
        snackbarHost = { SnackbarHost(snackbar) },
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            OutlinedTextField(
                modifier = Modifier.fillMaxWidth(),
                value = baseUrl,
                onValueChange = { baseUrl = it },
                label = { Text(stringResource(R.string.settings_base_url)) },
                placeholder = { Text(stringResource(R.string.settings_base_url_hint)) },
                singleLine = true,
            )
            OutlinedTextField(
                modifier = Modifier.fillMaxWidth(),
                value = apiKey,
                onValueChange = { apiKey = it },
                label = { Text(stringResource(R.string.settings_api_key)) },
                placeholder = { Text(stringResource(R.string.settings_api_key_hint)) },
                singleLine = true,
            )
            OutlinedTextField(
                modifier = Modifier.fillMaxWidth(),
                value = pollMin,
                onValueChange = { v -> pollMin = v.filter { it.isDigit() } },
                label = { Text(stringResource(R.string.settings_poll_interval)) },
                singleLine = true,
            )
            androidx.compose.foundation.layout.Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text("启用提醒通知", modifier = Modifier.weight(1f))
                Switch(checked = notifEnabled, onCheckedChange = { notifEnabled = it })
            }

            Button(
                modifier = Modifier.fillMaxWidth(),
                onClick = {
                    scope.launch {
                        repo.update {
                            it.copy(
                                baseUrl = baseUrl,
                                apiKey = apiKey,
                                pollIntervalMinutes = pollMin.toIntOrNull() ?: 15,
                                notificationsEnabled = notifEnabled,
                            )
                        }
                        WorkScheduler.scheduleOrUpdate(ctx)
                        snackbar.showSnackbar(ctx.getString(R.string.settings_saved))
                    }
                },
            ) { Text(stringResource(R.string.action_save)) }

            Button(
                modifier = Modifier.fillMaxWidth(),
                onClick = {
                    scope.launch {
                        val client = LingClient(baseUrl.trim().trimEnd('/'), apiKey.trim())
                        val ok = client.healthz()
                        snackbar.showSnackbar(if (ok) "连接成功 ✓" else "连接失败 ✗")
                    }
                },
            ) { Text(stringResource(R.string.settings_test_connection)) }
        }
    }
}
