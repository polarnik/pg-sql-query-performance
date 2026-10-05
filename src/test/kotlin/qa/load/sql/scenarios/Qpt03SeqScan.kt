package qa.load.sql.scenarios

import qa.load.sql.dsl.sql
import qa.load.sql.pools.Pools
import us.abstracta.jmeter.javadsl.JmeterDsl.transaction
import us.abstracta.jmeter.javadsl.core.controllers.DslTransactionController

/**
 * `qpt_03_seqscan (TC)`.
 * https://edu.postgrespro.ru/qpt/qpt_03_seqscan.html
 *
 * SQL texts are copies of the jmx: `trimIndent()` removes only the code indentation,
 * trailing spaces and tabs inside the queries are kept on purpose (`query_md5` in telegraf).
 */
object Qpt03SeqScan : Scenario {
    override val id = "qpt_03_seqscan"
    override val name = "qpt_03_seqscan (TC)"

    override fun tc(): DslTransactionController = transaction(
        name,
        sql("qpt_03_seqscan: Последовательное сканирование", Pools.QPT_03, "SELECT * FROM flights;"),
        sql("qpt_03_seqscan: Агрегация", Pools.QPT_03, "SELECT count(*) FROM seats;"),
        sql("qpt_03_seqscan: Параллельное последовательное сканирование", Pools.QPT_03, "SELECT count(*) FROM bookings;"),
    )
}
