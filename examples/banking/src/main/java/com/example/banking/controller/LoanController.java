package com.example.banking.controller;

import com.example.banking.model.dto.LoanEligibilityRequest;
import com.example.banking.model.dto.LoanEligibilityResponse;
import com.example.banking.service.LoanEligibilityService;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/loans")
public class LoanController {

    private final LoanEligibilityService loanEligibilityService;

    public LoanController(LoanEligibilityService loanEligibilityService) {
        this.loanEligibilityService = loanEligibilityService;
    }

    @PostMapping("/evaluate")
    public LoanEligibilityResponse evaluateLoan(@RequestBody LoanEligibilityRequest request) {
        String decision = loanEligibilityService.evaluateLoanEligibility(
                request.getCreditScore(),
                request.getAnnualIncome(),
                request.getMonthlyDebtPayment(),
                request.getRequestedAmount(),
                request.getEmploymentType(),
                request.isExistingCustomer(),
                request.getYearsEmployed());
        return new LoanEligibilityResponse(decision, "Evaluation complete for credit score " + request.getCreditScore());
    }
}
