const sampleFinancialData = {
  financial_data: {
    client_id: "CL-TEST-001",
    as_of_date: "2026-10-09",
    risk_profile: "conservative",
    annual_income: 2160000,
    cash_balance: 180000,
    monthly_history: [
      { month: "2026-07", income: 180000, expenses: 90000, savings: 90000, investments: 25000, debt_balance: 200000 },
      { month: "2026-08", income: 180000, expenses: 95000, savings: 85000, investments: 25000, debt_balance: 190000 },
      { month: "2026-09", income: 180000, expenses: 155000, savings: 25000, investments: 10000, debt_balance: 185000 },
    ],
    transactions: [
      { id: "TX-001", date: "2026-10-02", description: "Monthly groceries", category: "groceries", amount: 8500, transaction_type: "debit", currency: "INR", merchant: "Sample Market" },
      { id: "TX-002", date: "2026-10-04", description: "Large electronics purchase", category: "electronics", amount: 85000, transaction_type: "debit", currency: "INR", merchant: "Sample Electronics" },
      { id: "TX-003", date: "2026-10-06", description: "Monthly salary", category: "income", amount: 180000, transaction_type: "credit", currency: "INR", merchant: "Employer" },
    ],
    holdings: [
      { symbol: "FUND-A", asset_class: "equity", market_value: 500000, cost_basis: 450000 },
      { symbol: "FUND-B", asset_class: "debt", market_value: 250000, cost_basis: 240000 },
    ],
    liabilities: [
      { name: "Personal loan", outstanding: 185000, interest_rate: 12, monthly_payment: 12000 },
    ],
    goals: [
      { name: "Emergency fund", target_amount: 600000, target_date: "2027-10-09", priority: "HIGH" },
    ],
  },
};

export default sampleFinancialData;
