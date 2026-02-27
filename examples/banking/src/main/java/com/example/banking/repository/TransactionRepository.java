package com.example.banking.repository;

import com.example.banking.model.entity.Transaction;
import com.example.banking.model.enums.TransactionType;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;
import java.time.LocalDateTime;
import java.util.List;

@Repository
public interface TransactionRepository extends JpaRepository<Transaction, Long> {

    List<Transaction> findByAccountId(Long accountId);

    List<Transaction> findByTransactionType(TransactionType transactionType);

    @Query("SELECT t FROM Transaction t WHERE t.account.id = :accountId AND t.transactionDate >= :since")
    List<Transaction> findRecentByAccountId(@Param("accountId") Long accountId, @Param("since") LocalDateTime since);

    @Query("SELECT COUNT(t) FROM Transaction t WHERE t.account.id = :accountId AND t.transactionType = :type")
    long countByAccountIdAndType(@Param("accountId") Long accountId, @Param("type") TransactionType type);
}
