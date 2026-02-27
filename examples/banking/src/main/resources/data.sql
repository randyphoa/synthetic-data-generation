-- Seed data for legacy DAO tables

INSERT INTO T_LEGACY_CUSTOMER (CUST_FIRST_NM, CUST_LAST_NM, CUST_EMAIL, CUST_PHONE, CUST_STS_CDE, CUST_EMPL_TP_CDE, CUST_CRDT_SCR, CUST_ANN_INC, CUST_YRS_EMPL) VALUES
('Alice', 'Johnson', 'alice.johnson@example.com', '555-0101', 'A', 'FULL_TIME', 780, 120000.00, 8),
('Bob', 'Martinez', 'bob.martinez@example.com', '555-0102', 'A', 'SELF_EMPLOYED', 710, 95000.00, 12),
('Carol', 'Williams', 'carol.williams@example.com', '555-0103', 'A', 'PART_TIME', 620, 32000.00, 3),
('David', 'Chen', 'david.chen@example.com', '555-0104', 'A', 'RETIRED', 740, 65000.00, 0),
('Eva', 'Patel', 'eva.patel@example.com', '555-0105', 'A', 'FULL_TIME', 540, 45000.00, 1);

INSERT INTO T_LEGACY_ACCOUNT (ACCT_CUST_ID, ACCT_TP_CDE, ACCT_BAL, ACCT_STS_CDE, ACCT_OPEN_DT) VALUES
(1, 'CHECKING', 15200.50, 'A', '2016-02-01'),
(1, 'SAVINGS', 45000.00, 'A', '2016-02-01'),
(2, 'CHECKING', 8300.75, 'A', '2018-01-15'),
(2, 'MONEY_MARKET', 52000.00, 'A', '2021-06-01'),
(3, 'CHECKING', 1200.00, 'A', '2023-03-10'),
(4, 'SAVINGS', 125000.00, 'A', '2005-09-20'),
(4, 'CD', 50000.00, 'A', '2023-08-01'),
(5, 'CHECKING', -150.25, 'A', '2024-11-01');

INSERT INTO T_LEGACY_TRANSACTION (TXN_ACCT_ID, TXN_TP_CDE, TXN_AMT, TXN_MERCH_CAT, TXN_MERCH_DIST, TXN_VERIFIED, TXN_INTL, TXN_HOUR, TXN_DT, TXN_DESC) VALUES
(1, 'DEPOSIT', 3000.00, 'ATM', 0.0, TRUE, FALSE, 10, '2024-12-01 10:00:00', 'Payroll direct deposit'),
(1, 'WITHDRAWAL', 200.00, 'ATM', 2.0, TRUE, FALSE, 14, '2024-12-02 14:00:00', 'ATM withdrawal'),
(1, 'PAYMENT', 156.32, 'GROCERY', 5.0, TRUE, FALSE, 11, '2024-12-03 11:00:00', 'Whole Foods Market'),
(3, 'DEPOSIT', 4500.00, 'ATM', 0.0, TRUE, FALSE, 10, '2024-12-01 10:00:00', 'Client payment'),
(3, 'PAYMENT', 899.99, 'ELECTRONICS', 15.0, TRUE, FALSE, 16, '2024-12-05 16:00:00', 'Best Buy laptop'),
(6, 'WITHDRAWAL', 1500.00, 'ATM', 1.0, TRUE, FALSE, 10, '2024-12-01 10:00:00', 'Monthly withdrawal'),
(6, 'PAYMENT', 2500.00, 'TRAVEL', 500.0, TRUE, TRUE, 14, '2024-12-10 14:00:00', 'Intl hotel booking'),
(8, 'DEPOSIT', 850.25, 'ATM', 0.0, TRUE, FALSE, 10, '2024-11-01 10:00:00', 'Initial deposit');
