package com.example.banking.controller;

import com.example.banking.service.LoanEligibilityService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.bean.MockBean;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@WebMvcTest(LoanController.class)
class LoanControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private LoanEligibilityService loanEligibilityService;

    @Test
    void evaluateLoan_returnsDecision() throws Exception {
        when(loanEligibilityService.evaluateLoanEligibility(
                anyInt(), anyDouble(), anyDouble(), anyDouble(), anyString(), anyBoolean(), anyInt()))
                .thenReturn("APPROVED_PREMIUM");

        String requestBody = """
                {
                    "creditScore": 780,
                    "annualIncome": 120000,
                    "monthlyDebtPayment": 2000,
                    "requestedAmount": 25000,
                    "employmentType": "FULL_TIME",
                    "existingCustomer": true,
                    "yearsEmployed": 8
                }
                """;

        mockMvc.perform(post("/api/loans/evaluate")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(requestBody))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.decision").value("APPROVED_PREMIUM"));
    }
}
