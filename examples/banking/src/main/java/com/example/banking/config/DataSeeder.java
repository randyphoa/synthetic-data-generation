package com.example.banking.config;

import com.example.banking.model.entity.Account;
import com.example.banking.model.entity.Customer;
import com.example.banking.model.entity.LoanApplication;
import com.example.banking.model.entity.Transaction;
import com.example.banking.model.enums.*;
import com.example.banking.repository.AccountRepository;
import com.example.banking.repository.CustomerRepository;
import com.example.banking.repository.TransactionRepository;
import org.springframework.boot.CommandLineRunner;
import org.springframework.stereotype.Component;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Component
public class DataSeeder implements CommandLineRunner {

    private final CustomerRepository customerRepository;
    private final AccountRepository accountRepository;
    private final TransactionRepository transactionRepository;

    public DataSeeder(CustomerRepository customerRepository,
                      AccountRepository accountRepository,
                      TransactionRepository transactionRepository) {
        this.customerRepository = customerRepository;
        this.accountRepository = accountRepository;
        this.transactionRepository = transactionRepository;
    }

    @Override
    public void run(String... args) {
        // Customer 1: Excellent credit, full-time, existing customer
        Customer c1 = new Customer();
        c1.setFirstName("Alice");
        c1.setLastName("Johnson");
        c1.setEmail("alice.johnson@example.com");
        c1.setPhone("555-0101");
        c1.setStatus(CustomerStatus.ACTIVE);
        c1.setEmploymentType(EmploymentType.FULL_TIME);
        c1.setCreditScore(780);
        c1.setYearsEmployed(8);
        c1.setAnnualIncome(120000);
        c1.setExistingCustomer(true);
        c1.setDateOfBirth(LocalDate.of(1985, 3, 15));
        c1.setMemberSince(LocalDate.of(2015, 6, 1));
        customerRepository.save(c1);

        // Customer 2: Good credit, self-employed
        Customer c2 = new Customer();
        c2.setFirstName("Bob");
        c2.setLastName("Martinez");
        c2.setEmail("bob.martinez@example.com");
        c2.setPhone("555-0102");
        c2.setStatus(CustomerStatus.ACTIVE);
        c2.setEmploymentType(EmploymentType.SELF_EMPLOYED);
        c2.setCreditScore(710);
        c2.setYearsEmployed(12);
        c2.setAnnualIncome(95000);
        c2.setExistingCustomer(true);
        c2.setDateOfBirth(LocalDate.of(1978, 11, 22));
        c2.setMemberSince(LocalDate.of(2018, 1, 15));
        customerRepository.save(c2);

        // Customer 3: Fair credit, part-time
        Customer c3 = new Customer();
        c3.setFirstName("Carol");
        c3.setLastName("Williams");
        c3.setEmail("carol.williams@example.com");
        c3.setPhone("555-0103");
        c3.setStatus(CustomerStatus.ACTIVE);
        c3.setEmploymentType(EmploymentType.PART_TIME);
        c3.setCreditScore(620);
        c3.setYearsEmployed(3);
        c3.setAnnualIncome(32000);
        c3.setExistingCustomer(false);
        c3.setDateOfBirth(LocalDate.of(1992, 7, 8));
        c3.setMemberSince(LocalDate.of(2023, 3, 10));
        customerRepository.save(c3);

        // Customer 4: Retired, good credit
        Customer c4 = new Customer();
        c4.setFirstName("David");
        c4.setLastName("Chen");
        c4.setEmail("david.chen@example.com");
        c4.setPhone("555-0104");
        c4.setStatus(CustomerStatus.ACTIVE);
        c4.setEmploymentType(EmploymentType.RETIRED);
        c4.setCreditScore(740);
        c4.setYearsEmployed(0);
        c4.setAnnualIncome(65000);
        c4.setExistingCustomer(true);
        c4.setDateOfBirth(LocalDate.of(1955, 1, 30));
        c4.setMemberSince(LocalDate.of(2005, 9, 20));
        customerRepository.save(c4);

        // Customer 5: New customer, poor credit
        Customer c5 = new Customer();
        c5.setFirstName("Eva");
        c5.setLastName("Patel");
        c5.setEmail("eva.patel@example.com");
        c5.setPhone("555-0105");
        c5.setStatus(CustomerStatus.ACTIVE);
        c5.setEmploymentType(EmploymentType.FULL_TIME);
        c5.setCreditScore(540);
        c5.setYearsEmployed(1);
        c5.setAnnualIncome(45000);
        c5.setExistingCustomer(false);
        c5.setDateOfBirth(LocalDate.of(1998, 5, 12));
        c5.setMemberSince(LocalDate.of(2024, 11, 1));
        customerRepository.save(c5);

        // Accounts
        Account a1 = createAccount(c1, AccountType.CHECKING, CustomerStatus.ACTIVE, 15200.50, true, 96, LocalDate.of(2016, 2, 1));
        Account a2 = createAccount(c1, AccountType.SAVINGS, CustomerStatus.ACTIVE, 45000.00, false, 96, LocalDate.of(2016, 2, 1));
        Account a3 = createAccount(c2, AccountType.CHECKING, CustomerStatus.ACTIVE, 8300.75, true, 72, LocalDate.of(2018, 1, 15));
        Account a4 = createAccount(c2, AccountType.MONEY_MARKET, CustomerStatus.ACTIVE, 52000.00, false, 36, LocalDate.of(2021, 6, 1));
        Account a5 = createAccount(c3, AccountType.CHECKING, CustomerStatus.ACTIVE, 1200.00, false, 12, LocalDate.of(2023, 3, 10));
        Account a6 = createAccount(c4, AccountType.SAVINGS, CustomerStatus.ACTIVE, 125000.00, false, 228, LocalDate.of(2005, 9, 20));
        Account a7 = createAccount(c4, AccountType.CD, CustomerStatus.ACTIVE, 50000.00, false, 18, LocalDate.of(2023, 8, 1));
        Account a8 = createAccount(c5, AccountType.CHECKING, CustomerStatus.ACTIVE, 850.25, false, 3, LocalDate.of(2024, 11, 1));

        // Transactions
        createTransaction(a1, TransactionType.DEPOSIT, MerchantCategory.ATM, 3000.00, 0.0, true, false, 10, "Payroll direct deposit");
        createTransaction(a1, TransactionType.WITHDRAWAL, MerchantCategory.ATM, 200.00, 2.0, true, false, 14, "ATM withdrawal");
        createTransaction(a1, TransactionType.PAYMENT, MerchantCategory.GROCERY, 156.32, 5.0, true, false, 11, "Whole Foods Market");
        createTransaction(a1, TransactionType.PAYMENT, MerchantCategory.FUEL, 65.00, 3.0, true, false, 8, "Shell Gas Station");
        createTransaction(a1, TransactionType.TRANSFER, MerchantCategory.ATM, 1000.00, 0.0, true, false, 9, "Transfer to savings");
        createTransaction(a2, TransactionType.DEPOSIT, MerchantCategory.ATM, 1000.00, 0.0, true, false, 9, "Transfer from checking");
        createTransaction(a3, TransactionType.DEPOSIT, MerchantCategory.ATM, 4500.00, 0.0, true, false, 10, "Client payment");
        createTransaction(a3, TransactionType.PAYMENT, MerchantCategory.ELECTRONICS, 899.99, 15.0, true, false, 16, "Best Buy - laptop");
        createTransaction(a3, TransactionType.PAYMENT, MerchantCategory.RESTAURANT, 45.80, 1.5, true, false, 19, "Olive Garden");
        createTransaction(a3, TransactionType.WITHDRAWAL, MerchantCategory.ATM, 500.00, 8.0, true, false, 12, "ATM withdrawal");
        createTransaction(a4, TransactionType.DEPOSIT, MerchantCategory.ATM, 5000.00, 0.0, true, false, 10, "Monthly investment");
        createTransaction(a5, TransactionType.DEPOSIT, MerchantCategory.ATM, 1800.00, 0.0, true, false, 10, "Paycheck deposit");
        createTransaction(a5, TransactionType.PAYMENT, MerchantCategory.GROCERY, 89.50, 3.0, true, false, 17, "Kroger");
        createTransaction(a5, TransactionType.PAYMENT, MerchantCategory.ENTERTAINMENT, 15.99, 0.0, true, false, 20, "Netflix subscription");
        createTransaction(a6, TransactionType.WITHDRAWAL, MerchantCategory.ATM, 1500.00, 1.0, true, false, 10, "Monthly withdrawal");
        createTransaction(a6, TransactionType.PAYMENT, MerchantCategory.TRAVEL, 2500.00, 500.0, true, true, 14, "Intl hotel booking");
        createTransaction(a8, TransactionType.DEPOSIT, MerchantCategory.ATM, 850.25, 0.0, true, false, 10, "Initial deposit");
        createTransaction(a8, TransactionType.PAYMENT, MerchantCategory.GROCERY, 67.30, 4.0, true, false, 18, "Trader Joes");
        createTransaction(a8, TransactionType.PAYMENT, MerchantCategory.FUEL, 40.00, 2.0, true, false, 7, "Exxon");
        createTransaction(a1, TransactionType.PAYMENT, MerchantCategory.ELECTRONICS, 7500.00, 800.0, false, true, 3, "Suspicious intl electronics purchase");
    }

    private Account createAccount(Customer customer, AccountType type, CustomerStatus status,
                                  double balance, boolean hasDirectDeposit, int ageMonths, LocalDate openDate) {
        Account account = new Account();
        account.setCustomer(customer);
        account.setAccountType(type);
        account.setStatus(status);
        account.setBalance(balance);
        account.setHasDirectDeposit(hasDirectDeposit);
        account.setAccountAgeMonths(ageMonths);
        account.setOpenDate(openDate);
        return accountRepository.save(account);
    }

    private void createTransaction(Account account, TransactionType type, MerchantCategory category,
                                   double amount, double distance, boolean verified, boolean international,
                                   int hour, String description) {
        Transaction txn = new Transaction();
        txn.setAccount(account);
        txn.setTransactionType(type);
        txn.setMerchantCategory(category);
        txn.setAmount(amount);
        txn.setMerchantDistance(distance);
        txn.setVerified(verified);
        txn.setInternational(international);
        txn.setHourOfDay(hour);
        txn.setTransactionDate(LocalDateTime.now().minusDays((int) (Math.random() * 30)));
        txn.setDescription(description);
        transactionRepository.save(txn);
    }
}
