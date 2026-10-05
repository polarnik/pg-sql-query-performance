package qa.load.sql.scenarios

import qa.load.sql.dsl.sql
import qa.load.sql.pools.Pools
import us.abstracta.jmeter.javadsl.JmeterDsl.transaction
import us.abstracta.jmeter.javadsl.core.controllers.DslTransactionController

/**
 * `qpt_11_technics (TC)`.
 * https://edu.postgrespro.ru/qpt/qpt_11_technics.html
 *
 * SQL texts are copies of the jmx: `trimIndent()` removes only the code indentation,
 * trailing spaces and tabs inside the queries are kept on purpose (`query_md5` in telegraf).
 */
object Qpt11Technics : Scenario {
    override val id = "qpt_11_technics"
    override val name = "qpt_11_technics (TC)"

    /** qpt_11_technics: Пример оптимизации запроса */
    val SQL_1 =
        """
        SELECT a.aircraft_code, (
          SELECT round(avg(tf.amount))
          FROM flights f 
            JOIN ticket_flights tf ON tf.flight_id = f.flight_id 
          WHERE f.aircraft_code = a.aircraft_code 
            AND tf.amount > (SELECT min(amount) FROM ticket_flights) 
            AND tf.amount < (SELECT max(amount) FROM ticket_flights) 
        ) 
        FROM aircrafts a 
        GROUP BY a.aircraft_code
        LIMIT 1000;
        """.trimIndent()

    override fun tc(): DslTransactionController = transaction(
        name,
        sql("qpt_11_technics: Пример оптимизации запроса", Pools.QPT_11, SQL_1),
        sql("qpt_11_technics: Пример оптимизации запроса REPEATABLE_READ", Pools.QPT_11_REPEATABLE_READ, SQL_1),
    )
}
