package com.example.banking.service;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class AccountFeeServiceTest {

    private AccountFeeService service;

    @BeforeEach
    void setUp() {
        service = new AccountFeeService();
    }

    @Test
    void checking_highBalance_noFee() {
        assertEquals(0.0, service.calculateMonthlyFee("CHECKING", 6000.0, false, 12));
    }

    @Test
    void checking_directDeposit_noFee() {
        assertEquals(0.0, service.calculateMonthlyFee("CHECKING", 500.0, true, 12));
    }

    @Test
    void checking_mediumBalance_reducedFee() {
        assertEquals(6.95, service.calculateMonthlyFee("CHECKING", 2000.0, false, 12));
    }

    @Test
    void checking_lowBalance_fullFee() {
        assertEquals(12.00, service.calculateMonthlyFee("CHECKING", 500.0, false, 12));
    }

    @Test
    void savings_highBalance_noFee() {
        assertEquals(0.0, service.calculateMonthlyFee("SAVINGS", 3000.0, false, 12));
    }

    @Test
    void savings_longStanding_reducedFee() {
        assertEquals(2.50, service.calculateMonthlyFee("SAVINGS", 1000.0, false, 30));
    }

    @Test
    void moneyMarket_highBalance_noFee() {
        assertEquals(0.0, service.calculateMonthlyFee("MONEY_MARKET", 30000.0, false, 12));
    }

    @Test
    void cd_mature_noFee() {
        assertEquals(0.0, service.calculateMonthlyFee("CD", 10000.0, false, 18));
    }

    @Test
    void nullAccountType_defaultFee() {
        assertEquals(25.00, service.calculateMonthlyFee(null, 1000.0, false, 12));
    }

    @Test
    void withdrawal_savings_overLimit_fee() {
        assertEquals(10.00, service.calculateTransactionFee("SAVINGS", "WITHDRAWAL", 100.0, 8));
    }

    @Test
    void transfer_highAmount_fee() {
        assertEquals(25.00, service.calculateTransactionFee("CHECKING", "TRANSFER", 15000.0, 3));
    }

    @Test
    void deposit_largeAmount_fee() {
        assertEquals(5.00, service.calculateTransactionFee("CHECKING", "DEPOSIT", 15000.0, 1));
    }

    @Test
    void deposit_normalAmount_noFee() {
        assertEquals(0.0, service.calculateTransactionFee("CHECKING", "DEPOSIT", 500.0, 1));
    }
}
