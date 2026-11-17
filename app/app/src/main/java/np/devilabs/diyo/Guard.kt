package np.devilabs.diyo

/**
 * Pre-generation guard, ported from pipeline/guard.py so the app and the eval agree.
 *
 * Four request shapes never reach the model: harm to a person, self-harm, a medicine or
 * pesticide dose, and poisoning. Identity questions are answered here too, so the base model's
 * pretraining voice can never leak into the product.
 */
object Guard {

    private val HARM = Regex(
        "(छिमेकी|मान्छे|मानिस|श्रीमान|श्रीमती|बुबा|आमा|सासू|बच्चा|कसैलाई|उसलाई|उनलाई)" +
            "[^।?!]{0,30}" +
            "(मार्न|मार्ने|हानि|हत्या|घाउ|पुर्‍याउन|पुर्‍याउने|जलाउन|विष दिन)",
        RegexOption.IGNORE_CASE)

    private val SELF = Regex("(आत्महत्या|आफूलाई मार्न|आफ्नै ज्यान|ज्यान लिन)", RegexOption.IGNORE_CASE)

    private val DOSE = Regex(
        "(?:औषधि|औषध|विषादी|विष|युरिया|डीएपी|पोटास|कीटनाशक|पेस्टिसाइड|(?<!चा)(?<!ता)मल(?!ा|ि|ु|े|ो))" +
            "[^।?!]{0,30}" +
            "(?:कति|मात्रा|मिलिग्राम|मिलीग्राम|चक्की|ml|मिली|केजी|हाल्ने|खाने|दिने)",
        RegexOption.IGNORE_CASE)

    private val TOXIC = Regex("(विष हालेर|विष खान|जहर|सल्फास|कीटनाशक खान)", RegexOption.IGNORE_CASE)

    /** Insects are not people: "कीरा मार्ने" is legitimate farming. */
    private val BENIGN = Regex(
        "(कीरा|किरा|माहुरी|झिंगा|लामखुट्टे|मुसा|सर्प)[^।?!]{0,12}मार्न", RegexOption.IGNORE_CASE)

    private val IDENTITY_Q = Regex(
        "(?:तिमी को|तपाईं को|तिम्रो नाम|तपाईंको नाम|तिमी के हो|तपाईं के हो|" +
            "के तिमी (?:एआई|AI|मोडेल)|के तपाईं (?:एआई|AI|मोडेल)|who are you)",
        RegexOption.IGNORE_CASE)

    private val ORIGIN_Q = Regex(
        "(?:कसले तालिम|कुन मोडेल|कसले बनायो|तिमीलाई कसले|तपाईंलाई कसले|" +
            "गुगलले|Google ले|google ले|openai|ओपनएआई|base model|आधार मोडेल|" +
            "(?:तिमी|तपाईं)[^।?!]{0,20}(?:google|गुगल))",
        RegexOption.IGNORE_CASE)

    const val EMERGENCY = "प्रहरी १००, एम्बुलेन्स १०२"

    val HARM_ANSWER = "म यसमा सहयोग गर्न सक्दिन। कसैलाई हानि पुर्‍याउनु गैरकानुनी हो र त्यसले जीवन बिगार्छ। " +
        "धम्की वा झगडा भइरहेको छ भने नजिकको प्रहरी कार्यालय वा वडा कार्यालयमा जानुहोस्। " +
        "आपत्कालीन अवस्थामा $EMERGENCY मा फोन गर्नुहोस्।"

    val SELF_ANSWER = "तपाईं अहिले धेरै गाह्रो अनुभव गरिरहनुभएको जस्तो लाग्छ, र त्यो एक्लै बोक्नु पर्दैन। " +
        "कृपया अहिले कसैलाई भन्नुहोस् — परिवार, नजिकको साथी, वा स्वास्थ्यकर्मी। " +
        "तुरुन्त सहयोग चाहिए $EMERGENCY मा फोन गर्नुहोस् वा नजिकको अस्पताल जानुहोस्।"

    val DOSE_ANSWER = "औषधि वा विषादीको मात्रा म भन्न सक्दिन, गलत मात्राले गम्भीर हानि गर्छ। " +
        "प्याकेटको लेबलमा लेखेको कुरा पढ्नुहोस्, र डाक्टर वा कृषि प्राविधिकले भनेको मात्र पालना गर्नुहोस्। " +
        "शंका भए नजिकको स्वास्थ्य चौकी वा कृषि ज्ञान केन्द्रमा सोध्नुहोस्।"

    val TOXIC_ANSWER = "विष वा कीटनाशक खाएको वा हालेको भए तुरुन्त अस्पताल जानुहोस्। " +
        "बिरामीलाई जबरजस्ती उल्टी गराउने प्रयास नगर्नुहोस्, र बोतल वा प्याकेट साथै लिएर जानुहोस्। " +
        "एम्बुलेन्स १०२ मा फोन गर्नुहोस्।"

    val IDENTITY_ANSWER = "म दियो हुँ, Devilabs ले नेपालका लागि बनाएको सहायक। " +
        "इन्टरनेट नभए पनि फोनभित्रै जवाफ दिन्छु। बाली, कागजात, स्वास्थ्य र दैनिक काममा सोध्नुहोस्।"

    val ORIGIN_ANSWER = "म दियो हुँ, Devilabs ले नेपालका लागि बनाएको सहायक। " +
        "खुला नेपाली मोडेलमा आधारित भए पनि नेपाली बोली, सुरक्षा र सन्दर्भका लागि यसलाई Devilabs ले नै " +
        "तालिम दिएको हो। इन्टरनेट नभए पनि फोनभित्रै चल्छु।"

    /** Returns a fixed Nepali answer, or null when the request may reach the model. */
    fun check(prompt: String?): String? {
        val text = prompt ?: return null
        if (BENIGN.containsMatchIn(text)) return null
        if (SELF.containsMatchIn(text)) return SELF_ANSWER
        if (TOXIC.containsMatchIn(text)) return TOXIC_ANSWER
        if (HARM.containsMatchIn(text)) return HARM_ANSWER
        if (DOSE.containsMatchIn(text)) return DOSE_ANSWER
        if (ORIGIN_Q.containsMatchIn(text)) return ORIGIN_ANSWER
        if (IDENTITY_Q.containsMatchIn(text)) return IDENTITY_ANSWER
        return null
    }
}
