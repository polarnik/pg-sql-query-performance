package qa.load.sql.scenarios

import qa.load.sql.dsl.autoCommitFalse
import qa.load.sql.dsl.callableSql
import qa.load.sql.dsl.commit
import qa.load.sql.pools.Pools
import us.abstracta.jmeter.javadsl.JmeterDsl.constantTimer
import us.abstracta.jmeter.javadsl.JmeterDsl.threadPause
import us.abstracta.jmeter.javadsl.JmeterDsl.transaction
import us.abstracta.jmeter.javadsl.core.controllers.DslTransactionController
import java.time.Duration

/**
 * `qpt_transaction (TC)`: BEGIN, SELECT, pause, COMMIT on one connection,
 * the connection is "idle in transaction" during the pause.
 *
 * SQL texts are copies of the jmx: `trimIndent()` removes only the code indentation,
 * trailing spaces and tabs inside the queries are kept on purpose (`query_md5` in telegraf).
 */
object QptTransaction : Scenario {
    override val id = "qpt_transaction"
    override val name = "qpt_transaction (TC)"

    /** Pause inside the transaction */
    const val WAIT_MS = 10000L

    override fun tc(): DslTransactionController = tc(WAIT_MS)

    fun tc(waitMs: Long): DslTransactionController = transaction(
        name,
        autoCommitFalse("transaction: AutoCommit(false)", Pools.QPT_TRANSACTION),
        callableSql("transaction: BEGIN", Pools.QPT_TRANSACTION, "BEGIN;"),
        callableSql("transaction: SELECT", Pools.QPT_TRANSACTION,
            """
            SELECT * 
            FROM aircrafts_data 
            WHERE range > 3000;
            """.trimIndent()),
        threadPause(Duration.ofMillis(1)).children(constantTimer(Duration.ofMillis(waitMs))),
        commit("transaction: COMMIT", Pools.QPT_TRANSACTION, "COMMIT;"),
    )
}
