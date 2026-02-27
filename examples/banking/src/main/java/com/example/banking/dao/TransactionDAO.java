package com.example.banking.dao;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Repository
public class TransactionDAO {

    // Fragmented SQL constants
    private static final String SQL_SELECT = "SELECT TXN_ID, TXN_ACCT_ID, TXN_TP_CDE, TXN_AMT, "
            + "TXN_MERCH_CAT, TXN_MERCH_DIST, TXN_VERIFIED, TXN_INTL, TXN_HOUR, TXN_DT, TXN_DESC ";
    private static final String SQL_FROM = "FROM T_TRANSACTION ";
    private static final String SQL_WHERE_ACCOUNT = "WHERE TXN_ACCT_ID = ? ";
    private static final String SQL_AND_DATE_RANGE = "AND TXN_DT BETWEEN ? AND ? ";
    private static final String SQL_AND_AMOUNT_MIN = "AND TXN_AMT >= ? ";
    private static final String SQL_ORDER_BY_DATE = "ORDER BY TXN_DT DESC";

    private final JdbcTemplate jdbcTemplate;

    public TransactionDAO(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    public List<Map<String, Object>> findByAccount(long accountId) {
        String sql = SQL_SELECT + SQL_FROM + SQL_WHERE_ACCOUNT + SQL_ORDER_BY_DATE;
        return jdbcTemplate.queryForList(sql, accountId);
    }

    public List<Map<String, Object>> findByAccountAndDateRange(long accountId, String startDate, String endDate) {
        String sql = SQL_SELECT + SQL_FROM + SQL_WHERE_ACCOUNT + SQL_AND_DATE_RANGE + SQL_ORDER_BY_DATE;
        return jdbcTemplate.queryForList(sql, accountId, startDate, endDate);
    }

    public List<Map<String, Object>> findLargeTransactions(long accountId, double minAmount) {
        String sql = SQL_SELECT + SQL_FROM + SQL_WHERE_ACCOUNT + SQL_AND_AMOUNT_MIN + SQL_ORDER_BY_DATE;
        return jdbcTemplate.queryForList(sql, accountId, minAmount);
    }

    public List<Map<String, Object>> findByTransactionTypes(long accountId, List<String> transactionTypes) {
        if (transactionTypes == null || transactionTypes.isEmpty()) {
            return Collections.emptyList();
        }
        String inClause = buildSqlInCondition(transactionTypes);
        String sql = String.format(
                SQL_SELECT + SQL_FROM + SQL_WHERE_ACCOUNT + "AND TXN_TP_CDE IN (%s) " + SQL_ORDER_BY_DATE,
                inClause);
        Object[] params = new Object[transactionTypes.size() + 1];
        params[0] = accountId;
        for (int i = 0; i < transactionTypes.size(); i++) {
            params[i + 1] = transactionTypes.get(i);
        }
        return jdbcTemplate.queryForList(sql, params);
    }

    public int countByAccount(long accountId) {
        String sql = "SELECT COUNT(*) FROM T_TRANSACTION WHERE TXN_ACCT_ID = ?";
        Integer count = jdbcTemplate.queryForObject(sql, Integer.class, accountId);
        return count != null ? count : 0;
    }

    private String buildSqlInCondition(List<String> values) {
        return values.stream()
                .map(v -> "?")
                .collect(Collectors.joining(", "));
    }
}
