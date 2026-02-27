package com.example.banking.model.dto;

public class FraudCheckRequest {

    private double amount;
    private double dailyLimit;
    private double averageTransactionAmount;
    private String merchantCategory;
    private double merchantDistance;
    private boolean verified;
    private int hourOfDay;
    private boolean international;

    public double getAmount() { return amount; }
    public void setAmount(double amount) { this.amount = amount; }

    public double getDailyLimit() { return dailyLimit; }
    public void setDailyLimit(double dailyLimit) { this.dailyLimit = dailyLimit; }

    public double getAverageTransactionAmount() { return averageTransactionAmount; }
    public void setAverageTransactionAmount(double averageTransactionAmount) { this.averageTransactionAmount = averageTransactionAmount; }

    public String getMerchantCategory() { return merchantCategory; }
    public void setMerchantCategory(String merchantCategory) { this.merchantCategory = merchantCategory; }

    public double getMerchantDistance() { return merchantDistance; }
    public void setMerchantDistance(double merchantDistance) { this.merchantDistance = merchantDistance; }

    public boolean isVerified() { return verified; }
    public void setVerified(boolean verified) { this.verified = verified; }

    public int getHourOfDay() { return hourOfDay; }
    public void setHourOfDay(int hourOfDay) { this.hourOfDay = hourOfDay; }

    public boolean isInternational() { return international; }
    public void setInternational(boolean international) { this.international = international; }
}
