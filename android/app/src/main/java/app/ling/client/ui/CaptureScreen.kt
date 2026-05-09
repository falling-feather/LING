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
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import app.ling.client.R
import app.ling.client.data.SettingsRepo
import app.ling.client.net.LingClient
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CaptureScreen() {
    val ctx = LocalContext.current
    val settings by SettingsRepo(ctx).settings.collectAsState(initial = null)
    val scope = rememberCoroutineScope()
    val snackbar = remember { SnackbarHostState() }

    var input by remember { mutableStateOf("") }
    var submitting by remember { mutableStateOf(false) }

    Scaffold(
        topBar = { TopAppBar(title = { Text(stringResource(R.string.capture_title)) }) },
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
                modifier = Modifier
                    .fillMaxWidth(),
                value = input,
                onValueChange = { input = it },
                label = { Text(stringResource(R.string.capture_hint)) },
                minLines = 4,
            )
            Button(
                modifier = Modifier.fillMaxWidth(),
                enabled = !submitting && input.isNotBlank() && (settings?.isConfigured == true),
                onClick = {
                    val s = settings ?: return@Button
                    val client = LingClient.fromSettings(s) ?: return@Button
                    val text = input.trim()
                    submitting = true
                    scope.launch {
                        try {
                            client.capture(text)
                            input = ""
                            snackbar.showSnackbar(ctx.getString(R.string.capture_done))
                        } catch (t: Throwable) {
                            snackbar.showSnackbar("失败：${t.message}")
                        } finally {
                            submitting = false
                        }
                    }
                },
            ) {
                Text(stringResource(R.string.capture_submit))
            }
            if (settings?.isConfigured == false) {
                Text(text = "请先在「设置」中配置服务器")
            }
        }
    }
}
