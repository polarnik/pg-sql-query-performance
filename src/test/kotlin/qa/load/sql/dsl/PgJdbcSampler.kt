package qa.load.sql.dsl

import org.apache.jmeter.protocol.jdbc.sampler.JDBCSampler
import org.apache.jmeter.testelement.TestElement
import us.abstracta.jmeter.javadsl.jdbc.DslJdbcSampler
import us.abstracta.jmeter.javadsl.jdbc.DslJdbcSampler.QueryType

/**
 * JDBC Request with the properties used in `sql_demo_test.jmx`:
 * `resultSetHandler=Count Records` (the generator does not keep result sets in memory),
 * `resultSetMaxRows` and `queryTimeout` as strings (empty string is the jmx default).
 *
 * Query arguments are written as is (`DslJdbcSampler.param` quotes values with commas,
 * e.g. `${__Random(1000,5000,)}`, and the jmx keeps them unquoted).
 */
class PgJdbcSampler(
    label: String,
    pool: String,
    query: String,
    type: QueryType,
    private val resultSetMaxRows: String = "1",
    private val queryTimeout: String = "",
    private val queryArguments: List<String> = emptyList(),
    private val queryArgumentsTypes: List<String> = emptyList(),
) : DslJdbcSampler(label, pool, query) {

    init {
        queryType(type)
    }

    override fun buildTestElement(): TestElement {
        val ret = super.buildTestElement() as JDBCSampler
        ret.resultSetHandler = COUNT_RECORDS
        ret.resultSetMaxRows = resultSetMaxRows
        ret.queryTimeout = queryTimeout
        ret.queryArguments = queryArguments.joinToString(",")
        ret.queryArgumentsTypes = queryArgumentsTypes.joinToString(",")
        return ret
    }

    companion object {
        const val COUNT_RECORDS = "Count Records"
    }
}

/** Select Statement */
fun sql(label: String, pool: String, query: String, resultSetMaxRows: String = "1", queryTimeout: String = "") =
    PgJdbcSampler(label, pool, query, QueryType.SELECT, resultSetMaxRows, queryTimeout)

/** Prepared Select Statement, params are pairs of value and `java.sql.Types` field name (`INTEGER`, `VARCHAR`, ...) */
fun preparedSql(label: String, pool: String, query: String, vararg params: Pair<String, String>) =
    PgJdbcSampler(
        label, pool, query, QueryType.PREPARED_SELECT,
        queryArguments = params.map { it.first },
        queryArgumentsTypes = params.map { it.second },
    )

/** Callable Statement */
fun callableSql(label: String, pool: String, query: String) =
    PgJdbcSampler(label, pool, query, QueryType.CALLABLE)

/** AutoCommit(false) */
fun autoCommitFalse(label: String, pool: String, query: String = "") =
    PgJdbcSampler(label, pool, query, QueryType.AUTO_COMMIT_FALSE)

/** Commit */
fun commit(label: String, pool: String, query: String = "") =
    PgJdbcSampler(label, pool, query, QueryType.COMMIT)
