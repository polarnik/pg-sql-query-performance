package qa.load.sql.scenarios

import qa.load.sql.dsl.sql
import qa.load.sql.pools.Pools
import us.abstracta.jmeter.javadsl.JmeterDsl.transaction
import us.abstracta.jmeter.javadsl.core.controllers.DslTransactionController

/**
 * `qpt_08_mergejoin (TC)`.
 * https://edu.postgrespro.ru/qpt/qpt_08_mergejoin.html
 *
 * SQL texts are copies of the jmx: `trimIndent()` removes only the code indentation,
 * trailing spaces and tabs inside the queries are kept on purpose (`query_md5` in telegraf).
 */
object Qpt08MergeJoin : Scenario {
    override val id = "qpt_08_mergejoin"
    override val name = "qpt_08_mergejoin (TC)"

    override fun tc(): DslTransactionController = transaction(
        name,
        sql("qpt_08_mergejoin: Merge join", Pools.QPT_08,
            """
            SELECT *
              FROM tickets t JOIN ticket_flights tf ON tf.ticket_no = t.ticket_no
              ORDER BY t.ticket_no
            LIMIT 100;
            """.trimIndent(), resultSetMaxRows = "", queryTimeout = "0"),
        sql("qpt_08_mergejoin: Merge join 2", Pools.QPT_08,
            """
            SELECT * 
              FROM tickets t JOIN ticket_flights tf ON tf.ticket_no = t.ticket_no
              ORDER BY t.ticket_no
              LIMIT 1000;
            """.trimIndent(), queryTimeout = "0"),
        sql("qpt_08_mergejoin: Merge join 3", Pools.QPT_08,
            """
            SELECT * 
              FROM aircrafts a JOIN seats s ON a.aircraft_code = s.aircraft_code
              ORDER BY a.aircraft_code
              LIMIT 1000;
            """.trimIndent(), queryTimeout = "0"),
        sql("qpt_08_mergejoin: Группировка и уникальные значения", Pools.QPT_08,
            """
            SELECT DISTINCT book_date
              FROM bookings
              LIMIT 1000;
            """.trimIndent(), queryTimeout = "0"),
        sql("qpt_08_mergejoin: Группировка и уникальные значения 2", Pools.QPT_08,
            """
            SELECT DISTINCT book_date
              FROM bookings
              ORDER BY book_date
              LIMIT 1000;
            """.trimIndent(), queryTimeout = "0"),
        sql("qpt_08_mergejoin: Соединение нескольких таблиц", Pools.QPT_08,
            """
            SELECT t.ticket_no, bp.flight_id, bp.seat_no
              FROM tickets t
                JOIN ticket_flights tf ON t.ticket_no = tf.ticket_no 
                JOIN boarding_passes bp ON bp.ticket_no = tf.ticket_no 
                 AND bp.flight_id = tf.flight_id 
              ORDER BY t.ticket_no
              LIMIT 1000;
            """.trimIndent(), queryTimeout = "0"),
    )
}
