package com.example.banking.model.dto;

public class CreditRiskRequest {

    private int creditScore;
    private double debtToIncomeRatio;
    private int yearsOfCreditHistory;
    private boolean hasDefaultHistory;
    private int numberOfOpenAccounts;

    public int getCreditScore() { return creditScore; }
    public void setCreditScore(int creditScore) { this.creditScore = creditScore; }

    public double getDebtToIncomeRatio() { return debtToIncomeRatio; }
    public void setDebtToIncomeRatio(double debtToIncomeRatio) { this.debtToIncomeRatio = debtToIncomeRatio; }

    public int getYearsOfCreditHistory() { return yearsOfCreditHistory; }
    public void setYearsOfCreditHistory(int yearsOfCreditHistory) { this.yearsOfCreditHistory = yearsOfCreditHistory; }

    public boolean isHasDefaultHistory() { return hasDefaultHistory; }
    public void setHasDefaultHistory(boolean hasDefaultHistory) { this.hasDefaultHistory = hasDefaultHistory; }

    public int getNumberOfOpenAccounts() { return numberOfOpenAccounts; }
    public void setNumberOfOpenAccounts(int numberOfOpenAccounts) { this.numberOfOpenAccounts = numberOfOpenAccounts; }
}
