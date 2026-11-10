package com.catchlarp.app.net

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class UrlPolicyTest {
    @Test
    fun normalizeBackendUrl_acceptsHttpsAndStripsPathAndTrailingSlash() {
        val result = UrlPolicy.normalizeBackendUrl(
            "https://catchlarp-app.onrender.com/api/chat?x=1",
            allowInsecureLanHttp = false,
        )
        assertTrue(result.isSuccess)
        assertEquals("https://catchlarp-app.onrender.com", result.getOrThrow())
    }

    @Test
    fun normalizeBackendUrl_addsHttpsForRemoteBareHostAndHttpForEmulator() {
        val remote = UrlPolicy.normalizeBackendUrl("catchlarp.onrender.com", allowInsecureLanHttp = false)
        assertEquals("https://catchlarp.onrender.com", remote.getOrThrow())

        val emulator = UrlPolicy.normalizeBackendUrl("10.0.2.2:8000", allowInsecureLanHttp = false)
        assertEquals("http://10.0.2.2:8000", emulator.getOrThrow())
    }

    @Test
    fun normalizeBackendUrl_enforcesHttpsInReleaseAndAllowsPrivateLanInDebug() {
        val releasePublicHttp = UrlPolicy.normalizeBackendUrl("http://example.com:8000", allowInsecureLanHttp = false)
        assertTrue(releasePublicHttp.isFailure)

        val releaseLanHttp = UrlPolicy.normalizeBackendUrl("http://192.168.1.42:8000", allowInsecureLanHttp = false)
        assertTrue(releaseLanHttp.isFailure)

        val debugLanHttp = UrlPolicy.normalizeBackendUrl("192.168.1.42:8000", allowInsecureLanHttp = true)
        assertEquals("http://192.168.1.42:8000", debugLanHttp.getOrThrow())
    }

    @Test
    fun normalizeBackendUrl_rejectsUnsafeSchemesAndCredentials() {
        assertTrue(UrlPolicy.normalizeBackendUrl("javascript:alert(1)", allowInsecureLanHttp = true).isFailure)
        assertTrue(UrlPolicy.normalizeBackendUrl("file:///etc/passwd", allowInsecureLanHttp = true).isFailure)
        assertTrue(UrlPolicy.normalizeBackendUrl("https://user:secret@example.com", allowInsecureLanHttp = true).isFailure)
    }

    @Test
    fun extractInstagramReelUrl_cleansShareCaptionsAndReelsVariants() {
        val shared = "Check out this claim https://www.instagram.com/reels/C8-xY12abc/?igsh=TRACK123 #facts"
        assertEquals("https://www.instagram.com/reel/C8-xY12abc/", UrlPolicy.extractInstagramReelUrl(shared))

        val creatorReel = "https://instagram.com/nasa/reel/Space_99-A/?utm_source=ig_web_copy_link"
        assertEquals("https://www.instagram.com/reel/Space_99-A/", UrlPolicy.extractInstagramReelUrl(creatorReel))

        val postLink = "https://m.instagram.com/p/Post_42/"
        assertEquals("https://www.instagram.com/p/Post_42/", UrlPolicy.extractInstagramReelUrl(postLink))

        val shareRedirect = "https://www.instagram.com/share/reel/opaque123"
        assertNull(UrlPolicy.extractInstagramReelUrl(shareRedirect))
        assertTrue(UrlPolicy.containsUnsupportedShareRedirect(shareRedirect))
    }

    @Test
    fun isSameOrigin_comparesSchemeHostAndEffectivePort() {
        assertTrue(UrlPolicy.isSameOrigin("https://app.example.com:443/api/chat", "https://app.example.com"))
        assertTrue(UrlPolicy.isSameOrigin("http://10.0.2.2:8000/login", "http://10.0.2.2:8000"))
        assertFalse(UrlPolicy.isSameOrigin("https://evil.example.com/", "https://app.example.com"))
        assertFalse(UrlPolicy.isSameOrigin("http://app.example.com/", "https://app.example.com"))
    }
}
