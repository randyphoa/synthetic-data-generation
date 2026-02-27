package com.example.banking.model.entity;

import com.example.banking.model.enums.MerchantCategory;
import com.example.banking.model.enums.TransactionType;
import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "T_TRANSACTION")
public class Transaction {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "account_id")
    private Account account;

    @Enumerated(EnumType.STRING)
    private TransactionType transactionType;

    @Enumerated(EnumType.STRING)
    private MerchantCategory merchantCategory;

    private double amount;
    private double merchantDistance;
    private boolean verified;
    private boolean international;
    private int hourOfDay;
    private LocalDateTime transactionDate;
    private String description;

    public Transaction() {}

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }

    public Account getAccount() { return account; }
    public void setAccount(Account account) { this.account = account; }

    public TransactionType getTransactionType() { return transactionType; }
    public void setTransactionType(TransactionType transactionType) { this.transactionType = transactionType; }

    public MerchantCategory getMerchantCategory() { return merchantCategory; }
    public void setMerchantCategory(MerchantCategory merchantCategory) { this.merchantCategory = merchantCategory; }

    public double getAmount() { return amount; }
    public void setAmount(double amount) { this.amount = amount; }

    public double getMerchantDistance() { return merchantDistance; }
    public void setMerchantDistance(double merchantDistance) { this.merchantDistance = merchantDistance; }

    public boolean isVerified() { return verified; }
    public void setVerified(boolean verified) { this.verified = verified; }

    public boolean isInternational() { return international; }
    public void setInternational(boolean international) { this.international = international; }

    public int getHourOfDay() { return hourOfDay; }
    public void setHourOfDay(int hourOfDay) { this.hourOfDay = hourOfDay; }

    public LocalDateTime getTransactionDate() { return transactionDate; }
    public void setTransactionDate(LocalDateTime transactionDate) { this.transactionDate = transactionDate; }

    public String getDescription() { return description; }
    public void setDescription(String description) { this.description = description; }
}
