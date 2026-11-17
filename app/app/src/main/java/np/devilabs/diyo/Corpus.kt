package np.devilabs.diyo

import android.content.Context
import org.json.JSONObject
import java.io.BufferedReader

/**
 * On-device retrieval over the licensed Nepali corpus (3,253 chunks).
 *
 * Loaded lazily from assets/corpus.jsonl (shipped in the APK) so answers are grounded in cited
 * text before generation. Stage 0 scorer: keyword overlap, no embeddings, no network. Good enough
 * to pull the right health/agri/paperwork paragraph for a short Nepali question.
 */
data class Chunk(val text: String, val domain: String, val source: String)

object Corpus {
    @Volatile private var loaded: List<Chunk>? = null

    private val stop = setOf(
        "के","गर्ने","हो","छ","भयो","भए","गरेर","गर्न","कसरी","किन","र","मा","को","छैन",
        "होला","पर्छ","गर्नुहोस्","भने","लागि","एउटा","मलाई","मेरो","तपाईं"
    )

    fun ensureLoaded(context: Context) {
        if (loaded != null) return
        synchronized(this) {
            if (loaded != null) return
            loaded = try {
                context.assets.open("corpus.jsonl").bufferedReader().use { br ->
                    val out = ArrayList<Chunk>(3500)
                    br.lineSequence().forEach { line ->
                        if (line.isBlank()) return@forEach
                        try {
                            val o = JSONObject(line)
                            val text = o.optString("text")
                            if (text.length > 30) {
                                out.add(Chunk(text, o.optString("domain","general"), o.optString("source","")))
                            }
                        } catch (_: Throwable) { }
                    }
                    out
                }
            } catch (_: Throwable) {
                seed
            }
        }
    }

    private fun data(context: Context? = null): List<Chunk> {
        if (context != null) ensureLoaded(context)
        return loaded ?: seed
    }

    fun search(query: String, limit: Int = 2, context: Context? = null): List<Chunk> {
        val terms = terms(query)
        if (terms.isEmpty()) return emptyList()
        val pool = data(context)
        val scored = ArrayList<Pair<Chunk, Int>>(limit * 4)
        for (c in pool) {
            var s = 0
            for (t in terms) if (c.text.contains(t)) s++
            if (s > 0) scored.add(c to s)
        }
        return scored.sortedByDescending { it.second }.take(limit).map { it.first }
    }

    /** Grounding block to prepend to the prompt, or "" if nothing relevant matches. */
    fun ground(query: String, context: Context? = null): String {
        val hits = search(query, 2, context)
        if (hits.isEmpty()) return ""
        return "सन्दर्भ:\n" + hits.joinToString("\n") { "- ${it.text.take(420)}" }
    }

    private fun terms(query: String): List<String> = query.split(Regex("\\s+"))
        .map { it.trim('?', '।', ',', '!', '“', '”', '"', '(', ')', ':', '-') }
        .filter { it.length >= 2 && it !in stop }

    // Tiny fallback so the class works in plain JVM tests without an Android context/assets.
    private val seed = listOf(
        Chunk("धानको पात पहेँलो। खेतमा पानी जमेको छ भने निकास गर्नुहोस्। पातको टुप्पो पहेँलो छ भने नाइट्रोजन कम हुन सक्छ; नमुना लिएर कृषि प्राविधिकलाई देखाउनुहोस्।", "farming", "corpus"),
        Chunk("ज्वरो तीन दिनभन्दा बढी भए वा बच्चाले नखाए आजै स्वास्थ्य चौकी जानुहोस्। दिनमा धेरै पटक झोल र जीवनजल दिनुहोस्; बाक्लो कम्बलमा नबेर्नुहोस्।", "health", "corpus"),
        Chunk("दिसा पातलो भए हरेक दिसापछि जीवनजल दिनुहोस्। आँखा धसिए, पिसाब कम भए वा सुस्त भए तुरुन्तै स्वास्थ्य चौकी जानुहोस्।", "health", "corpus"),
        Chunk("सर्पले टोकेको छ भने टोकेको ठाउँ चिर्नु, चुस्नु वा डोरीले बाँध्नु हुँदैन। बिरामीलाई शान्त राखेर तुरुन्तै अस्पताल लैजानुहोस्।", "health", "corpus"),
        Chunk("भूकम्प आउँदा भुइँमा ढल्किनुहोस् र टेबलमुनि टाउको छोप्नुहोस्। हल्लिन छाडेपछि खुला ठाउँमा जानुहोस्।", "daily", "corpus"),
        Chunk("नेपालको राजधानी काठमाडौं हो। प्रहरी १००, एम्बुलेन्स १०२, दमकल १०१।", "daily", "corpus"),
        Chunk("नागरिकतामा जन्म मिति गलत भए जन्म दर्ता प्रमाणपत्र र निवेदनसहित जिल्ला प्रशासन कार्यालय जानुहोस्; वडा सिफारिस मागिन्छ।", "paperwork", "corpus"),
        Chunk("ज्याला नदिए काम गरेको प्रमाण राखेर श्रम कार्यालय वा वडा कार्यालयमा उजुरी दिनुहोस्।", "legal", "corpus")
    )
}
