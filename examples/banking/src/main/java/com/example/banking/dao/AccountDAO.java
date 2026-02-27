package com.example.banking.dao;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;
import java.util.List;
import java.util.Map;

@Repository
public class AccountDAO {

    private final JdbcTemplate jdbcTemplate;

    public AccountDAO(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    public List<Map<String, Object>> findActiveAccountsWithCustomer() {
        String sql = "SELECT a.ACCT_ID, a.ACCT_TP_CDE, a.ACCT_BAL, a.ACCT_STS_CDE, "
                + "c.CUST_ID, c.CUST_FIRST_NM, c.CUST_LAST_NM "
                + "FROM T_ACCOUNT a "
                + "INNER JOIN T_CUSTOMER c ON a.ACCT_CUST_ID = c.CUST_ID "
                + "WHERE a.ACCT_STS_CDE = 'A' "
                + "ORDER BY a.ACCT_ID";
        return jdbcTemplate.queryForList(sql);
    }

    public List<Map<String, Object>> findOverdrawnAccounts() {
        String sql = "SELECT a.ACCT_ID, a.ACCT_TP_CDE, a.ACCT_BAL, "
                + "c.CUST_FIRST_NM, c.CUST_LAST_NM, c.CUST_EMAIL "
                + "FROM T_ACCOUNT a "
                + "INNER JOIN T_CUSTOMER c ON a.ACCT_CUST_ID = c.CUST_ID "
                + "WHERE a.ACCT_BAL < 0 "
                + "ORDER BY a.ACCT_BAL ASC";
        return jdbcTemplate.queryForList(sql);
    }

    public List<Map<String, Object>> findAccountsByType(String accountType) {
        String sql = "SELECT ACCT_ID, ACCT_TP_CDE, ACCT_BAL, ACCT_STS_CDE, ACCT_OPEN_DT "
                + "FROM T_ACCOUNT "
                + "WHERE ACCT_TP_CDE = ? AND ACCT_STS_CDE = 'A' "
                + "ORDER BY ACCT_BAL DESC";
        return jdbcTemplate.queryForList(sql, accountType);
    }

    public int countAccountsByCustomer(long customerId) {
        String sql = "SELECT COUNT(*) FROM T_ACCOUNT WHERE ACCT_CUST_ID = ? AND ACCT_STS_CDE = 'A'";
        Integer count = jdbcTemplate.queryForObject(sql, Integer.class, customerId);
        return count != null ? count : 0;
    }
}
