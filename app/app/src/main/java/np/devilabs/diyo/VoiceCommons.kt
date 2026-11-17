package np.devilabs.diyo

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.util.UUID

/**
 * Consent-first contribution log (docs/VOICE-COMMONS.md).
 *
 * Nothing leaves the device by default. Each clip/text correction is stored locally with a scope
 * and a receipt id; upload is an explicit, revocable action handled later by a Nepal-hosted
 * endpoint. Scraping and silent collection are out of scope by design.
 */
object VoiceCommons {
    enum class Scope(val label: String) { LISTENING("A"), SPEAKING("B"), STYLE("C") }

    data class Receipt(val id: String, val scope: Scope, val kind: String, val path: String)

    fun donate(context: Context, source: File, scope: Scope): Receipt {
        val dir = File(context.filesDir, "commons/${scope.name.lowercase()}").also { it.mkdirs() }
        val dest = File(dir, source.name)
        source.copyTo(dest, overwrite = true)
        val receipt = Receipt(UUID.randomUUID().toString(), scope, if (source.extension == "wav") "audio" else "text", dest.absolutePath)
        append(context, receipt)
        return receipt
    }

    fun donateCorrection(context: Context, prompt: String, wrong: String, right: String): Receipt {
        val dir = File(context.filesDir, "commons/listening").also { it.mkdirs() }
        val f = File(dir, "correction-${System.currentTimeMillis()}.json")
        val obj = JSONObject().put("prompt", prompt).put("model", wrong).put("correct", right)
        f.writeText(obj.toString())
        val receipt = Receipt(UUID.randomUUID().toString(), Scope.LISTENING, "correction", f.absolutePath)
        append(context, receipt)
        return receipt
    }

    fun withdraw(context: Context, receiptId: String): Boolean {
        val log = logFile(context)
        if (!log.exists()) return false
        val arr = JSONArray(log.readText())
        val kept = JSONArray()
        var removed = false
        for (i in 0 until arr.length()) {
            val o = arr.getJSONObject(i)
            if (o.getString("id") == receiptId) {
                File(o.getString("path")).delete()
                removed = true
            } else kept.put(o)
        }
        log.writeText(kept.toString())
        return removed
    }

    fun receipts(context: Context): List<String> {
        val log = logFile(context)
        if (!log.exists()) return emptyList()
        val arr = JSONArray(log.readText())
        return (0 until arr.length()).map { arr.getJSONObject(it).getString("id") }
    }

    private fun logFile(context: Context) = File(context.filesDir, "commons/receipts.json")
    private fun append(context: Context, r: Receipt) {
        val log = logFile(context)
        log.parentFile?.mkdirs()
        val arr = if (log.exists()) JSONArray(log.readText()) else JSONArray()
        arr.put(JSONObject().put("id", r.id).put("scope", r.scope.name).put("kind", r.kind).put("path", r.path).put("ts", System.currentTimeMillis()))
        log.writeText(arr.toString())
    }
}
