package qa.load.sql

import qa.load.sql.config.LoadConfig
import qa.load.sql.scenarios.Qpt03SeqScan
import qa.load.sql.scenarios.Qpt04IndexScan
import qa.load.sql.scenarios.Qpt05BitmapScan
import qa.load.sql.scenarios.Qpt06NestLoop
import qa.load.sql.scenarios.Qpt07HashJoin
import qa.load.sql.scenarios.Qpt08MergeJoin
import qa.load.sql.scenarios.Qpt10Profiling
import qa.load.sql.scenarios.Qpt11Technics
import qa.load.sql.scenarios.QptTransaction
import qa.load.sql.scenarios.Scenario

/**
 * THE place to set load intensity.
 *
 * Every scenario runs in its own thread group, one iteration = one transaction (all its queries once).
 * Rate of a scenario = `-Dtps` × multiplier, transactions per second for the whole thread group:
 *
 * - `1.0` = the same as `sql_demo_test.jmx` (all scenarios get `-Dtps`);
 * - `0.1` = 10 times less often, `5.0` = 5 times more often;
 * - `0`   = scenario is disabled.
 *
 * A multiplier can be overridden without editing the code: `-Drate.qpt_11_technics=0.1`.
 *
 * The upper bound is `thread_count / transaction time`: e.g. qpt_11 (~0.5 s) with 50 threads
 * cannot go faster than ~100 TPS, qpt_transaction (10 s pause) not faster than 5 TPS.
 *
 * MaxPerf runs all scenarios with multiplier > 0 one after another in each iteration.
 */
object LoadProfile {

    val stable: List<Pair<Scenario, Double>> = listOf(
        //  scenario             multiplier     queries, mean time of a query in pg_stat_statements
        Qpt03SeqScan        to 1.0,     //  3 queries, ~10 ms
        Qpt04IndexScan      to 1.0,     //  2 queries, < 1 ms
        Qpt05BitmapScan     to 1.0,     //  7 queries, ~20 ms
        Qpt06NestLoop       to 1.0,     //  7 queries, ~3 ms
        Qpt07HashJoin       to 1.0,     //  5 queries, < 1 ms
        Qpt08MergeJoin      to 1.0,     //  6 queries, ~12 ms
        Qpt10Profiling      to 1.0,     //  2 queries, ~40 ms, report() runs more queries inside
        Qpt11Technics       to 1.0,     //  2 queries, ~470 ms, the heaviest
        QptTransaction      to 1.0,     //  BEGIN, SELECT, 10 s "idle in transaction", COMMIT
    )

    /** Multiplier with `-Drate.<id>` override applied */
    fun multiplier(scenario: Scenario, default: Double): Double =
        LoadConfig.prop("rate.${scenario.id}", default.toString()).trim().toDouble()

    /** Scenarios to run with their rate in transactions per second, disabled ones are dropped */
    fun rates(cfg: LoadConfig): List<Pair<Scenario, Double>> =
        stable
            .map { (scenario, default) -> scenario to cfg.tps * multiplier(scenario, default) }
            .filter { (_, tps) -> tps > 0.0 }
}
