package qa.load.sql.scenarios

import qa.load.sql.dsl.callableSql
import qa.load.sql.dsl.sql
import qa.load.sql.pools.Pools
import us.abstracta.jmeter.javadsl.JmeterDsl.transaction
import us.abstracta.jmeter.javadsl.core.controllers.DslTransactionController

/**
 * `qpt_05_bitmapscan (TC)`.
 * https://edu.postgrespro.ru/qpt/qpt_05_bitmapscan.html
 *
 * SQL texts are copies of the jmx: `trimIndent()` removes only the code indentation,
 * trailing spaces and tabs inside the queries are kept on purpose (`query_md5` in telegraf).
 */
object Qpt05BitmapScan : Scenario {
    override val id = "qpt_05_bitmapscan"
    override val name = "qpt_05_bitmapscan (TC)"

    /** qpt_05_bitmapscan: Сканирование по битовой карте */
    const val SQL_1 =
        "SELECT * FROM bookings WHERE total_amount < 10000;"

    override fun tc(): DslTransactionController = transaction(
        name,
        sql("qpt_05_bitmapscan: Сканирование по битовой карте", Pools.QPT_05, SQL_1),
        callableSql("qpt_05_bitmapscan: Использование памяти", Pools.QPT_05,
            """
            SET work_mem = '64kB';
            SELECT * FROM bookings WHERE total_amount < 10000;
            RESET work_mem;
            """.trimIndent()),
        callableSql("qpt_05_bitmapscan: Объединение битовых карт", Pools.QPT_05,
            """
            SELECT * FROM bookings
              WHERE total_amount < 10000 OR total_amount > 100000;
            """.trimIndent()),
        callableSql("qpt_05_bitmapscan: Объединение битовых карт 2", Pools.QPT_05,
            """
            |  SELECT * FROM bookings
            |  WHERE total_amount < 10000
            |     OR book_date = bookings.now() - INTERVAL '1 day';
            """.trimMargin()),
        callableSql("qpt_05_bitmapscan: Кластеризация", Pools.QPT_05, "SELECT * FROM bookings LIMIT 10;"),
        callableSql("qpt_05_bitmapscan: Кластеризация 2", Pools.QPT_05, SQL_1),
        callableSql("qpt_05_bitmapscan: Параллельное сканирование по битовой карте", Pools.QPT_05,
            """
            SELECT 
            	count(*) 
            FROM bookings 
            WHERE book_date > bookings.now() - INTERVAL '2 months';
            """.trimIndent()),
    )
}
