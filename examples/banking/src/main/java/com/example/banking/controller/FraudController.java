package com.example.banking.controller;

import com.example.banking.model.dto.FraudCheckRequest;
import com.example.banking.model.dto.FraudCheckResponse;
import com.example.banking.service.TransactionFraudService;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/fraud")
public class FraudController {

    private final TransactionFraudService transactionFraudService;

    public FraudController(TransactionFraudService transactionFraudService) {
        this.transactionFraudService = transactionFraudService;
    }

    @PostMapping("/check")
    public FraudCheckResponse checkFraud(@RequestBody FraudCheckRequest request) {
        String verdict = transactionFraudService.assessTransaction(
                request.getAmount(),
                request.getDailyLimit(),
                request.getAverageTransactionAmount(),
                request.getMerchantCategory(),
                request.getMerchantDistance(),
                request.isVerified(),
                request.getHourOfDay(),
                request.isInternational());
        return new FraudCheckResponse(verdict, "Fraud assessment complete for amount " + request.getAmount());
    }
}
