package np.devilabs.diyo

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class SayTest {

    @Test
    fun smallNumbersAreSpoken() {
        assertEquals("बाह्र", Say.words(12))
        assertEquals("पन्ध्र", Say.words(15))
        assertEquals("शून्य", Say.words(0))
        assertEquals("उनान्सय", Say.words(99))
    }

    @Test
    fun hundredsAndThousandsCompose() {
        assertEquals("एक सय", Say.words(100))
        assertEquals("एक सय चालिस", Say.words(140))
        assertEquals("एक हजार एक सय चालिस", Say.words(1140))
        assertEquals("दुई हजार", Say.words(2000))
    }

    @Test
    fun devanagariDigitsAreExpanded() {
        assertEquals("बाह्र केजी", Say.expandNumbers("१२ केजी"))
        assertEquals("एक हजार एक सय चालिस रुपैयाँ", Say.expandNumbers("११४० रुपैयाँ"))
    }

    @Test
    fun asciiDigitsAreExpandedToo() {
        assertEquals("एक सय पच्चीस", Say.expandNumbers("125"))
    }

    @Test
    fun commasAreHandled() {
        assertEquals("पाँच हजार", Say.expandNumbers("5,000"))
    }

    @Test
    fun markdownIsStripped() {
        val out = Say.prepareForSpeech("**ज्वरो** आएको छ।\n- पानी दिनुहोस्।\n- आराम गर्नुहोस्।")
        assertTrue(!out.contains("*"))
        assertTrue(!out.contains("-"))
        assertTrue(out.contains("पानी"))
    }

    @Test
    fun longAnswersAreCutForSpeech() {
        val six = "एक। दुई। तीन। चार। पाँच। छ।"
        assertEquals(4, Say.sentences(Say.prepareForSpeech(six)).size)
    }

    @Test
    fun shortAnswersSurviveIntact() {
        val two = "पानी दिनुहोस्। आजै स्वास्थ्य चौकी जानुहोस्।"
        assertEquals(two, Say.prepareForSpeech(two))
    }

    @Test
    fun fullPipelineExpandsNumbersAfterTrimming() {
        val out = Say.forSpeech("दिनको २ पटक दिनुहोस्। ३ दिनसम्म।")
        assertTrue(out.contains("दुई पटक"))
        assertTrue(!out.contains("२"))
    }
}
