package com.catchlarp.app.auth

import com.catchlarp.app.AppConfig
import com.catchlarp.app.BuildConfig
import com.catchlarp.app.net.CatchLarpApiClient
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.nio.charset.StandardCharsets
import java.util.Base64

class SupabaseAuthConfigTest {
    private fun fakeJwtWithRole(role: String): String {
        val header = Base64.getUrlEncoder().withoutPadding()
            .encodeToString("""{"alg":"HS256","typ":"JWT"}""".toByteArray(StandardCharsets.UTF_8))
        val payload = Base64.getUrlEncoder().withoutPadding()
            .encodeToString("""{"iss":"supabase","role":"$role"}""".toByteArray(StandardCharsets.UTF_8))
        return "$header.$payload.fakesig"
    }

    @Test
    fun appConfig_routesToPermanentRenderBackendAndExposesNoSecrets() {
        assertEquals("https://catchlarp.onrender.com", AppConfig.PRODUCTION_BACKEND_URL)
        assertEquals("https://catchlarp.onrender.com", AppConfig.DEFAULT_BACKEND_URL)
        assertEquals("https://catchlarp.onrender.com", BuildConfig.DEFAULT_BACKEND_URL)

        val fieldNames = BuildConfig::class.java.declaredFields.map { it.name.uppercase() }
        assertTrue(fieldNames.contains("SUPABASE_URL"))
        assertTrue(fieldNames.contains("SUPABASE_ANON_KEY"))
        assertTrue(fieldNames.contains("DEFAULT_BACKEND_URL"))

        val forbidden = listOf("JWT_SECRET", "SERVICE_ROLE", "GROQ", "GEMINI", "ADMIN_KEY")
        for (name in fieldNames) {
            for (bad in forbidden) {
                assertFalse("Unexpected secret BuildConfig field: $name", name.contains(bad))
            }
        }
    }

    @Test
    fun supabaseConfig_acceptsPublicUrlAndAnonKeyAndRejectsServiceRoleOrSecretKeys() {
        val validAnonJwt = fakeJwtWithRole("anon")
        val okJwt = SupabaseConfig.validate("https://xyzproj.supabase.co/", validAnonJwt)
        assertTrue(okJwt.isSuccess)
        assertEquals("https://xyzproj.supabase.co", okJwt.getOrThrow().supabaseUrl)
        assertEquals(validAnonJwt, okJwt.getOrThrow().supabaseAnonKey)

        val okPublishable = SupabaseConfig.validate("https://xyzproj.supabase.co", "sb_publishable_public123")
        assertTrue(okPublishable.isSuccess)

        val serviceRoleJwt = fakeJwtWithRole("service_role")
        assertTrue(SupabaseConfig.validate("https://xyzproj.supabase.co", serviceRoleJwt).isFailure)
        assertTrue(SupabaseConfig.validate("https://xyzproj.supabase.co", "sb_secret_privileged999").isFailure)
        assertTrue(SupabaseConfig.validate("http://xyzproj.supabase.co", validAnonJwt, allowInsecureLocalHttp = false).isFailure)
    }

    @Test
    fun apiClient_attachesBearerAuthorizationHeaderWhenSessionActive() {
        val authedHeaders = CatchLarpApiClient.buildBackendHeaders("eyJ.user.jwt", mapOf("Content-Type" to "application/json"))
        assertEquals("Bearer eyJ.user.jwt", authedHeaders["Authorization"])
        assertEquals("application/json", authedHeaders["Accept"])
        assertEquals("application/json", authedHeaders["Content-Type"])

        val unauthHeaders = CatchLarpApiClient.buildBackendHeaders("  ")
        assertNull(unauthHeaders["Authorization"])
    }
}
