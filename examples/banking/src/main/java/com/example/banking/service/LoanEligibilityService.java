package com.example.banking.service;

import org.springframework.stereotype.Service;

@Service
public class LoanEligibilityService {

    /**
     * Evaluates loan eligibility based on credit score, income, debt, employment, and customer history.
     * Deep nested if/else with compound booleans, enum string equality, null checks, and boolean params.
     *
     * @param creditScore        applicant's credit score (300-850)
     * @param annualIncome       applicant's annual income
     * @param monthlyDebtPayment applicant's monthly debt obligations
     * @param requestedAmount    loan amount requested
     * @param employmentType     employment status (FULL_TIME, PART_TIME, SELF_EMPLOYED, RETIRED, UNEMPLOYED)
     * @param isExistingCustomer whether the applicant is an existing bank customer
     * @param yearsEmployed      number of years at current employment
     * @return decision string indicating loan eligibility outcome
     */
    public String evaluateLoanEligibility(
            int creditScore,
            double annualIncome,
            double monthlyDebtPayment,
            double requestedAmount,
            String employmentType,
            boolean isExistingCustomer,
            int yearsEmployed) {

        // Null check on employmentType
        if (employmentType == null) {
            return "DENIED_MISSING_INFO";
        }

        // Invalid score guard
        if (creditScore < 300 || creditScore > 850) {
            return "DENIED_INVALID_SCORE";
        }

        // Calculate debt-to-income ratio
        double monthlyIncome = annualIncome / 12.0;
        double debtToIncomeRatio = (monthlyIncome > 0) ? monthlyDebtPayment / monthlyIncome : 1.0;

        // Excellent credit tier (>= 750)
        if (creditScore >= 750) {
            if (annualIncome >= 100000) {
                if (isExistingCustomer) {
                    if (debtToIncomeRatio <= 0.35) {
                        return "APPROVED_PREMIUM";
                    } else {
                        return "APPROVED_STANDARD";
                    }
                } else {
                    if (requestedAmount <= annualIncome * 0.5) {
                        return "APPROVED_STANDARD";
                    } else {
                        return "MANUAL_REVIEW";
                    }
                }
            } else if (annualIncome >= 50000) {
                if (employmentType.equals("FULL_TIME") || employmentType.equals("SELF_EMPLOYED")) {
                    if (yearsEmployed >= 2) {
                        return "APPROVED_STANDARD";
                    } else {
                        return "APPROVED_CONDITIONAL";
                    }
                } else {
                    return "MANUAL_REVIEW";
                }
            } else {
                if (isExistingCustomer && debtToIncomeRatio <= 0.28) {
                    return "APPROVED_CONDITIONAL";
                } else {
                    return "MANUAL_REVIEW";
                }
            }
        }

        // Good credit tier (>= 670)
        if (creditScore >= 670) {
            if (employmentType.equals("FULL_TIME") || employmentType.equals("SELF_EMPLOYED")) {
                if (annualIncome >= 75000) {
                    if (yearsEmployed >= 3 && debtToIncomeRatio <= 0.40) {
                        return "APPROVED_STANDARD";
                    } else if (yearsEmployed >= 1) {
                        return "APPROVED_CONDITIONAL";
                    } else {
                        return "DENIED_EMPLOYMENT_HISTORY";
                    }
                } else if (annualIncome >= 40000) {
                    if (isExistingCustomer) {
                        if (requestedAmount <= 15000) {
                            return "APPROVED_CONDITIONAL";
                        } else {
                            return "MANUAL_REVIEW";
                        }
                    } else {
                        if (debtToIncomeRatio <= 0.30) {
                            return "APPROVED_CONDITIONAL";
                        } else {
                            return "DENIED_DEBT_RATIO";
                        }
                    }
                } else {
                    return "DENIED_INCOME";
                }
            } else if (employmentType.equals("PART_TIME")) {
                if (annualIncome >= 30000 && yearsEmployed >= 2) {
                    return "MANUAL_REVIEW";
                } else {
                    return "DENIED_PART_TIME";
                }
            } else if (employmentType.equals("RETIRED")) {
                if (annualIncome >= 50000) {
                    return "APPROVED_CONDITIONAL";
                } else {
                    return "MANUAL_REVIEW";
                }
            } else {
                return "DENIED_EMPLOYMENT";
            }
        }

        // Fair credit tier (>= 580)
        if (creditScore >= 580) {
            if (employmentType.equals("FULL_TIME")) {
                if (isExistingCustomer && annualIncome >= 60000) {
                    if (debtToIncomeRatio <= 0.30 && yearsEmployed >= 3) {
                        return "MANUAL_REVIEW";
                    } else {
                        return "DENIED_CREDIT";
                    }
                } else {
                    return "DENIED_CREDIT";
                }
            } else if (employmentType.equals("SELF_EMPLOYED")) {
                if (annualIncome >= 80000 && yearsEmployed >= 5) {
                    return "MANUAL_REVIEW";
                } else {
                    return "DENIED_CREDIT";
                }
            } else {
                return "DENIED_CREDIT";
            }
        }

        // Poor credit tier (< 580)
        if (isExistingCustomer) {
            if (annualIncome >= 100000 && debtToIncomeRatio <= 0.20) {
                return "MANUAL_REVIEW";
            } else {
                return "DENIED_CREDIT";
            }
        } else {
            return "DENIED_CREDIT";
        }
    }
}
