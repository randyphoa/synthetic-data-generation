package com.example.dao;

import java.util.List;

public class SampleDAO extends AbstractDAO<CustomerDTO> {

    private static final String TABLE_NAME = "T_CUSTOMER";

    private static final String SQL_SELECT = "SELECT * FROM " + TABLE_NAME;

    private static final String SQL_WHERE_ACTIVE = " WHERE CUST_STS_CDE = 'A'";

    private static final String SQL_AND_CREDIT_RANGE =
        " AND CUST_CRDT_SCR >= ? AND CUST_CRDT_SCR < ?";

    private static final String SQL_ACTIVE_BY_CREDIT =
        SQL_SELECT + SQL_WHERE_ACTIVE + SQL_AND_CREDIT_RANGE;

    private static final String SQL_COUNT_BY_DATE =
        "SELECT COUNT(*) FROM " + TABLE_NAME
        + " WHERE CUST_MBR_SINCE_DT <= ? AND CUST_STS_CDE = ?";

    public List<CustomerDTO> findActiveCustomersByCreditRange(
            String minScore, String maxScore, String sortOrder) {
        return executeQuery(SQL_ACTIVE_BY_CREDIT,
            new Object[] { minScore, maxScore }, sortOrder);
    }

    public List<CustomerDTO> findByStatusAndEmploymentType(String stsCde, String emplTpCde) {
        return findAllByVariables(
            new String[] { "CUST_STS_CDE", "CUST_EMPL_TP_CDE" },
            new ConditionType[] { ConditionType.EQUALS, ConditionType.EQUALS },
            new Object[] { stsCde, emplTpCde },
            null);
    }

    public int countCustomersByMemberDate(String memberDate, String status) {
        return executeCount(SQL_COUNT_BY_DATE,
            new Object[] { memberDate, status });
    }

    public List<CustomerDTO> findClosedCustomers(String cutoffDate) {
        String query = "SELECT * FROM " + TABLE_NAME
            + " WHERE CUST_STS_CDE = 'C'"
            + " AND CUST_MBR_SINCE_DT < ?";
        return executeQuery(query, new Object[] { cutoffDate }, null);
    }
}
