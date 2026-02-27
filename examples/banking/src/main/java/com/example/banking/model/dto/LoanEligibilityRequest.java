package com.example.banking.model.dto;

public class LoanEligibilityRequest {

    private int creditScore;
    private double annualIncome;
    private double monthlyDebtPayment;
    private double requestedAmount;
    private String employmentType;
    private boolean existingCustomer;
    private int yearsEmployed;

    public int getCreditScore() { return creditScore; }
    public void setCreditScore(int creditScore) { this.creditScore = creditScore; }

    public double getAnnualIncome() { return annualIncome; }
    public void setAnnualIncome(double annualIncome) { this.annualIncome = annualIncome; }

    public double getMonthlyDebtPayment() { return monthlyDebtPayment; }
    public void setMonthlyDebtPayment(double monthlyDebtPayment) { this.monthlyDebtPayment = monthlyDebtPayment; }

    public double getRequestedAmount() { return requestedAmount; }
    public void setRequestedAmount(double requestedAmount) { this.requestedAmount = requestedAmount; }

    public String getEmploymentType() { return employmentType; }
    public void setEmploymentType(String employmentType) { this.employmentType = employmentType; }

    public boolean isExistingCustomer() { return existingCustomer; }
    public void setExistingCustomer(boolean existingCustomer) { this.existingCustomer = existingCustomer; }

    public int getYearsEmployed() { return yearsEmployed; }
    public void setYearsEmployed(int yearsEmployed) { this.yearsEmployed = yearsEmployed; }
}
