# Banking Application Demo

A Spring Boot banking application demonstrating realistic business logic for synthetic data generation testing.

## Quick Start

```bash
cd examples/banking
./mvnw spring-boot:run
```

## Endpoints

- **Swagger UI:** http://localhost:8080/swagger-ui.html
- **H2 Console:** http://localhost:8080/h2-console (JDBC URL: `jdbc:h2:mem:bankingdb`)
- **Health:** http://localhost:8080/actuator/health

## API Examples

```bash
# Evaluate loan eligibility
curl -X POST http://localhost:8080/api/loans/evaluate \
  -H "Content-Type: application/json" \
  -d '{"creditScore": 720, "annualIncome": 85000, "monthlyDebtPayment": 1200,
       "requestedAmount": 25000, "employmentType": "FULL_TIME",
       "existingCustomer": true, "yearsEmployed": 5}'

# Check transaction for fraud
curl -X POST http://localhost:8080/api/fraud/check \
  -H "Content-Type: application/json" \
  -d '{"amount": 7500, "dailyLimit": 5000, "averageTransactionAmount": 200,
       "merchantCategory": "ELECTRONICS", "merchantDistance": 800.0,
       "verified": false, "hourOfDay": 3, "international": true}'

# Assess credit risk
curl -X POST http://localhost:8080/api/risk/assess \
  -H "Content-Type: application/json" \
  -d '{"creditScore": 680, "debtToIncomeRatio": 0.35,
       "yearsOfCreditHistory": 8, "hasDefaultHistory": false,
       "numberOfOpenAccounts": 4}'

# List customers
curl http://localhost:8080/api/customers

# Get account monthly fee
curl http://localhost:8080/api/accounts/1/monthly-fee
```

## Running Tests

```bash
./mvnw test
```

## Business Logic Services

| Service | Primary Pattern | Paths |
|---------|----------------|-------|
| `LoanEligibilityService` | Nested if/else (3+ levels) | ~22 |
| `AccountFeeService` | Switch/case + ternary | ~20 |
| `TransactionFraudService` | Compound booleans + inter-variable deps | ~18 |
| `CreditRiskService` | Ternary + numeric boundaries | ~16 |

## Technology Stack

- Java 17, Spring Boot 3.2, H2 Database, Maven, SpringDoc OpenAPI
