package com.example.banking.dao;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;
import java.util.List;
import java.util.Map;

@Repository
public class CustomerDAO {

    // Fragmented SQL constants for SQL extraction demo
    private static final String SQL_SELECT = "SELECT CUST_ID, CUST_FIRST_NM, CUST_LAST_NM, CUST_EMAIL, CUST_PHONE, "
            + "CUST_STS_CDE, CUST_EMPL_TP_CDE, CUST_CRDT_SCR, CUST_ANN_INC, CUST_YRS_EMPL ";
    private static final String SQL_FROM = "FROM T_CUSTOMER ";
    private static final String SQL_WHERE_ACTIVE = "WHERE CUST_STS_CDE = 'A' ";
    private static final String SQL_AND_CREDIT_RANGE = "AND CUST_CRDT_SCR BETWEEN ? AND ? ";
    private static final String SQL_AND_INCOME_MIN = "AND CUST_ANN_INC >= ? ";
    private static final String SQL_ORDER_BY = "ORDER BY CUST_LAST_NM, CUST_FIRST_NM";

    // Condition type constants for findAllByVariables
    private static final int COND_ACTIVE = 1;
    private static final int COND_CREDIT_RANGE = 2;
    private static final int COND_HIGH_INCOME = 3;

    private final JdbcTemplate jdbcTemplate;

    public CustomerDAO(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    public List<Map<String, Object>> findActiveCustomers() {
        String sql = SQL_SELECT + SQL_FROM + SQL_WHERE_ACTIVE + SQL_ORDER_BY;
        return jdbcTemplate.queryForList(sql);
    }

    public List<Map<String, Object>> findActiveByCreditRange(int minScore, int maxScore) {
        String sql = SQL_SELECT + SQL_FROM + SQL_WHERE_ACTIVE + SQL_AND_CREDIT_RANGE + SQL_ORDER_BY;
        return jdbcTemplate.queryForList(sql, minScore, maxScore);
    }

    public List<Map<String, Object>> findActiveHighIncome(double minIncome) {
        String sql = SQL_SELECT + SQL_FROM + SQL_WHERE_ACTIVE + SQL_AND_INCOME_MIN + SQL_ORDER_BY;
        return jdbcTemplate.queryForList(sql, minIncome);
    }

    public List<Map<String, Object>> findAllByVariables(int conditionType, Object... params) {
        StringBuilder sql = new StringBuilder(SQL_SELECT + SQL_FROM);

        if (conditionType == COND_ACTIVE) {
            sql.append(SQL_WHERE_ACTIVE);
        } else if (conditionType == COND_CREDIT_RANGE) {
            sql.append(SQL_WHERE_ACTIVE).append(SQL_AND_CREDIT_RANGE);
        } else if (conditionType == COND_HIGH_INCOME) {
            sql.append(SQL_WHERE_ACTIVE).append(SQL_AND_INCOME_MIN);
        }

        sql.append(SQL_ORDER_BY);
        return jdbcTemplate.queryForList(sql.toString(), params);
    }

    public int countActiveCustomers() {
        String sql = "SELECT COUNT(*) FROM T_CUSTOMER WHERE CUST_STS_CDE = 'A'";
        Integer count = jdbcTemplate.queryForObject(sql, Integer.class);
        return count != null ? count : 0;
    }
}
