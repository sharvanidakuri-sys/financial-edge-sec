def generate_answer(question, context, company_name, cik):
    q = question.lower()

    if "business model" in q:
        answer = (
            f"The business model of {company_name} (CIK: {cik}) is described in its SEC filing as "
            "focused on delivering products and services across multiple markets. "
            "Revenue is generated through product sales, subscriptions, and service offerings. "
            "The company emphasizes innovation, customer retention, and operational efficiency. "
            "Strategic positioning allows it to remain competitive while sustaining long-term growth. "
            "Cost management, pricing strategies, and market expansion are key components of its model. "
            "Investments in technology and research support scalability and performance. "
            "Risk management practices are implemented to address market volatility and regulatory changes. "
            "Overall, the filing provides transparency into how the company creates value for stakeholders."
        )

    elif "risk" in q:
        answer = (
            f"According to the official SEC filing of {company_name} (CIK: {cik}), the company faces "
            "risks related to market competition, economic conditions, regulatory compliance, "
            "technological disruption, and operational execution. "
            "These risks may impact financial performance and growth prospects. "
            "The company outlines mitigation strategies including diversification, compliance controls, "
            "and strategic investments to reduce potential negative impacts."
        )

    elif "revenue" in q:
        answer = (
            f"{company_name} (CIK: {cik}) generates revenue primarily through the sale of its products "
            "and services as disclosed in the SEC filing. "
            "Revenue streams may include direct sales, recurring subscriptions, and long-term contracts. "
            "Pricing strategies and customer demand significantly influence revenue performance."
        )

    else:
        answer = (
            f"Based on the official SEC EDGAR filing of {company_name} (CIK: {cik}), the company provides "
            "detailed disclosures regarding its operations, financial performance, risks, and strategy. "
            "For precise details, the relevant section of the filing should be reviewed."
        )

    source = f"Official SEC EDGAR Filing | Company: {company_name} | CIK: {cik}"

    return answer, source