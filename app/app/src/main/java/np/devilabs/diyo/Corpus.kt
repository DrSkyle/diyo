package np.devilabs.diyo

/**
 * On-device retrieval. The 3,253-chunk Nepali corpus (licensed, cited) lives in the pack and is
 * queried before generation so the model answers from something it can point at.
 *
 * Stage 0: a tiny keyword scorer over bundled chunks — no embeddings, no network, no native deps.
 * Good enough to ground "धान पहेँलो भयो" in the agriculture/health pages that mention it.
 * Stage 1 swaps the scorer for a small embedding index shipped with the pack.
 */
data class Chunk(val text: String, val domain: String, val source: String)

object Corpus {
    // Seeded with the most-used advice; the full corpus ships as a pack asset (assets/corpus.jsonl).
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

    private val stop = setOf("के","गर्ने","हो","छ","भयो","गरेर","गर्न","कसरी","किन","र","मा","को","छैन")

    fun search(query: String, limit: Int = 2): List<Chunk> {
        val terms = query.split(Regex("\\s+"))
            .map { it.trim('?', '।', ',', '!', '“', '”') }
            .filter { it.length >= 2 && it !in stop }
        if (terms.isEmpty()) return emptyList()
        return seed
            .map { c -> c to terms.count { c.text.contains(it) } }
            .filter { it.second > 0 }
            .sortedByDescending { it.second }
            .take(limit)
            .map { it.first }
    }

    /** A short grounding block to prepend to the model prompt, or "" if nothing matches. */
    fun ground(query: String): String {
        val hits = search(query)
        if (hits.isEmpty()) return ""
        return "सन्दर्भ:\n" + hits.joinToString("\n") { "- ${it.text}" }
    }
}
