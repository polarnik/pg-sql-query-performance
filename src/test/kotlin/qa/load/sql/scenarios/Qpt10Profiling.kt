package qa.load.sql.scenarios

import qa.load.sql.dsl.sql
import qa.load.sql.pools.Pools
import us.abstracta.jmeter.javadsl.JmeterDsl.transaction
import us.abstracta.jmeter.javadsl.core.controllers.DslTransactionController

/**
 * `qpt_10_profiling (TC)`.
 * https://edu.postgrespro.ru/qpt/qpt_10_profiling.html
 *
 * SQL texts are copies of the jmx: `trimIndent()` removes only the code indentation,
 * trailing spaces and tabs inside the queries are kept on purpose (`query_md5` in telegraf).
 */
object Qpt10Profiling : Scenario {
    override val id = "qpt_10_profiling"
    override val name = "qpt_10_profiling (TC)"

    override fun tc(): DslTransactionController = transaction(
        name,
        sql("qpt_10_profiling: Профиль выполнения", Pools.QPT_10,
            """
            SELECT * FROM report()
            LIMIT 1000;
            """.trimIndent()),
        sql("qpt_10_profiling: отчет одним запросом", Pools.QPT_10,
            """
            WITH t AS (
              SELECT f.aircraft_code, 
                count(*) FILTER (WHERE s.fare_conditions = 'Economy') economy,
                count(*) FILTER (WHERE s.fare_conditions = 'Comfort') comfort,
                count(*) FILTER (WHERE s.fare_conditions = 'Business') business 
              FROM flights f 
                JOIN boarding_passes bp ON bp.flight_id = f.flight_id 
                JOIN seats s ON s.aircraft_code = f.aircraft_code AND s.seat_no = bp.seat_no 
              GROUP BY f.aircraft_code
            )
            SELECT a.model,
                   coalesce(t.economy,0) economy, 
                   coalesce(t.comfort,0) comfort, 
                   coalesce(t.business,0) business 
              FROM aircrafts a LEFT JOIN t ON a.aircraft_code = t.aircraft_code 
              ORDER BY a.model
            LIMIT 1000;
            """.trimIndent()),
    )
}
