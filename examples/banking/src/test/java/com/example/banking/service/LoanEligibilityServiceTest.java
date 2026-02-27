package com.example.banking.service;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class LoanEligibilityServiceTest {

    private LoanEligibilityService service;

    @BeforeEach
    void setUp() {
        service = new LoanEligibilityService();
    }

    @Test
    void nullEmploymentType_returnsDeniedMissingInfo() {
        assertEquals("DENIED_MISSING_INFO",
                service.evaluateLoanEligibility(750, 100000, 1000, 25000, null, true, 5));
    }

    @Test
    void invalidCreditScoreTooLow_returnsDeniedInvalidScore() {
        assertEquals("DENIED_INVALID_SCORE",
                service.evaluateLoanEligibility(200, 100000, 1000, 25000, "FULL_TIME", true, 5));
    }

    @Test
    void invalidCreditScoreTooHigh_returnsDeniedInvalidScore() {
        assertEquals("DENIED_INVALID_SCORE",
                service.evaluateLoanEligibility(900, 100000, 1000, 25000, "FULL_TIME", true, 5));
    }

    @Test
    void excellentCredit_highIncome_existingCustomer_lowDebt_approvedPremium() {
        assertEquals("APPROVED_PREMIUM",
                service.evaluateLoanEligibility(780, 120000, 2000, 25000, "FULL_TIME", true, 8));
    }

    @Test
    void excellentCredit_highIncome_existingCustomer_highDebt_approvedStandard() {
        assertEquals("APPROVED_STANDARD",
                service.evaluateLoanEligibility(780, 120000, 5000, 25000, "FULL_TIME", true, 8));
    }

    @Test
    void excellentCredit_highIncome_newCustomer_smallLoan_approvedStandard() {
        assertEquals("APPROVED_STANDARD",
                service.evaluateLoanEligibility(780, 120000, 2000, 50000, "FULL_TIME", false, 8));
    }

    @Test
    void excellentCredit_highIncome_newCustomer_largeLoan_manualReview() {
        assertEquals("MANUAL_REVIEW",
                service.evaluateLoanEligibility(780, 120000, 2000, 80000, "FULL_TIME", false, 8));
    }

    @Test
    void goodCredit_fullTime_highIncome_experienced_approvedStandard() {
        assertEquals("APPROVED_STANDARD",
                service.evaluateLoanEligibility(700, 80000, 2000, 25000, "FULL_TIME", true, 5));
    }

    @Test
    void goodCredit_unemployed_deniedEmployment() {
        assertEquals("DENIED_EMPLOYMENT",
                service.evaluateLoanEligibility(700, 80000, 2000, 25000, "UNEMPLOYED", true, 5));
    }

    @Test
    void fairCredit_fullTime_existingCustomer_goodIncome_lowDebt_manualReview() {
        assertEquals("MANUAL_REVIEW",
                service.evaluateLoanEligibility(600, 70000, 1000, 20000, "FULL_TIME", true, 5));
    }

    @Test
    void poorCredit_notExisting_deniedCredit() {
        assertEquals("DENIED_CREDIT",
                service.evaluateLoanEligibility(500, 50000, 1000, 10000, "FULL_TIME", false, 3));
    }

    @Test
    void poorCredit_existingCustomer_highIncome_lowDebt_manualReview() {
        assertEquals("MANUAL_REVIEW",
                service.evaluateLoanEligibility(500, 120000, 1500, 10000, "FULL_TIME", true, 3));
    }
}
