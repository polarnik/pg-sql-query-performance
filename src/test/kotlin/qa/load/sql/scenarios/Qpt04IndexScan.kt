package qa.load.sql.scenarios

import qa.load.sql.dsl.preparedSql
import qa.load.sql.dsl.sql
import qa.load.sql.pools.Pools
import us.abstracta.jmeter.javadsl.JmeterDsl.transaction
import us.abstracta.jmeter.javadsl.core.controllers.DslTransactionController

/**
 * `qpt_04_indexscan (TC)`.
 * https://edu.postgrespro.ru/qpt/qpt_04_indexscan.html
 *
 * SQL texts are copies of the jmx: `trimIndent()` removes only the code indentation,
 * trailing spaces and tabs inside the queries are kept on purpose (`query_md5` in telegraf).
 */
object Qpt04IndexScan : Scenario {
    override val id = "qpt_04_indexscan"
    override val name = "qpt_04_indexscan (TC)"

    override fun tc(): DslTransactionController = transaction(
        name,
        sql("qpt_04_indexscan: поиск одного значения", Pools.QPT_04, "SELECT * FROM bookings WHERE book_ref = '0009D5';"),
        preparedSql("qpt_04_indexscan: с условием, которого нет в индексе", Pools.QPT_04,
            """
            SELECT * FROM bookings 
              WHERE book_ref = '0009D5' AND total_amount > ?;
            """.trimIndent(), "\${__Random(1000,5000,)}" to "INTEGER"),
    )
}
