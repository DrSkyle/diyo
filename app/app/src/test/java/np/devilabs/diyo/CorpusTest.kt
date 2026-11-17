package np.devilabs.diyo

import org.junit.Assert.assertTrue
import org.junit.Assert.assertEquals
import org.junit.Test

class CorpusTest {
    @Test fun findsFarmingAdvice() {
        val hits = Corpus.search("धानको पात पहेँलो हुँदै गयो")
        assertTrue(hits.isNotEmpty())
        assertEquals("farming", hits[0].domain)
    }

    @Test fun findsEmergencyNumbers() {
        val hits = Corpus.search("नेपालमा एम्बुलेन्स नम्बर")
        assertTrue(hits.isNotEmpty())
        assertTrue(hits[0].text.contains("१०२"))
    }

    @Test fun emptyQueryReturnsNothing() {
        assertTrue(Corpus.search("के हो").isEmpty())
    }

    @Test fun groundPrefixesContext() {
        val g = Corpus.ground("सर्पले टोकेको छ")
        assertTrue(g.startsWith("सन्दर्भ:"))
        assertTrue(g.contains("चिर्नु"))
    }

    @Test fun groundedBrainIsHonestAndOffline() {
        val a = GroundedBrain.answer("भूकम्प आउँदा के गर्ने")
        assertTrue(a != null && a!!.contains("टेबलमुनि"))
    }
}
