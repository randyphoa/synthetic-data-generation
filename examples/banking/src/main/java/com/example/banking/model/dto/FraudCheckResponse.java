package com.example.banking.model.dto;

public class FraudCheckResponse {

    private String verdict;
    private String reason;

    public FraudCheckResponse() {}

    public FraudCheckResponse(String verdict, String reason) {
        this.verdict = verdict;
        this.reason = reason;
    }

    public String getVerdict() { return verdict; }
    public void setVerdict(String verdict) { this.verdict = verdict; }

    public String getReason() { return reason; }
    public void setReason(String reason) { this.reason = reason; }
}
