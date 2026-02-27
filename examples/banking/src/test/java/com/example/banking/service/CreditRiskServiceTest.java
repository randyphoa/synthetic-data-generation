package com.example.banking.service;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class CreditRiskServiceTest {

    private CreditRiskService service;

    @BeforeEach
    void setUp() {
        service = new CreditRiskService();
    }

    @Test
    void invalidScore_returnsInvalid() {
        assertEquals("INVALID", service.assessRisk(200, 0.30, 5, false, 3));
    }

    @Test
    void defaultHistory_highScore_longHistory_returnsHigh() {
        assertEquals("HIGH", service.assessRisk(750, 0.30, 10, true, 3));
    }

    @Test
    void defaultHistory_highScore_shortHistory_returnsCritical() {
        assertEquals("CRITICAL", service.assessRisk(750, 0.30, 3, true, 3));
    }

    @Test
    void defaultHistory_lowScore_returnsCritical() {
        assertEquals("CRITICAL", service.assessRisk(600, 0.30, 5, true, 3));
    }

    @Test
    void excellentScore_lowDebt_fewAccounts_returnsLow() {
        assertEquals("LOW", service.assessRisk(780, 0.20, 10, false, 5));
    }

    @Test
    void excellentScore_lowDebt_manyAccounts_returnsModerate() {
        assertEquals("MODERATE", service.assessRisk(780, 0.20, 10, false, 15));
    }

    @Test
    void excellentScore_moderateDebt_longHistory_returnsLow() {
        assertEquals("LOW", service.assessRisk(780, 0.35, 12, false, 5));
    }

    @Test
    void goodScore_lowDebt_longHistory_fewAccounts_returnsLow() {
        assertEquals("LOW", service.assessRisk(700, 0.30, 8, false, 5));
    }

    @Test
    void goodScore_moderateDebt_longHistory_returnsModerate() {
        assertEquals("MODERATE", service.assessRisk(700, 0.45, 10, false, 5));
    }

    @Test
    void goodScore_highDebt_returnsHigh() {
        assertEquals("HIGH", service.assessRisk(700, 0.55, 10, false, 5));
    }

    @Test
    void fairScore_lowDebt_longHistory_returnsModerate() {
        assertEquals("MODERATE", service.assessRisk(600, 0.30, 10, false, 5));
    }

    @Test
    void fairScore_highDebt_returnsCritical() {
        assertEquals("CRITICAL", service.assessRisk(600, 0.55, 10, false, 5));
    }

    @Test
    void poorScore_lowDebt_longHistory_returnsHigh() {
        assertEquals("HIGH", service.assessRisk(400, 0.20, 12, false, 5));
    }

    @Test
    void poorScore_highDebt_returnsCritical() {
        assertEquals("CRITICAL", service.assessRisk(400, 0.50, 5, false, 5));
    }
}
