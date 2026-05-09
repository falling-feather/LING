package app.ling.client.ui

import android.os.Build
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.dynamicDarkColorScheme
import androidx.compose.material3.dynamicLightColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext

private val LightScheme = lightColorScheme(
    primary = Color(0xFF1F2933),
    onPrimary = Color.White,
    secondary = Color(0xFF52606D),
    background = Color(0xFFF5F7FA),
    surface = Color(0xFFFFFFFF),
)

private val DarkScheme = darkColorScheme(
    primary = Color(0xFFE4E7EB),
    onPrimary = Color(0xFF1F2933),
    secondary = Color(0xFFCBD2D9),
    background = Color(0xFF111418),
    surface = Color(0xFF1A1F26),
)

@Composable
fun LingTheme(
    useDarkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit,
) {
    val colors = when {
        Build.VERSION.SDK_INT >= Build.VERSION_CODES.S -> {
            val ctx = LocalContext.current
            if (useDarkTheme) dynamicDarkColorScheme(ctx) else dynamicLightColorScheme(ctx)
        }
        useDarkTheme -> DarkScheme
        else -> LightScheme
    }

    MaterialTheme(colorScheme = colors, content = content)
}
