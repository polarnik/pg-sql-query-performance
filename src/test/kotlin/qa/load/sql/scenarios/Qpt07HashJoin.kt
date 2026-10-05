package qa.load.sql.scenarios

import qa.load.sql.dsl.callableSql
import qa.load.sql.pools.Pools
import us.abstracta.jmeter.javadsl.JmeterDsl.transaction
import us.abstracta.jmeter.javadsl.core.controllers.DslTransactionController

/**
 * `qpt_07_hashjoin (TC)`.
 * https://edu.postgrespro.ru/qpt/qpt_07_hashjoin.html
 *
 * SQL texts are copies of the jmx: `trimIndent()` removes only the code indentation,
 * trailing spaces and tabs inside the queries are kept on purpose (`query_md5` in telegraf).
 */
object Qpt07HashJoin : Scenario {
    override val id = "qpt_07_hashjoin"
    override val name = "qpt_07_hashjoin (TC)"

    override fun tc(): DslTransactionController = transaction(
        name,
        callableSql("qpt_07_hashjoin: Hash join", Pools.QPT_07,
            """
            SELECT *
              FROM tickets t JOIN ticket_flights tf ON tf.ticket_no = t.ticket_no
              LIMIT 1000;
            """.trimIndent()),
        callableSql("qpt_07_hashjoin: Модификации", Pools.QPT_07,
            """
            SELECT * 
              FROM aircrafts a FULL JOIN seats s ON a.aircraft_code = s.aircraft_code
              LIMIT 1000;
            """.trimIndent()),
        callableSql("qpt_07_hashjoin: Группировка и уникальные значения", Pools.QPT_07,
            """
            SELECT fare_conditions, count(*)
              FROM seats
              GROUP BY fare_conditions
              LIMIT 1000;
            """.trimIndent()),
        callableSql("qpt_07_hashjoin: Группировка и уникальные значения 2", Pools.QPT_07,
            """
            SELECT DISTINCT fare_conditions
              FROM seats
              LIMIT 1000;
            """.trimIndent()),
        callableSql("qpt_07_hashjoin: Соединение нескольких таблиц", Pools.QPT_07,
            """
            SELECT t.passenger_name, f.flight_no
              FROM tickets t
                JOIN ticket_flights tf ON tf.ticket_no = t.ticket_no
                JOIN flights f ON f.flight_id = tf.flight_id
            LIMIT 1000;
            """.trimIndent()),
    )
}
