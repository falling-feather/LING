package app.ling.client.ui

import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AddCircleOutline
import androidx.compose.material.icons.filled.CheckCircleOutline
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.navigation.NavHostController
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import androidx.navigation.navDeepLink
import app.ling.client.R

object Routes {
    const val TASKS = "tasks"
    const val CAPTURE = "capture"
    const val SETTINGS = "settings"
    const val TASK_DETAIL = "task/{id}"
    fun taskDetail(id: String) = "task/$id"
}

private data class Tab(val route: String, val labelRes: Int, val icon: androidx.compose.ui.graphics.vector.ImageVector)

private val tabs = listOf(
    Tab(Routes.TASKS, R.string.nav_tasks, Icons.Filled.CheckCircleOutline),
    Tab(Routes.CAPTURE, R.string.nav_capture, Icons.Filled.AddCircleOutline),
    Tab(Routes.SETTINGS, R.string.nav_settings, Icons.Filled.Settings),
)

@Composable
fun LingNavRoot(navController: NavHostController = rememberNavController()) {
    val backStack by navController.currentBackStackEntryAsState()
    val currentRoute = backStack?.destination?.route

    Scaffold(
        bottomBar = {
            // 任务详情页隐藏底部栏
            if (currentRoute == null || currentRoute in tabs.map { it.route }) {
                NavigationBar {
                    tabs.forEach { tab ->
                        NavigationBarItem(
                            selected = currentRoute == tab.route,
                            onClick = {
                                if (currentRoute != tab.route) {
                                    navController.navigate(tab.route) {
                                        popUpTo(Routes.TASKS) { saveState = true }
                                        launchSingleTop = true
                                        restoreState = true
                                    }
                                }
                            },
                            icon = { Icon(tab.icon, contentDescription = null) },
                            label = { Text(stringResource(tab.labelRes)) },
                        )
                    }
                }
            }
        },
    ) { padding ->
        LingNavGraph(navController, padding)
    }
}

@Composable
private fun LingNavGraph(navController: NavHostController, padding: PaddingValues) {
    NavHost(
        navController = navController,
        startDestination = Routes.TASKS,
        modifier = Modifier.padding(padding),
    ) {
        composable(Routes.TASKS) {
            TaskListScreen(
                onTaskClick = { id -> navController.navigate(Routes.taskDetail(id)) },
            )
        }
        composable(Routes.CAPTURE) { CaptureScreen() }
        composable(Routes.SETTINGS) { SettingsScreen() }

        composable(
            route = Routes.TASK_DETAIL,
            arguments = listOf(navArgument("id") { type = NavType.StringType }),
            deepLinks = listOf(navDeepLink { uriPattern = "ling://task/{id}" }),
        ) { entry ->
            val id = entry.arguments?.getString("id").orEmpty()
            TaskDetailScreen(
                taskId = id,
                onBack = { navController.popBackStack() },
            )
        }
    }
}
