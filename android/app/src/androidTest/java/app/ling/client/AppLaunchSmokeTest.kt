package app.ling.client

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/** App 启动后底部 Tab "任务 / 捕获 / 设置" 三个标签应该都能渲染出来。 */
@RunWith(AndroidJUnit4::class)
class AppLaunchSmokeTest {

    @get:Rule
    val composeRule = createAndroidComposeRule<MainActivity>()

    @Test
    fun bottomTabs_areVisible() {
        composeRule.onNodeWithText("任务").assertIsDisplayed()
        composeRule.onNodeWithText("捕获").assertIsDisplayed()
        composeRule.onNodeWithText("设置").assertIsDisplayed()
    }

    @Test
    fun emptyState_or_error_is_shown() {
        // 未配置服务器时 TaskList 应显示提示
        composeRule.waitForIdle()
        // 这两个候选其一会出现
        val anyExpected = listOf(
            "请先到「设置」配置",
            "暂无任务",
        )
        // 用 Assertions：找到任意一条
        var found = false
        for (txt in anyExpected) {
            try {
                composeRule.onNodeWithText(txt, substring = true).assertIsDisplayed()
                found = true
                break
            } catch (_: AssertionError) {
                // try next
            }
        }
        assert(found) { "expected an empty/unconfigured hint to be shown" }
    }
}
