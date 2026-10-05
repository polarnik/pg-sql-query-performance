package qa.load.sql.dsl

import us.abstracta.jmeter.javadsl.JmeterDsl.threadPause
import us.abstracta.jmeter.javadsl.JmeterDsl.throughputTimer
import us.abstracta.jmeter.javadsl.core.samplers.DslFlowControlAction
import us.abstracta.jmeter.javadsl.core.timers.DslThroughputTimer.ThroughputMode
import java.time.Duration

/**
 * Pacing at the start of every iteration: an empty pause with a Constant Throughput Timer.
 * The timer is scoped to the pause, so there is exactly one delay per iteration
 * (not one per every JDBC request).
 *
 * @param tps transactions per second
 * @param perThread `false` -> `tps` for the whole thread group (Stable),
 *                  `true`  -> `tps` for every thread (MaxPerf)
 */
fun pacing(tps: Double, perThread: Boolean): DslFlowControlAction {
    val mode = if (perThread) ThroughputMode.PER_THREAD else ThroughputMode.THREAD_GROUP_EVEN
    return threadPause(Duration.ZERO).children(throughputTimer(tps * 60.0).calculation(mode))
}
