package qa.load.sql.config

import java.util.Locale

/**
 * Load parameters, the same as `User Defined Variables` of `src/test/jmeter/sql_demo_test.jmx`
 * (`p-isStable`, `p-isMaxPerf`, `p-duration`, `p-tps`, `p-thread_count`, `p-title`, `p-testId`)
 * plus connection settings for running from IDE.
 */
data class LoadConfig(
    val isStable: Int,
    val isMaxPerf: Int,
    val durationSec: Long,
    val tps: Double,
    val threadCount: Int,
    val title: String,
    val testId: String,
    val dbHost: String,
    val dbPort: Int,
    val dbName: String,
    val dbPassword: String,
    val influxUrl: String,
    val influxEnabled: Boolean,
    val outputDir: String,
) {
    /** p-tpm: TPS -> TPM */
    val tpm: Double get() = tps * 60.0

    /** p-thread_count-stable */
    val stableThreads: Int get() = isStable * threadCount

    /** p-thread_count-maxperf */
    val maxPerfThreads: Int get() = isMaxPerf * threadCount

    fun jdbcUrl(applicationName: String): String =
        "jdbc:postgresql://$dbHost:$dbPort/$dbName?currentSchema=bookings&tcpKeepAlive=true&ApplicationName=$applicationName"

    /** testTitle of the Backend Listener: `${p-title} (Thread: ${p-thread_count}, TPS: ${p-tps}, Duration: ${p-duration})` */
    val influxTitle: String
        get() = "$title (Thread: $threadCount, TPS: ${prop("tps", formatTps(tps))}, Duration: $durationSec)"

    fun validate() {
        require(isStable == 1 || isMaxPerf == 1) {
            "Nothing to run: set -DisStable=1 and/or -DisMaxPerf=1 (or use Maven profile Stable / MaxPerf)"
        }
        require(threadCount > 0) { "thread_count must be > 0, actual: $threadCount" }
        require(tps > 0.0) { "tps must be > 0, actual: $tps" }
        if (isStable == 1) {
            require(durationSec > RAMP_UP_SEC) {
                "duration must be > $RAMP_UP_SEC seconds for Stable (ramp-up is $RAMP_UP_SEC s), actual: $durationSec"
            }
        }
        if (isMaxPerf == 1) {
            require(durationSec > 0) { "duration must be > 0 for MaxPerf, actual: $durationSec" }
        }
    }

    companion object {
        /** Ramp-up of Stable thread groups, `ThreadGroup.ramp_time` in jmx */
        const val RAMP_UP_SEC = 10L

        fun fromSystem(): LoadConfig {
            val influxHost = prop("influxdb.host", "sql_monitor_influxdb")
            val influxPort = prop("influxdb.port", "8086")
            val influxDatabase = prop("influxdb.database", "jmeter")
            val buildDir = prop("project.build.directory", "target")
            return LoadConfig(
                isStable = intProp("isStable", 0),
                isMaxPerf = intProp("isMaxPerf", 0),
                durationSec = prop("duration", "0").trim().toLong(),
                tps = prop("tps", "0.0").trim().toDouble(),
                threadCount = intProp("thread_count", 0),
                title = prop("title", ""),
                testId = prop("testId", System.currentTimeMillis().toString()),
                dbHost = prop("db.host", "sql_monitor_postgres"),
                dbPort = intProp("db.port", 5432),
                dbName = prop("db.name", "demo"),
                dbPassword = prop("db.password", "pass"),
                influxUrl = "http://$influxHost:$influxPort/write?db=$influxDatabase",
                influxEnabled = prop("influxdb.enabled", "true").trim().toBoolean(),
                outputDir = "$buildDir/jmeter-dsl",
            )
        }

        /** Empty values (unset Maven properties) are treated as absent. */
        fun prop(name: String, default: String): String =
            System.getProperty(name)?.takeUnless { it.isBlank() || it == "\${$name}" } ?: default

        private fun intProp(name: String, default: Int): Int = prop(name, default.toString()).trim().toInt()

        private fun formatTps(tps: Double): String = String.format(Locale.ROOT, "%s", tps)
    }
}
