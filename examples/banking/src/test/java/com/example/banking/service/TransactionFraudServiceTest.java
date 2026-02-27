package com.example.banking.service;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class TransactionFraudServiceTest {

    private TransactionFraudService service;

    @BeforeEach
    void setUp() {
        service = new TransactionFraudService();
    }

    @Test
    void nullMerchantCategory_blockedMissingData() {
        assertEquals("BLOCKED_MISSING_DATA",
                service.assessTransaction(100.0, 5000.0, 200.0, null, 10.0, true, 12, false));
    }

    @Test
    void amountFarOverDailyLimit_blockedOverLimit() {
        assertEquals("BLOCKED_OVER_LIMIT",
                service.assessTransaction(12000.0, 5000.0, 200.0, "RETAIL", 10.0, true, 12, false));
    }

    @Test
    void amountSlightlyOverLimit_verified_flagOverLimit() {
        assertEquals("FLAG_OVER_LIMIT",
                service.assessTransaction(6000.0, 5000.0, 200.0, "RETAIL", 10.0, true, 12, false));
    }

    @Test
    void highAmount_unverified_international_blockedUnverifiedIntl() {
        assertEquals("BLOCKED_UNVERIFIED_INTL",
                service.assessTransaction(7500.0, 10000.0, 200.0, "ELECTRONICS", 800.0, false, 14, true));
    }

    @Test
    void highAmount_unverified_domestic_night_flagUnverifiedHighNight() {
        assertEquals("FLAG_UNVERIFIED_HIGH_NIGHT",
                service.assessTransaction(7500.0, 10000.0, 200.0, "ELECTRONICS", 10.0, false, 3, false));
    }

    @Test
    void highAmount_unverified_domestic_day_flagUnverifiedHigh() {
        assertEquals("FLAG_UNVERIFIED_HIGH",
                service.assessTransaction(7500.0, 10000.0, 200.0, "ELECTRONICS", 10.0, false, 14, false));
    }

    @Test
    void spikeAmount_farMerchant_night_intl_flagSuspiciousIntlNight() {
        assertEquals("FLAG_SUSPICIOUS_INTL_NIGHT",
                service.assessTransaction(1500.0, 10000.0, 200.0, "TRAVEL", 800.0, true, 2, true));
    }

    @Test
    void spikeAmount_farMerchant_day_unverified_flagSuspiciousUnverified() {
        assertEquals("FLAG_SUSPICIOUS_UNVERIFIED",
                service.assessTransaction(1500.0, 10000.0, 200.0, "TRAVEL", 800.0, false, 14, false));
    }

    @Test
    void atm_highAmount_unverified_flagAtmHigh() {
        assertEquals("FLAG_ATM_HIGH",
                service.assessTransaction(1500.0, 10000.0, 1000.0, "ATM", 5.0, false, 12, false));
    }

    @Test
    void atm_normalAmount_approved() {
        assertEquals("APPROVED",
                service.assessTransaction(200.0, 5000.0, 200.0, "ATM", 5.0, true, 12, false));
    }

    @Test
    void international_highAmount_electronics_flagInternational() {
        assertEquals("FLAG_INTERNATIONAL",
                service.assessTransaction(3000.0, 10000.0, 2000.0, "ELECTRONICS", 10.0, true, 14, true));
    }

    @Test
    void normalTransaction_approved() {
        assertEquals("APPROVED",
                service.assessTransaction(100.0, 5000.0, 200.0, "GROCERY", 5.0, true, 12, false));
    }
}
