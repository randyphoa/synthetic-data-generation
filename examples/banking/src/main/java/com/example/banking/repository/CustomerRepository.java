package com.example.banking.repository;

import com.example.banking.model.entity.Customer;
import com.example.banking.model.enums.CustomerStatus;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;
import java.util.List;

@Repository
public interface CustomerRepository extends JpaRepository<Customer, Long> {

    List<Customer> findByStatus(CustomerStatus status);

    List<Customer> findByCreditScoreGreaterThanEqual(int minScore);

    @Query("SELECT c FROM Customer c WHERE c.creditScore >= :minScore AND c.creditScore <= :maxScore")
    List<Customer> findByCreditScoreRange(@Param("minScore") int minScore, @Param("maxScore") int maxScore);

    @Query("SELECT c FROM Customer c WHERE c.annualIncome >= :minIncome AND c.status = :status")
    List<Customer> findByMinIncomeAndStatus(@Param("minIncome") double minIncome, @Param("status") CustomerStatus status);
}
