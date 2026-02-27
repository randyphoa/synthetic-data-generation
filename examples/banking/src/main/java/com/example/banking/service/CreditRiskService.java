package com.example.banking.service;

import org.springframework.stereotype.Service;

@Service
public class CreditRiskService {

    /**
     * Assesses credit risk based on credit score, debt ratio, credit history, and account status.
     * Ternary expressions in returns, sequential if/else, multiple numeric ranges.
     *
     * @param creditScore          credit score (300-850)
     * @param debtToIncomeRatio    ratio of monthly debt to monthly income
     * @param yearsOfCreditHistory years of credit history
     * @param hasDefaultHistory    whether the applicant has a history of defaults
     * @param numberOfOpenAccounts number of open credit accounts
     * @return risk rating string (LOW, MODERATE, HIGH, CRITICAL, INVALID)
     */
    public String assessRisk(
            int creditScore,
            double debtToIncomeRatio,
            int yearsOfCreditHistory,
            boolean hasDefaultHistory,
            int numberOfOpenAccounts) {

        // Invalid score guard
        if (creditScore < 300 || creditScore > 850) {
            return "INVALID";
        }

        // Default history check
        if (hasDefaultHistory) {
            if (creditScore >= 700) {
                return (yearsOfCreditHistory >= 5) ? "HIGH" : "CRITICAL";
            } else {
                return "CRITICAL";
            }
        }

        // Excellent score tier (>= 750)
        if (creditScore >= 750) {
            if (debtToIncomeRatio <= 0.28) {
                return (numberOfOpenAccounts <= 10) ? "LOW" : "MODERATE";
            } else if (debtToIncomeRatio <= 0.43) {
                if (yearsOfCreditHistory >= 10) {
                    return "LOW";
                } else {
                    return "MODERATE";
                }
            } else {
                return "MODERATE";
            }
        }

        // Good score tier (>= 670)
        if (creditScore >= 670) {
            if (debtToIncomeRatio <= 0.36) {
                if (yearsOfCreditHistory >= 5) {
                    return (numberOfOpenAccounts <= 8) ? "LOW" : "MODERATE";
                } else {
                    return "MODERATE";
                }
            } else if (debtToIncomeRatio <= 0.50) {
                return (yearsOfCreditHistory >= 7) ? "MODERATE" : "HIGH";
            } else {
                return "HIGH";
            }
        }

        // Fair score tier (>= 580)
        if (creditScore >= 580) {
            if (debtToIncomeRatio <= 0.36) {
                return (yearsOfCreditHistory >= 8) ? "MODERATE" : "HIGH";
            } else {
                return (debtToIncomeRatio <= 0.50) ? "HIGH" : "CRITICAL";
            }
        }

        // Poor score tier (< 580)
        if (debtToIncomeRatio <= 0.28) {
            return (yearsOfCreditHistory >= 10) ? "HIGH" : "CRITICAL";
        } else {
            return "CRITICAL";
        }
    }
}
