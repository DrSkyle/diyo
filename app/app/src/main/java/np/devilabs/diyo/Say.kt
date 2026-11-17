package np.devilabs.diyo

/**
 * Everything between "the model produced text" and "the phone speaks it".
 *
 * Two jobs that the model must not be trusted with:
 *  - numbers: TTS reads digits badly and inconsistently in Nepali, so १२ becomes बाह्र
 *  - shape: a spoken answer is 2-4 sentences. Lists and markdown are unreadable aloud.
 */
object Say {

    private val UNITS = arrayOf(
        "शून्य", "एक", "दुई", "तीन", "चार", "पाँच", "छ", "सात", "आठ", "नौ",
        "दस", "एघार", "बाह्र", "तेह्र", "चौध", "पन्ध्र", "सोह्र", "सत्र", "अठार", "उन्नाइस",
        "बीस", "एक्काइस", "बाइस", "तेइस", "चौबीस", "पच्चीस", "छब्बीस", "सत्ताइस", "अठ्ठाइस", "उनन्तिस",
        "तीस", "एकत्तिस", "बत्तिस", "तेत्तिस", "चौँतिस", "पैँतिस", "छत्तिस", "सैँतिस", "अठतिस", "उनन्चालिस",
        "चालिस", "एकचालिस", "बयालिस", "त्रिचालिस", "चवालिस", "पैँतालिस", "छयालिस", "सतचालिस", "अठचालिस", "उनन्चास",
        "पचास", "एकाउन्न", "बाउन्न", "त्रिपन्न", "चौवन्न", "पचपन्न", "छपन्न", "सन्ताउन्न", "अन्ठाउन्न", "उनन्साठी",
        "साठी", "एकसट्ठी", "बयसट्ठी", "त्रिसट्ठी", "चौंसट्ठी", "पैंसट्ठी", "छयसट्ठी", "सतसट्ठी", "अठसट्ठी", "उनन्सत्तरी",
        "सत्तरी", "एकहत्तर", "बहत्तर", "त्रिहत्तर", "चौहत्तर", "पचहत्तर", "छयहत्तर", "सतहत्तर", "अठहत्तर", "उनासी",
        "असी", "एकासी", "बयासी", "त्रियासी", "चौरासी", "पचासी", "छयासी", "सतासी", "अठासी", "उनान्नब्बे",
        "नब्बे", "एकानब्बे", "बयानब्बे", "त्रियानब्बे", "चौरानब्बे", "पन्चानब्बे", "छयानब्बे", "सन्तानब्बे",
        "अन्ठानब्बे", "उनान्सय")

    /** 0..99 as spoken Nepali. */
    fun wordsUnder100(n: Int): String = when {
        n in 0..99 -> UNITS[n]
        else -> throw IllegalArgumentException("expected 0..99, got $n")
    }

    /** Any non-negative integer as spoken Nepali, with सय / हजार composition. */
    fun words(n: Long): String {
        if (n < 0) return "ऋणात्मक " + words(-n)
        if (n < 100) return wordsUnder100(n.toInt())
        if (n < 1000) {
            val hundreds = n / 100
            val rest = n % 100
            val head = wordsUnder100(hundreds.toInt()) + " सय"
            return if (rest == 0L) head else "$head ${wordsUnder100(rest.toInt())}"
        }
        if (n < 100_000) {
            val thousands = n / 1000
            val rest = n % 1000
            val head = words(thousands) + " हजार"
            return if (rest == 0L) head else "$head ${words(rest)}"
        }
        if (n < 10_000_000) {
            val lakhs = n / 100_000
            val rest = n % 100_000
            val head = words(lakhs) + " लाख"
            return if (rest == 0L) head else "$head ${words(rest)}"
        }
        val crores = n / 10_000_000
        val rest = n % 10_000_000
        val head = words(crores) + " करोड"
        return if (rest == 0L) head else "$head ${words(rest)}"
    }

    private val DEV_DIGITS = "०१२३४५६७८९"
    private val NUMBER = Regex("[०-९0-9][०-९0-9,]*")

    /** Rewrite every number in the text the way it should be spoken. */
    fun expandNumbers(text: String): String = NUMBER.replace(text) { m ->
        val raw = m.value.replace(",", "")
        val normalised = raw.map { c ->
            val i = DEV_DIGITS.indexOf(c)
            if (i >= 0) ('0' + i) else c
        }.joinToString("")
        val value = normalised.toLongOrNull()
        if (value == null || normalised.length > 9) m.value else words(value)
    }

    private val MARKDOWN = Regex("(?m)^\\s*(?:[-*•]|\\d+\\.)\\s+|\\*\\*|__|`|^#{1,6}\\s+")
    private val SENTENCE = Regex("[^।!?]+[।!?]?")

    fun sentences(text: String): List<String> =
        SENTENCE.findAll(text).map { it.value.trim() }.filter { it.isNotEmpty() }.toList()

    /** Keep the answer speakable: no markdown, no lists, at most [max] sentences. */
    fun prepareForSpeech(text: String, max: Int = 4): String {
        var t = text.replace(MARKDOWN, " ")
        t = t.replace(Regex("\\s+"), " ").trim()
        val s = sentences(t)
        val kept = if (s.size <= max) s else s.take(max)
        return kept.joinToString(" ").trim()
    }

    /** The full pipeline the app runs before handing text to TTS. */
    fun forSpeech(modelText: String): String = expandNumbers(prepareForSpeech(modelText))
}
