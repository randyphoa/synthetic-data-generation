package com.example.banking.controller;

import com.example.banking.model.dto.CreditRiskRequest;
import com.example.banking.model.dto.CreditRiskResponse;
import com.example.banking.service.CreditRiskService;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/risk")
public class RiskController {

    private final CreditRiskService creditRiskService;

    public RiskController(CreditRiskService creditRiskService) {
        this.creditRiskService = creditRiskService;
    }

    @PostMapping("/assess")
    public CreditRiskResponse assessRisk(@RequestBody CreditRiskRequest request) {
        String rating = creditRiskService.assessRisk(
                request.getCreditScore(),
                request.getDebtToIncomeRatio(),
                request.getYearsOfCreditHistory(),
                request.isHasDefaultHistory(),
                request.getNumberOfOpenAccounts());
        return new CreditRiskResponse(rating, "Risk assessment complete for credit score " + request.getCreditScore());
    }
}
