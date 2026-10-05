package qa.load.sql.scenarios

import qa.load.sql.dsl.sql
import qa.load.sql.pools.Pools
import us.abstracta.jmeter.javadsl.JmeterDsl.transaction
import us.abstracta.jmeter.javadsl.core.controllers.DslTransactionController

/**
 * `qpt_06_nestloop (TC)`.
 * https://edu.postgrespro.ru/qpt/qpt_06_nestloop.html
 *
 * SQL texts are copies of the jmx: `trimIndent()` removes only the code indentation,
 * trailing spaces and tabs inside the queries are kept on purpose (`query_md5` in telegraf).
 */
object Qpt06NestLoop : Scenario {
    override val id = "qpt_06_nestloop"
    override val name = "qpt_06_nestloop (TC)"

    override fun tc(): DslTransactionController = transaction(
        name,
        sql("qpt_06_nestloop: Nested loop", Pools.QPT_06,
            """
            SELECT *
              FROM tickets t JOIN ticket_flights tf ON tf.ticket_no = t.ticket_no 
              WHERE t.ticket_no IN ('0005434877256','0005433843368');
            """.trimIndent()),
        sql("qpt_06_nestloop: Модификации", Pools.QPT_06,
            """
            SELECT * 
              FROM aircrafts a LEFT JOIN seats s ON (a.aircraft_code = s.aircraft_code) 
              WHERE a.model LIKE 'Аэробус%';
            """.trimIndent()),
        sql("qpt_06_nestloop: Модификации 2", Pools.QPT_06,
            """
            SELECT * 
              FROM aircrafts a
              WHERE a.model LIKE 'Аэробус%'
              AND NOT EXISTS (SELECT * FROM seats s WHERE s.aircraft_code = a.aircraft_code);
            """.trimIndent()),
        sql("qpt_06_nestloop: Модификации 3", Pools.QPT_06,
            """
            SELECT * 
              FROM aircrafts a LEFT JOIN seats s ON (a.aircraft_code = s.aircraft_code) 
              WHERE a.model LIKE 'Аэробус%'
              AND s.aircraft_code IS NULL;
            """.trimIndent()),
        sql("qpt_06_nestloop: Модификации 4", Pools.QPT_06,
            """
            SELECT * 
              FROM aircrafts a
              WHERE a.model LIKE 'Аэробус%'
              AND EXISTS (SELECT * FROM seats s WHERE s.aircraft_code = a.aircraft_code);
            """.trimIndent()),
        sql("qpt_06_nestloop: Модификации 5", Pools.QPT_06,
            """
            SELECT *
              FROM aircrafts a
              WHERE a.model LIKE 'Аэробус%'
              AND EXISTS (SELECT * FROM seats s WHERE s.aircraft_code = a.aircraft_code);
            """.trimIndent()),
        sql("qpt_06_nestloop: Соединение нескольких таблиц", Pools.QPT_06,
            """
            SELECT t.passenger_name
              FROM tickets t
                JOIN ticket_flights tf ON tf.ticket_no = t.ticket_no
                JOIN flights f ON f.flight_id = tf.flight_id
              WHERE f.flight_id = 12345;
            """.trimIndent()),
    )
}
