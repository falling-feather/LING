package app.ling.client.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
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
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import app.ling.client.R
import app.ling.client.data.SettingsRepo
import app.ling.client.data.Task
import app.ling.client.net.LingClient
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TaskDetailScreen(taskId: String, onBack: () -> Unit) {
    val ctx = LocalContext.current
    val settings by SettingsRepo(ctx).settings.collectAsState(initial = null)
    val scope = rememberCoroutineScope()
    val snackbar = remember { SnackbarHostState() }

    var task by remember { mutableStateOf<Task?>(null) }
    var loading by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }

    suspend fun reload(client: LingClient) {
        loading = true
        try {
            task = client.getTask(taskId)
            error = null
        } catch (t: Throwable) {
            error = t.message
        } finally {
            loading = false
        }
    }

    LaunchedEffect(taskId, settings?.baseUrl, settings?.apiKey) {
        val s = settings ?: return@LaunchedEffect
        val client = LingClient.fromSettings(s) ?: return@LaunchedEffect
        reload(client)
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(stringResource(R.string.task_detail_title)) },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = stringResource(R.string.action_back))
                    }
                },
            )
        },
        snackbarHost = { SnackbarHost(snackbar) },
    ) { padding ->
        val s = settings ?: return@Scaffold
        val client = LingClient.fromSettings(s)

        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            if (error != null) {
                Text(text = error!!, color = MaterialTheme.colorScheme.error)
            }
            val t = task
            if (t == null) {
                if (loading) Text("加载中…")
                return@Column
            }
            Text(text = t.title, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.SemiBold)
            Text(
                text = "状态：${t.status}",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.8f),
            )
            t.deadline?.let {
                Text(
                    text = "截止：$it",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.8f),
                )
            }
            if (!t.notes.isNullOrBlank()) {
                Text(text = t.notes, style = MaterialTheme.typography.bodyLarge)
            }

            if (client != null) {
                Button(
                    modifier = Modifier.fillMaxWidth(),
                    onClick = {
                        scope.launch {
                            try {
                                client.completeTask(t.id)
                                snackbar.showSnackbar("已标记为完成")
                                reload(client)
                            } catch (e: Throwable) {
                                snackbar.showSnackbar("失败：${e.message}")
                            }
                        }
                    },
                    enabled = t.status.lowercase() != "done",
                ) {
                    Text(stringResource(R.string.task_action_complete))
                }

                Text(stringResource(R.string.task_action_snooze), style = MaterialTheme.typography.titleSmall)
                Row(
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    listOf(15 to R.string.task_snooze_15, 60 to R.string.task_snooze_60, 240 to R.string.task_snooze_240)
                        .forEach { (m, label) ->
                            OutlinedButton(
                                modifier = Modifier.weight(1f),
                                onClick = {
                                    scope.launch {
                                        try {
                                            client.snoozeTask(t.id, m)
                                            snackbar.showSnackbar("已设定 $m 分钟后再提醒")
                                        } catch (e: Throwable) {
                                            snackbar.showSnackbar("失败：${e.message}")
                                        }
                                    }
                                },
                            ) { Text(stringResource(label)) }
                        }
                }
            }
        }
    }
}
