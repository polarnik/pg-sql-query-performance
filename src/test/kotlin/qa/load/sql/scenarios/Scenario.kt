package qa.load.sql.scenarios

import us.abstracta.jmeter.javadsl.core.controllers.DslTransactionController

/** One qpt topic: a transaction with its JDBC requests. */
interface Scenario {
    /** Short id, used in [qa.load.sql.LoadProfile] and in `-Drate.<id>=...` */
    val id: String

    /** Transaction Controller name, the `transaction` tag in InfluxDB */
    val name: String

    fun tc(): DslTransactionController
}
