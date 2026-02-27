package com.example.banking.repository;

import com.example.banking.model.entity.Account;
import com.example.banking.model.enums.AccountType;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;
import java.util.List;

@Repository
public interface AccountRepository extends JpaRepository<Account, Long> {

    List<Account> findByCustomerId(Long customerId);

    List<Account> findByAccountType(AccountType accountType);

    @Query("SELECT a FROM Account a WHERE a.balance < 0")
    List<Account> findOverdrawnAccounts();

    @Query("SELECT COUNT(a) FROM Account a WHERE a.customer.id = :customerId")
    long countByCustomerId(@Param("customerId") Long customerId);
}
