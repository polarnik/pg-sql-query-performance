package qa.load.sql.dsl

import org.apache.jmeter.protocol.jdbc.config.DataSourceElement
import org.apache.jmeter.testelement.TestElement
import org.postgresql.Driver
import us.abstracta.jmeter.javadsl.jdbc.DslJdbcConnectionPool
import java.time.Duration

/**
 * JDBC Connection Configuration with the full set of properties used in `sql_demo_test.jmx`.
 *
 * `DslJdbcConnectionPool` always sets `preinit=true` and has no builders for
 * `keepAlive`, `connectionAge`, `trimInterval`, `checkQuery`, `initQuery`,
 * so they are set on the built `DataSourceElement`.
 */
class PgJdbcPool(
    dataSource: String,
    url: String,
    private val testName: String,
    private val poolMax: Int,
    private val isolation: String,
    private val preinit: Boolean,
    private val checkQuery: String,
    private val initQuery: String,
    private val keepAlive: Boolean = true,
    private val connectionAge: String = "5000",
    private val trimInterval: String = "60000",
) : DslJdbcConnectionPool(dataSource, Driver::class.java, url) {

    override fun buildTestElement(): TestElement {
        val ret = super.buildTestElement() as DataSourceElement
        ret.poolMax = poolMax.toString()
        ret.transactionIsolation = isolation
        ret.isPreinit = preinit
        ret.checkQuery = checkQuery
        ret.initQuery = initQuery
        ret.isKeepAlive = keepAlive
        ret.connectionAge = connectionAge
        ret.trimInterval = trimInterval
        ret.connectionProperties = ""
        return ret
    }

    override fun buildConfiguredTestElement(): TestElement {
        val ret = super.buildConfiguredTestElement()
        ret.name = testName
        return ret
    }
}

/**
 * @param poolMax `0` means "connection per thread", required for `BEGIN ... COMMIT` on one connection
 * @param isolation `DEFAULT` or `TRANSACTION_REPEATABLE_READ` and other `java.sql.Connection` constant names
 */
fun pgPool(
    dataSource: String,
    applicationName: String,
    user: String,
    password: String,
    url: String,
    testName: String = "JDBC Connection Configuration $applicationName",
    poolMax: Int = 50,
    autoCommit: Boolean = true,
    isolation: String = "DEFAULT",
    preinit: Boolean = false,
    checkQuery: String = "",
    initQuery: String = "",
): PgJdbcPool {
    val pool = PgJdbcPool(
        dataSource = dataSource,
        url = url,
        testName = testName,
        poolMax = poolMax,
        isolation = isolation,
        preinit = preinit,
        checkQuery = checkQuery,
        initQuery = initQuery,
    )
    pool.user(user)
        .password(password)
        .autoCommit(autoCommit)
        .maxConnectionWait(Duration.ofMillis(10000))
    return pool
}
