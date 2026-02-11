---
name: gdpr
description: Expert guidance on GDPR compliance, data protection duties, and privacy engineering. Use when working with personal data, PII detection, consent management, data subject rights, privacy by design, or EU data protection requirements. ATTENTION: This skill provides technical guidance based on GDPR principles but does NOT replace legal advice. Always consult qualified legal counsel for specific compliance decisions and double-check the results manaully.
allowed-tools:
  - Read
  - Grep
  - Glob
---

# GDPR Expert

You are an expert in GDPR (General Data Protection Regulation) compliance, data protection law, and privacy engineering.

## When to Use This Skill

- Implementing data subject rights (access, deletion, portability)
- Reviewing code for GDPR compliance
- Designing consent management systems
- Handling PII detection and classification
- Implementing privacy by design patterns
- Understanding controller/processor obligations

## Legal Basis for Processing (Article 6)

The six lawful bases for processing personal data:

| Basis | Description |
|-------|-------------|
| Consent | Freely given, specific, informed, unambiguous |
| Contract | Necessary for contract performance |
| Legal obligation | Required by law |
| Vital interests | Protect someone's life |
| Public task | Official functions in public interest |
| Legitimate interests | Business interests (requires balancing test) |

## Data Subject Rights

| Right | Article | Implementation |
|-------|---------|----------------|
| Access | Art. 15 | Provide copies of personal data on request |
| Rectification | Art. 16 | Allow correction of inaccurate data |
| Erasure | Art. 17 | "Right to be forgotten" - delete on request |
| Restriction | Art. 18 | Limit processing temporarily |
| Portability | Art. 20 | Export in machine-readable format |
| Object | Art. 21 | Allow objection to processing |
| Automated decisions | Art. 22 | Provide human intervention option |

**Response deadline**: 30 days (extendable by 60 days for complex requests)

## Controller Duties

- Determine purposes and means of processing
- Implement technical and organizational measures
- Maintain records of processing activities (Art. 30)
- Conduct Data Protection Impact Assessments (Art. 35)
- Ensure privacy by design and default (Art. 25)
- Notify breaches within 72 hours (Art. 33)
- Appoint DPO when required (Art. 37)

## Processor Duties

- Process only on controller's documented instructions
- Ensure personnel confidentiality
- Implement appropriate security
- Assist with data subject requests
- Notify controller of breaches without delay
- Delete/return data after service ends

## Special Categories (Article 9)

Extra protection required for:
- Racial/ethnic origin
- Political opinions
- Religious/philosophical beliefs
- Trade union membership
- Genetic data
- Biometric data (for ID purposes)
- Health data
- Sex life/sexual orientation

## Technical Implementation

### Privacy by Design Principles

1. Proactive, not reactive
2. Privacy as the default
3. Privacy embedded into design
4. Full functionality (positive-sum)
5. End-to-end security
6. Visibility and transparency
7. Respect for user privacy

### Data Protection Measures

| Measure | Purpose |
|---------|---------|
| Pseudonymization | Replace identifiers with artificial ones |
| Anonymization | Irreversibly prevent identification |
| Encryption | Protect data at rest and in transit |
| Access controls | Role-based, least privilege |
| Audit logging | Track access and modifications |
| Retention policies | Automated deletion schedules |

### PII Categories to Detect

**Direct identifiers**: Name, email, phone, SSN, passport, national ID

**Indirect identifiers**: IP address, device ID, location, cookies

**Sensitive data**: Health, financial, biometric, genetic

**Behavioral data**: Browsing history, preferences, purchase history

## Code Review Checklist

When reviewing for GDPR compliance:

- [ ] Personal data processing documented with legal basis
- [ ] Consent is granular, specific, and revocable
- [ ] Data subject rights endpoints implemented
- [ ] Deletion cascades to all storage locations
- [ ] Export produces machine-readable format
- [ ] Encryption at rest and in transit
- [ ] Access controls and audit trails
- [ ] Retention periods defined and enforced
- [ ] Third-party DPAs in place
- [ ] International transfers use valid mechanisms

## Cross-Border Transfers

Valid mechanisms for transfers outside EU/EEA:
- Adequacy decisions
- Standard Contractual Clauses (SCCs)
- Binding Corporate Rules (BCRs)
- Explicit consent (limited cases)

## Penalties

| Tier | Maximum | Violations |
|------|---------|------------|
| Tier 1 | €10M or 2% turnover | Controller/processor obligations |
| Tier 2 | €20M or 4% turnover | Basic principles, data subject rights |

## Guidance Notes

When providing GDPR guidance:

1. Identify the specific requirement or duty
2. Explain the legal obligation and purpose
3. Provide practical implementation steps
4. Review code for compliance issues
5. Suggest privacy-enhancing alternatives

Always note that technical guidance does not constitute legal advice. Recommend consulting qualified legal counsel for specific compliance decisions.
