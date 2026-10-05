package qa.load.sql.pools

import qa.load.sql.config.LoadConfig
import qa.load.sql.dsl.PgJdbcPool
import qa.load.sql.dsl.pgPool

/**
 * JDBC Connection Configurations of `sql_demo_test.jmx`.
 * `ApplicationName` (-> `pg_stat_activity.application_name`) and user (-> `usename`)
 * are the monitoring contract, users are created in `config/postgresql/bookings.functions.sql`.
 */
object Pools {
    const val QPT_03 = "DB_qpt_03_seqscan"
    const val QPT_04 = "DB_qpt_04_indexscan"
    const val QPT_05 = "DB_qpt_05_bitmapscan"
    const val QPT_06 = "DB_qpt_06_nestloop"
    const val QPT_07 = "DB_qpt_07_hashjoin"
    const val QPT_08 = "DB_qpt_08_mergejoin"
    const val QPT_10 = "DB_qpt_10_profiling"
    const val QPT_11 = "DB_qpt_11_technics"
    const val QPT_11_REPEATABLE_READ = "DB_qpt_11_technics_REPEATABLE_READ"
    const val QPT_TRANSACTION = "DB_qpt_transaction"
    const val IDLE = "DB_idle"

    fun all(cfg: LoadConfig): List<PgJdbcPool> = listOf(
        pool(cfg, QPT_03, "qpt_03_seqscan", "qpt_03_seqscan_user"),
        pool(cfg, QPT_04, "qpt_04_indexscan", "qpt_04_indexscan_user"),
        pool(cfg, QPT_05, "qpt_05_bitmapscan", "qpt_05_bitmapscan_user"),
        pool(cfg, QPT_06, "qpt_06_nestloop", "qpt_06_nestloop_user"),
        pool(cfg, QPT_07, "qpt_07_hashjoin", "qpt_07_hashjoin_user"),
        pool(cfg, QPT_08, "qpt_08_mergejoin", "qpt_08_mergejoin_user"),
        pool(cfg, QPT_10, "qpt_10_profiling", "qpt_10_profiling_user"),
        pool(cfg, QPT_11, "qpt_11_technics", "qpt_11_technics_user"),
        pgPool(
            dataSource = QPT_11_REPEATABLE_READ,
            applicationName = "qpt_11_technics_REPEATABLE_READ",
            user = "qpt_11_technics_user",
            password = cfg.dbPassword,
            url = cfg.jdbcUrl("qpt_11_technics_REPEATABLE_READ"),
            testName = "JDBC Connection Configuration qpt_11_technics REPEATABLE_READ",
            isolation = "TRANSACTION_REPEATABLE_READ",
        ),
        // own connection per thread and no autocommit: BEGIN ... sleep ... COMMIT -> "idle in transaction"
        pgPool(
            dataSource = QPT_TRANSACTION,
            applicationName = "qpt_transaction",
            user = "qpt_transaction_user",
            password = cfg.dbPassword,
            url = cfg.jdbcUrl("qpt_transaction"),
            poolMax = 0,
            autoCommit = false,
        ),
        // pool without samplers: preinit opens connections that stay "idle"
        pgPool(
            dataSource = IDLE,
            applicationName = "qpt_idle",
            user = "qpt_idle_user",
            password = cfg.dbPassword,
            url = cfg.jdbcUrl("qpt_idle"),
            preinit = true,
            checkQuery = "select 1",
            initQuery = "/*Init SQL*/ select 'Init SQL'",
        ),
    )

    private fun pool(cfg: LoadConfig, dataSource: String, applicationName: String, user: String) =
        pgPool(
            dataSource = dataSource,
            applicationName = applicationName,
            user = user,
            password = cfg.dbPassword,
            url = cfg.jdbcUrl(applicationName),
        )
}
