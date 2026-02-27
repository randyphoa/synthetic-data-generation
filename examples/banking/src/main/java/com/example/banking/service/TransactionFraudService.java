package com.example.banking.service;

import org.springframework.stereotype.Service;

@Service
public class TransactionFraudService {

    /**
     * Assesses a transaction for potential fraud based on amount, patterns, merchant info, and verification.
     * Compound booleans, inter-variable dependencies, negation, null checks.
     *
     * @param amount                   transaction amount
     * @param dailyLimit               customer's daily transaction limit
     * @param averageTransactionAmount customer's average transaction amount
     * @param merchantCategory         merchant category (RETAIL, GROCERY, TRAVEL, ELECTRONICS, etc.)
     * @param merchantDistance          distance to merchant in miles
     * @param isVerified               whether the transaction is verified (e.g., chip/PIN)
     * @param hourOfDay                hour of the day (0-23)
     * @param isInternational          whether the transaction is international
     * @return fraud assessment verdict string
     */
    public String assessTransaction(
            double amount,
            double dailyLimit,
            double averageTransactionAmount,
            String merchantCategory,
            double merchantDistance,
            boolean isVerified,
            int hourOfDay,
            boolean isInternational) {

        // Null check on merchantCategory
        if (merchantCategory == null) {
            return "BLOCKED_MISSING_DATA";
        }

        // Inter-variable dependency: amount vs dailyLimit
        if (amount > dailyLimit) {
            if (amount > dailyLimit * 2.0) {
                return "BLOCKED_OVER_LIMIT";
            } else {
                if (!isVerified && isInternational) {
                    return "BLOCKED_OVER_LIMIT";
                } else {
                    return "FLAG_OVER_LIMIT";
                }
            }
        }

        // Compound boolean: high amount + unverified
        if (amount > 5000.0 && !isVerified) {
            if (isInternational) {
                return "BLOCKED_UNVERIFIED_INTL";
            } else {
                if (hourOfDay >= 0 && hourOfDay <= 5) {
                    return "FLAG_UNVERIFIED_HIGH_NIGHT";
                } else {
                    return "FLAG_UNVERIFIED_HIGH";
                }
            }
        }

        // Inter-variable dependency: amount vs average + merchant distance
        if (amount > averageTransactionAmount * 5.0 && merchantDistance > 500.0) {
            if (hourOfDay >= 0 && hourOfDay <= 5) {
                if (isInternational) {
                    return "FLAG_SUSPICIOUS_INTL_NIGHT";
                } else {
                    return "FLAG_SUSPICIOUS_NIGHT";
                }
            } else {
                if (!isVerified) {
                    return "FLAG_SUSPICIOUS_UNVERIFIED";
                } else {
                    return "FLAG_REVIEW";
                }
            }
        }

        // ATM-specific checks
        if (merchantCategory.equals("ATM")) {
            if (amount > 1000.0) {
                if (!isVerified || hourOfDay >= 22 || hourOfDay <= 4) {
                    return "FLAG_ATM_HIGH";
                } else {
                    return "APPROVED";
                }
            } else {
                return "APPROVED";
            }
        }

        // International + high amount
        if (isInternational && amount > 2000.0) {
            if (merchantCategory.equals("ELECTRONICS") || merchantCategory.equals("TRAVEL")) {
                return "FLAG_INTERNATIONAL";
            } else {
                return "APPROVED";
            }
        }

        // Default: approve
        return "APPROVED";
    }
}
