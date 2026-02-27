package com.example.banking.model.dto;

public class CreditRiskResponse {

    private String riskRating;
    private String reason;

    public CreditRiskResponse() {}

    public CreditRiskResponse(String riskRating, String reason) {
        this.riskRating = riskRating;
        this.reason = reason;
    }

    public String getRiskRating() { return riskRating; }
    public void setRiskRating(String riskRating) { this.riskRating = riskRating; }

    public String getReason() { return reason; }
    public void setReason(String reason) { this.reason = reason; }
}
