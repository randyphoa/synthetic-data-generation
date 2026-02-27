package com.example.banking.model.dto;

public class LoanEligibilityResponse {

    private String decision;
    private String reason;

    public LoanEligibilityResponse() {}

    public LoanEligibilityResponse(String decision, String reason) {
        this.decision = decision;
        this.reason = reason;
    }

    public String getDecision() { return decision; }
    public void setDecision(String decision) { this.decision = decision; }

    public String getReason() { return reason; }
    public void setReason(String reason) { this.reason = reason; }
}
