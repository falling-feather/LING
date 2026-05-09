package app.ling.client.net

import kotlinx.coroutines.test.runTest
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import okhttp3.mockwebserver.RecordedRequest
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

class LingClientTest {

    private lateinit var server: MockWebServer
    private lateinit var client: LingClient

    @Before
    fun setUp() {
        server = MockWebServer().also { it.start() }
        client = LingClient(server.url("/").toString().trimEnd('/'), apiKey = "test-key")
    }

    @After
    fun tearDown() {
        server.shutdown()
    }

    private fun nextRequest(): RecordedRequest = server.takeRequest()

    @Test
    fun `healthz returns true on 200`() = runTest {
        server.enqueue(MockResponse().setResponseCode(200).setBody("""{"ok":true}"""))
        assertTrue(client.healthz())

        val req = nextRequest()
        assertEquals("/healthz", req.path)
        assertEquals("GET", req.method)
    }

    @Test
    fun `healthz returns false on non-200`() = runTest {
        server.enqueue(MockResponse().setResponseCode(503))
        assertEquals(false, client.healthz())
    }

    @Test
    fun `listTasks decodes array`() = runTest {
        server.enqueue(
            MockResponse().setResponseCode(200).setBody(
                """[
                    {"id":"a","title":"任务A","status":"todo","deadline":"2026-05-11T10:00:00+08:00"},
                    {"id":"b","title":"任务B","status":"done"}
                ]""".trimIndent(),
            ),
        )
        val tasks = client.listTasks()
        assertEquals(2, tasks.size)
        assertEquals("a", tasks[0].id)
        assertEquals("任务A", tasks[0].title)
        assertEquals("done", tasks[1].status)
        assertNull(tasks[1].deadline)

        val req = nextRequest()
        assertEquals("/tasks", req.path)
        assertEquals("test-key", req.getHeader("X-API-Key"))
    }

    @Test
    fun `getTask uses path id`() = runTest {
        server.enqueue(
            MockResponse().setResponseCode(200).setBody(
                """{"id":"x","title":"X","status":"todo"}""",
            ),
        )
        val t = client.getTask("x")
        assertEquals("x", t.id)
        assertEquals("/tasks/x", nextRequest().path)
    }

    @Test
    fun `completeTask sends POST and parses git_sha`() = runTest {
        server.enqueue(
            MockResponse().setResponseCode(200).setBody(
                """{"ok":true,"git_sha":"abc123"}""",
            ),
        )
        val resp = client.completeTask("a")
        assertTrue(resp.ok)
        assertEquals("abc123", resp.gitSha)

        val req = nextRequest()
        assertEquals("POST", req.method)
        assertEquals("/tasks/a/complete", req.path)
    }

    @Test
    fun `snoozeTask sends minutes in body`() = runTest {
        server.enqueue(
            MockResponse().setResponseCode(200).setBody("""{"ok":true,"fire_at":"2026-01-01T00:00:00+08:00"}"""),
        )
        client.snoozeTask("a", 30)
        val req = nextRequest()
        assertEquals("POST", req.method)
        assertEquals("/tasks/a/snooze", req.path)
        assertTrue(req.body.readUtf8().contains(""""minutes":30"""))
    }

    @Test
    fun `rescheduleTask serializes deadline`() = runTest {
        server.enqueue(MockResponse().setResponseCode(200).setBody("""{"ok":true}"""))
        client.rescheduleTask("a", "2026-05-12T10:00:00+08:00")
        val req = nextRequest()
        assertTrue(req.body.readUtf8().contains("2026-05-12T10:00:00+08:00"))
    }

    @Test
    fun `pendingReminders parses event list`() = runTest {
        server.enqueue(
            MockResponse().setResponseCode(200).setBody(
                """[
                    {"event_id":"e1","task_id":"t1","title":"Hello","fire_at":"2026-05-09T22:00:00+08:00","overdue":false,"type":"reminder","state":"pending","created_at":"2026-05-09T21:59:00+08:00"},
                    {"event_id":"e2","task_id":"t2","title":"World","overdue":true,"type":"reminder","state":"pending","created_at":"2026-05-09T22:00:00+08:00"}
                ]""".trimIndent(),
            ),
        )
        val list = client.pendingReminders()
        assertEquals(2, list.size)
        assertEquals("e1", list[0].eventId)
        assertEquals(true, list[1].overdue)

        val req = nextRequest()
        assertTrue(req.path?.startsWith("/reminders/pending") == true)
    }

    @Test
    fun `capture posts text`() = runTest {
        server.enqueue(MockResponse().setResponseCode(200).setBody("""{"ok":true,"appended":"hi"}"""))
        val r = client.capture("hello 中文")
        assertTrue(r.ok)
        assertEquals("hi", r.appended)

        val req = nextRequest()
        assertEquals("POST", req.method)
        assertEquals("/capture", req.path)
        // body 应该是 UTF-8 编码的 JSON，包含中文
        val body = req.body.readUtf8()
        assertTrue(body.contains("hello 中文"))
    }

    @Test
    fun `registerDevice sends correct fields`() = runTest {
        server.enqueue(MockResponse().setResponseCode(200).setBody("""{"ok":true,"device_id":"d1","updated_at":"x"}"""))
        client.registerDevice(deviceId = "d1", fcmToken = "tok-X", label = "phone")
        val req = nextRequest()
        assertEquals("/devices/register", req.path)
        val body = req.body.readUtf8()
        assertTrue(body.contains(""""device_id":"d1""""))
        assertTrue(body.contains(""""fcm_token":"tok-X""""))
        assertTrue(body.contains(""""label":"phone""""))
    }

    @Test
    fun `unregisterDevice posts device_id`() = runTest {
        server.enqueue(MockResponse().setResponseCode(200).setBody("""{"ok":true}"""))
        client.unregisterDevice("d1")
        val req = nextRequest()
        assertEquals("/devices/unregister", req.path)
        assertTrue(req.body.readUtf8().contains(""""device_id":"d1""""))
    }

    @Test
    fun `non-2xx throws IOException`() = runTest {
        server.enqueue(MockResponse().setResponseCode(401).setBody("""{"error":"unauthorized"}"""))
        var failed = false
        try {
            client.listTasks()
        } catch (e: java.io.IOException) {
            failed = true
            assertNotNull(e.message)
            assertTrue(e.message!!.contains("401"))
        }
        assertTrue(failed)
    }
}
