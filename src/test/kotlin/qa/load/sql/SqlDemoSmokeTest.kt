package qa.load.sql

import org.assertj.core.api.Assertions.assertThat
import org.assertj.core.api.SoftAssertions
import org.junit.jupiter.api.Test
import qa.load.sql.config.LoadConfig
import qa.load.sql.pools.Pools
import qa.load.sql.scenarios.QptTransaction
import us.abstracta.jmeter.javadsl.JmeterDsl.testPlan
import us.abstracta.jmeter.javadsl.JmeterDsl.threadGroup
import us.abstracta.jmeter.javadsl.core.DslTestPlan.TestPlanChild

/**
 * Every transaction of the load test is executed once by one thread, all requests must succeed.
 *
 * ```
 * docker compose up -d db
 * mvn -P jmeter-dsl test -Dtest=SqlDemoSmokeTest -Ddb.host=localhost -Dinfluxdb.enabled=false
 * ```
 */
class SqlDemoSmokeTest {

    @Test
    fun everyQueryRunsWithoutErrors() {
        val cfg = LoadConfig.fromSystem().copy(
            isStable = 1,
            isMaxPerf = 0,
            durationSec = 60,
            tps = 1.0,
            threadCount = 1,
            influxEnabled = false,
        )
        val groups = LoadProfile.stable.map { (scenario, _) ->
            val tc = if (scenario == QptTransaction) QptTransaction.tc(SMOKE_WAIT_MS) else scenario.tc()
            threadGroup("Smoke: ${scenario.id}", 1, 1, tc)
        }

        val children = mutableListOf<TestPlanChild>()
        children += Pools.all(cfg)
        children += groups
        val stats = testPlan(*children.toTypedArray()).run()

        val soft = SoftAssertions()
        stats.labels().sorted().forEach { label ->
            val s = stats.byLabel(label)
            println("$label: samples=${s.samplesCount()} errors=${s.errorsCount()}")
            soft.assertThat(s.errorsCount()).`as`("errors of '%s'", label).isZero()
            soft.assertThat(s.samplesCount()).`as`("samples of '%s'", label).isEqualTo(1L)
        }
        soft.assertAll()
        assertThat(stats.overall().errorsCount()).`as`("errors").isZero()
        assertThat(stats.labels()).`as`("labels: JDBC requests + transactions")
            .hasSize(JDBC_REQUESTS + TRANSACTIONS)
    }

    companion object {
        /** 3 + 2 + 7 + 7 + 5 + 6 + 2 + 2 qpt requests and 4 requests of qpt_transaction */
        const val JDBC_REQUESTS = 38

        /** qpt_03..qpt_11 (8) and qpt_transaction */
        const val TRANSACTIONS = 9

        const val SMOKE_WAIT_MS = 1000L
    }
}
