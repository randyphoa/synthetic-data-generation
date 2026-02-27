package com.example.banking.controller;

import com.example.banking.model.entity.Account;
import com.example.banking.service.AccountFeeService;
import com.example.banking.service.AccountService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/accounts")
public class AccountController {

    private final AccountService accountService;
    private final AccountFeeService accountFeeService;

    public AccountController(AccountService accountService, AccountFeeService accountFeeService) {
        this.accountService = accountService;
        this.accountFeeService = accountFeeService;
    }

    @GetMapping
    public List<Account> getAllAccounts() {
        return accountService.findAll();
    }

    @GetMapping("/{id}")
    public ResponseEntity<Account> getAccountById(@PathVariable Long id) {
        return accountService.findById(id)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @GetMapping("/{id}/monthly-fee")
    public ResponseEntity<Map<String, Object>> getMonthlyFee(@PathVariable Long id) {
        return accountService.findById(id)
                .map(account -> {
                    double fee = accountFeeService.calculateMonthlyFee(
                            account.getAccountType().name(),
                            account.getBalance(),
                            account.isHasDirectDeposit(),
                            account.getAccountAgeMonths());
                    return ResponseEntity.ok(Map.of(
                            "accountId", account.getId(),
                            "accountType", account.getAccountType().name(),
                            "monthlyFee", fee));
                })
                .orElse(ResponseEntity.notFound().build());
    }

    @GetMapping("/{id}/transaction-fee")
    public ResponseEntity<Map<String, Object>> getTransactionFee(
            @PathVariable Long id,
            @RequestParam String type,
            @RequestParam double amount) {
        return accountService.findById(id)
                .map(account -> {
                    double fee = accountFeeService.calculateTransactionFee(
                            account.getAccountType().name(),
                            type,
                            amount,
                            0);
                    return ResponseEntity.ok(Map.of(
                            "accountId", account.getId(),
                            "transactionType", type,
                            "amount", amount,
                            "fee", fee));
                })
                .orElse(ResponseEntity.notFound().build());
    }
}
