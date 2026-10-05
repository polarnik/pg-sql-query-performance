package qa.load.sql

import qa.load.sql.config.LoadConfig
import qa.load.sql.dsl.influxListener
import qa.load.sql.dsl.pacing
import qa.load.sql.pools.Pools
import qa.load.sql.scenarios.QptTransaction
import us.abstracta.jmeter.javadsl.JmeterDsl.htmlReporter
import us.abstracta.jmeter.javadsl.JmeterDsl.jtlWriter
import us.abstracta.jmeter.javadsl.JmeterDsl.testPlan
import us.abstracta.jmeter.javadsl.JmeterDsl.threadGroup
import us.abstracta.jmeter.javadsl.core.DslTestPlan
import us.abstracta.jmeter.javadsl.core.DslTestPlan.TestPlanChild
import us.abstracta.jmeter.javadsl.core.threadgroups.BaseThreadGroup
import java.time.Duration

/**
 * Test plan:
 * - Stable (`-DisStable=1`): a thread group per scenario of [LoadProfile], rate = tps × multiplier;
 * - MaxPerf (`-DisMaxPerf=1`): one thread group, all enabled scenarios except qpt_transaction
 *   in each iteration, `tps` per thread;
 * - pool `DB_idle` without requests keeps "idle" connections.
 */
object SqlDemoPlan {

    fun threadGroups(cfg: LoadConfig): List<BaseThreadGroup<*>> {
        val rates = LoadProfile.rates(cfg)
        require(rates.isNotEmpty()) { "All scenarios are disabled in LoadProfile" }
        val ret = mutableListOf<BaseThreadGroup<*>>()

        if (cfg.isStable == 1) {
            rates.forEach { (scenario, tps) ->
                ret += threadGroup("Stable: ${scenario.id}")
                    .rampToAndHold(
                        cfg.stableThreads,
                        Duration.ofSeconds(LoadConfig.RAMP_UP_SEC),
                        Duration.ofSeconds(cfg.durationSec - LoadConfig.RAMP_UP_SEC),
                    )
                    .children(pacing(tps, perThread = false), scenario.tc())
            }
        }

        if (cfg.isMaxPerf == 1) {
            val scenarios = rates.map { it.first }.filter { it != QptTransaction }
            ret += threadGroup("MaxPerf")
                .rampTo(cfg.maxPerfThreads, Duration.ofSeconds(cfg.durationSec))
                .children(pacing(cfg.tps, perThread = true), *scenarios.map { it.tc() }.toTypedArray())
        }
        return ret
    }

    fun testPlan(cfg: LoadConfig, withReports: Boolean = true): DslTestPlan {
        cfg.validate()
        val children = mutableListOf<TestPlanChild>()
        children += Pools.all(cfg)
        children += threadGroups(cfg)
        if (cfg.influxEnabled) {
            children += influxListener(cfg)
        }
        if (withReports) {
            children += jtlWriter("${cfg.outputDir}/results", "sql_demo_test-${cfg.testId}.jtl")
            children += htmlReporter("${cfg.outputDir}/report", "sql_demo_test-${cfg.testId}")
        }
        return testPlan(*children.toTypedArray())
    }
}
