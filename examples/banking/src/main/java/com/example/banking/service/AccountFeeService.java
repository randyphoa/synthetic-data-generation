package com.example.banking.service;

import org.springframework.stereotype.Service;

@Service
public class AccountFeeService {

    /**
     * Calculates monthly maintenance fee based on account type, balance, and customer status.
     * Switch/case with nested if/else for fee waiver conditions.
     *
     * @param accountType      account type (CHECKING, SAVINGS, MONEY_MARKET, CD)
     * @param balance          current account balance
     * @param hasDirectDeposit whether the account has direct deposit set up
     * @param accountAgeMonths age of the account in months
     * @return monthly fee amount
     */
    public double calculateMonthlyFee(
            String accountType,
            double balance,
            boolean hasDirectDeposit,
            int accountAgeMonths) {

        if (accountType == null) {
            return 25.00;
        }

        switch (accountType) {
            case "CHECKING":
                if (balance >= 5000.0) {
                    return 0.0;
                } else if (hasDirectDeposit) {
                    return 0.0;
                } else if (balance >= 1500.0) {
                    return 6.95;
                } else {
                    return 12.00;
                }

            case "SAVINGS":
                if (balance >= 2500.0) {
                    return 0.0;
                } else if (accountAgeMonths >= 24) {
                    return 2.50;
                } else {
                    return 5.00;
                }

            case "MONEY_MARKET":
                if (balance >= 25000.0) {
                    return 0.0;
                } else if (balance >= 10000.0) {
                    return 10.00;
                } else {
                    return 25.00;
                }

            case "CD":
                if (accountAgeMonths >= 12) {
                    return 0.0;
                } else {
                    return 15.00;
                }

            default:
                return 25.00;
        }
    }

    /**
     * Calculates per-transaction fee based on transaction type, account type, and amount.
     * Switch/case with ternary expressions in return statements.
     *
     * @param accountType           account type
     * @param transactionType       type of transaction (WITHDRAWAL, TRANSFER, PAYMENT, DEPOSIT)
     * @param amount                transaction amount
     * @param transactionsThisMonth number of transactions this month
     * @return transaction fee amount
     */
    public double calculateTransactionFee(
            String accountType,
            String transactionType,
            double amount,
            int transactionsThisMonth) {

        if (transactionType == null) {
            return 0.0;
        }

        switch (transactionType) {
            case "WITHDRAWAL":
                if ("SAVINGS".equals(accountType)) {
                    return (transactionsThisMonth > 6) ? 10.00 : 0.0;
                } else if ("MONEY_MARKET".equals(accountType)) {
                    return (transactionsThisMonth > 3) ? 15.00 : 0.0;
                } else {
                    return 0.0;
                }

            case "TRANSFER":
                if (amount > 10000.0) {
                    return 25.00;
                } else if (amount > 1000.0) {
                    return (transactionsThisMonth > 5) ? 5.00 : 2.50;
                } else {
                    return 0.0;
                }

            case "PAYMENT":
                if ("CD".equals(accountType)) {
                    return 35.00;
                } else {
                    return (amount > 5000.0) ? 3.00 : 0.0;
                }

            case "DEPOSIT":
                return (amount >= 10000.0) ? 5.00 : 0.0;

            default:
                return 0.0;
        }
    }
}
