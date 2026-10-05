package qa.load.sql.dsl

import qa.load.sql.config.LoadConfig
import us.abstracta.jmeter.javadsl.core.listeners.InfluxDbBackendListener
import java.net.InetAddress

/**
 * Backend Listener InfluxDB with the same arguments as in `sql_demo_test.jmx`.
 *
 * `InfluxDbBackendListener.percentiles(float...)` writes `90.0;95.0;99.0` which changes
 * InfluxDB field names (`pct90.0` instead of `pct90`), so percentiles are set as a raw string.
 */
class PgInfluxDbListener(url: String, percentiles: String) : InfluxDbBackendListener(url) {
    init {
        name = "Backend Listener"
        this.percentiles = percentiles
    }
}

fun influxListener(cfg: LoadConfig): InfluxDbBackendListener {
    val listener = PgInfluxDbListener(cfg.influxUrl, "90;95;99")
    listener
        .application("postgresql demo database")
        .measurement("jmeter")
        .samplersRegex(".*")
        .title(cfg.influxTitle)
        .tag("testId", cfg.testId)
        .tag("generatorHost", machineName())
    return listener
}

/** The same as JMeter `${__machineName()}` */
private fun machineName(): String =
    try {
        InetAddress.getLocalHost().hostName
    } catch (e: Exception) {
        "unknown"
    }
