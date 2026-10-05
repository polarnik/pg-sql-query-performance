package qa.load.sql

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import qa.load.sql.config.LoadConfig
import java.io.File

/**
 * Load for monitoring checks, the same as `src/test/jmeter/sql_demo_test.jmx`.
 *
 * ```
 * mvn verify -P jmeter-dsl,Stable -Dtps=1.0
 * mvn verify -P jmeter-dsl,MaxPerf
 * mvn verify -P jmeter-dsl,Stable -Ddsl.exportOnly=true   # only save target/jmeter-dsl/sql_demo_test.dsl.jmx
 * ```
 */
class SqlDemoLoadTest {

    @Test
    fun sqlDemoLoad() {
        val cfg = LoadConfig.fromSystem()
        val plan = SqlDemoPlan.testPlan(cfg)

        if (LoadConfig.prop("dsl.exportOnly", "false").toBoolean()) {
            val jmx = File(cfg.outputDir, EXPORTED_JMX)
            jmx.parentFile.mkdirs()
            plan.saveAsJmx(jmx.path)
            println("Test plan saved to ${jmx.absolutePath}")
            return
        }

        println("Start: $cfg")
        val stats = plan.run()
        val overall = stats.overall()
        println(
            "Samples: ${overall.samplesCount()}, errors: ${overall.errorsCount()}, " +
                "duration: ${stats.duration()}, labels: ${stats.labels().size}"
        )
        stats.labels().sorted().forEach { label ->
            val s = stats.byLabel(label)
            println("  $label: samples=${s.samplesCount()} errors=${s.errorsCount()} p95=${s.sampleTime().perc95()}")
        }
        // as ignoreResultFailures=true in the jmeter profile: errors are reported, the load itself must happen
        assertThat(overall.samplesCount()).`as`("samples count").isGreaterThan(0)
    }

    companion object {
        const val EXPORTED_JMX = "sql_demo_test.dsl.jmx"
    }
}
