"""
Generate Standalone Synthetic Privilege Benchmark Dataset

Creates data/synthetic_privilege_benchmark.csv with 24 original, realistic email-style documents.
- 12 TRUE privilege cases (genuine attorney legal advice, litigation/regulatory defense strategy)
- 12 FALSE hard negatives (lawyer CC'd with business-only chatter, boilerplate disclaimer only,
  routine legal dept administrative task, business forwarding lawyer contact details, etc.)
- source = "synthetic" explicitly tagged on every row
- completely distinct from the real 400-email Enron dataset
"""

import os
import csv

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_CSV = os.path.join(DATA_DIR, "synthetic_privilege_benchmark.csv")

BENCHMARK_RECORDS = [
    # =========================================================================
    # TRUE PRIVILEGE: Genuine Attorney Legal Advice & Strategy (12 records)
    # =========================================================================
    {
        "benchmark_id": "synth_priv_001",
        "source": "synthetic",
        "category": "legal_advice_regulatory_compliance",
        "is_privileged": "TRUE",
        "sender": "elena.vance@apollocounsel.com",
        "recipient": "marcus.trent@meridianenergy.com, sarah.lin@meridianenergy.com",
        "subject": "Privileged & Confidential: Legal Assessment of CFTC Rule 43 Swaps Reporting",
        "text": (
            "Marcus and Sarah,\n\n"
            "Pursuant to your request yesterday regarding our cross-border power swap execution facilities, "
            "I have reviewed the CFTC Part 43 real-time public reporting obligations against our proposed routing architecture. "
            "In my legal opinion, routing these physical-settlement derivatives through the London desk without real-time "
            "reporting exposes Meridian to significant non-compliance sanctions under Section 2(a)(13) of the Commodity Exchange Act. "
            "I strongly advise structuring the transaction confirmations with the standardized fallback language attached in Exhibit B, "
            "which legally preserves the bona fide hedging exclusion. Let us schedule a confidential call tomorrow at 10 AM to discuss implementation.\n\n"
            "Elena Vance\nSenior Regulatory Counsel\nApollo Legal Advisors LLP"
        ),
        "privilege_explanation": "Direct legal advice from outside counsel interpreting statutory reporting requirements under the Commodity Exchange Act and recommending compliance structuring."
    },
    {
        "benchmark_id": "synth_priv_002",
        "source": "synthetic",
        "category": "litigation_strategy_work_product",
        "is_privileged": "TRUE",
        "sender": "david.ross@rosskellerlaw.com",
        "recipient": "claire.bennett@apexlogistics.com",
        "subject": "ATTORNEY WORK PRODUCT: Deposition Prep and Cross-Examination Strategy in Apex v. RailCorp",
        "text": (
            "Claire,\n\n"
            "Attached is our revised trial outline for the upcoming deposition of RailCorp's VP of Dispatch. "
            "Our litigation theory centers on establishing their intentional delay in clearing the siding tracks during the Q3 freeze. "
            "Based on the documents produced in tranche 4, we have identified three critical contradictions in their maintenance logs. "
            "Please do not share this draft outline outside the core litigation steering committee, as it reflects our mental impressions, "
            "legal theories, and targeted cross-examination sequence for the hearing before Judge Harmon next month.\n\n"
            "David Ross\nTrial Counsel\nRoss & Keller LLP"
        ),
        "privilege_explanation": "Classic attorney work-product containing mental impressions, trial theories, and cross-examination strategy for active litigation."
    },
    {
        "benchmark_id": "synth_priv_003",
        "source": "synthetic",
        "category": "legal_advice_contract_indemnity",
        "is_privileged": "TRUE",
        "sender": "nathan.kline@inhouse-vanguard.com",
        "recipient": "rachel.morales@inhouse-vanguard.com, kevin.choi@inhouse-vanguard.com",
        "subject": "LEGAL ADVICE: Indemnification Clause Risk in Project Sierra EPC Contract",
        "text": (
            "Rachel and Kevin,\n\n"
            "I have conducted a legal review of the indemnification and consequential damages limitation in Section 14.2 of the Siemens EPC draft. "
            "As currently drafted by opposing counsel, the carve-out for 'gross negligence' fails to protect Vanguard from third-party environmental claims "
            "arising under CERCLA joint-and-several liability standards. Under Texas law, indemnity provisions must meet the express negligence doctrine "
            "to enforce indemnification for our own negligence. To mitigate this exposure, you must replace their paragraph with our revised clause below, "
            "which specifically disclaims consequential damages while preserving strict environmental hold-harmless coverage.\n\n"
            "Nathan Kline\nAssistant General Counsel - Commercial Projects\nVanguard Power Infrastructure"
        ),
        "privilege_explanation": "In-house attorney providing legal counsel on contractual indemnity enforceability under state law and drafting defensive contract language."
    },
    {
        "benchmark_id": "synth_priv_004",
        "source": "synthetic",
        "category": "litigation_strategy_settlement",
        "is_privileged": "TRUE",
        "sender": "patricia.mendez@mendezlitigation.com",
        "recipient": "julian.foster@solisutilities.com, amanda.wright@solisutilities.com",
        "subject": "CONFIDENTIAL ATTORNEY-CLIENT PRIVILEGED: Mediation Risk Assessment and Settlement Authority",
        "text": (
            "Julian and Amanda,\n\n"
            "Ahead of Friday's mandatory settlement conference before Magistrate Judge Torres, our team has completed a formal exposure evaluation. "
            "If this matter proceeds to a jury verdict, our analysis indicates a 65% probability of a liability finding on the breach of warranty claim, "
            "with realistic damages ranging between $4.2M and $6.8M. Given the unfavorable pre-trial evidentiary rulings on the metallurgical test reports, "
            "we recommend seeking settlement authority up to $2.5M. Opening negotiations at $750k will position us credibly without signaling vulnerability.\n\n"
            "Patricia Mendez\nLead Defense Counsel\nMendez & Albright P.C."
        ),
        "privilege_explanation": "Outside defense litigation counsel providing legal risk evaluation, probabilistic liability assessment, and mediation strategy."
    },
    {
        "benchmark_id": "synth_priv_005",
        "source": "synthetic",
        "category": "internal_investigation_counsel",
        "is_privileged": "TRUE",
        "sender": "rebecca.hastings@sterlinglegal.com",
        "recipient": "audit.committee@zenithfin.com",
        "subject": "PRIVILEGED AND CONFIDENTIAL: Interim Findings on Whistleblower Allegations (Trade Allocation)",
        "text": (
            "To the Audit Committee of the Board of Directors:\n\n"
            "At the direction of the Audit Committee, we have conducted an independent legal inquiry into the whistleblower complaint dated January 14 "
            "regarding block-trading allocations in the municipal bond group. Based on our preliminary interview of six trading floor employees and review "
            "of Bloomberg chat archives, we have identified potential exposure under SEC Rule 10b-5 and Section 17(a) of the Securities Act. "
            "We advise immediately suspending data purge protocols on the secondary backup servers and retaining outside forensic accounting experts "
            "under our supervision to preserve attorney-client privilege over their work papers.\n\n"
            "Rebecca Hastings\nSpecial Counsel to the Audit Committee\nSterling & Sterling LLP"
        ),
        "privilege_explanation": "Counsel retained by Board Audit Committee providing legal evaluation of securities law liability and advising on preservation/investigative steps."
    },
    {
        "benchmark_id": "synth_priv_006",
        "source": "synthetic",
        "category": "legal_advice_ip_patent_infringement",
        "is_privileged": "TRUE",
        "sender": "arthur.pendleton@pendletonip.com",
        "recipient": "cto@novabiotech.com, dev-leads@novabiotech.com",
        "subject": "ATTORNEY-CLIENT PRIVILEGED: Freedom-to-Operate Analysis for Compound NB-409",
        "text": (
            "Dr. Aris and Engineering Team,\n\n"
            "We have completed the freedom-to-operate patent clearance opinion regarding Nova's synthetic ester purification technique. "
            "Having analyzed Claims 1 through 18 of US Patent 8,492,101 held by Genex Corp, our legal conclusion is that Nova's two-stage countercurrent extraction "
            "does not literally infringe due to the absence of an alkaline wash step in your operating parameters. However, to eliminate any doctrine-of-equivalents "
            "vulnerability, we strongly recommend maintaining the solvent pH strictly above 7.4. Detailed claim construction charts are attached.\n\n"
            "Arthur Pendleton\nRegistered Patent Attorney\nPendleton Intellectual Property Law Group"
        ),
        "privilege_explanation": "Formal patent freedom-to-operate legal opinion analyzing infringement risk and advising engineering changes to avoid patent litigation."
    },
    {
        "benchmark_id": "synth_priv_007",
        "source": "synthetic",
        "category": "legal_advice_employment_termination",
        "is_privileged": "TRUE",
        "sender": "laura.chen@kestrelpower.com",
        "recipient": "tom.bradford@kestrelpower.com",
        "subject": "CONFIDENTIAL: Legal Guidance on Proposed Involuntary Separation - Northwest Region",
        "text": (
            "Tom,\n\n"
            "I reviewed your performance documentation regarding the regional sales director in Seattle. "
            "Because this employee filed an OSHA safety complaint three months ago regarding generator maintenance logs, an immediate termination "
            "presents high legal risk of a statutory retaliation claim under Section 11(c) of the OSH Act. To defend against such an action, "
            "we need clearer contemporaneous documentation establishing that performance deficiencies predated the protected whistleblower activity. "
            "I recommend placing him on a 30-day objective performance improvement plan first or negotiating a mutual separation agreement with a comprehensive release.\n\n"
            "Laura Chen\nAssociate General Counsel, Labor & Employment\nKestrel Power Generation Corp"
        ),
        "privilege_explanation": "Employment counsel advising HR/management on legal exposure and defense strategy regarding retaliation claims under whistleblower statutes."
    },
    {
        "benchmark_id": "synth_priv_008",
        "source": "synthetic",
        "category": "regulatory_defense_ferc_inquiry",
        "is_privileged": "TRUE",
        "sender": "richard.thornton@thorntonenergy.com",
        "recipient": "martin.sellers@thorntonenergy.com, greg.hayes@thorntonenergy.com",
        "subject": "ATTORNEY WORK PRODUCT: Response Strategy to FERC Enforcement Staff Data Request",
        "text": (
            "Martin and Greg,\n\n"
            "FERC's Division of Investigations issued an informal data request yesterday concerning bidding behavior in the PJM day-ahead ancillary services market. "
            "My legal assessment is that FERC staff is testing whether our virtual bids constituted manipulative anti-competitive withholding under 18 CFR Part 1c. "
            "We must formulate our response narrative carefully: our submissions must demonstrate that every bid reflected bona fide economic dispatch models. "
            "I will draft our response narrative; please pull the underlying econometric dispatch curves by Friday for my privileged review before anything is disclosed.\n\n"
            "Richard Thornton\nVice President & General Counsel\nThornton Energy Trading LLC"
        ),
        "privilege_explanation": "General counsel analyzing regulatory enforcement exposure under federal anti-manipulation rules and directing factual assembly to prepare defense."
    },
    {
        "benchmark_id": "synth_priv_009",
        "source": "synthetic",
        "category": "antitrust_compliance_legal_advice",
        "is_privileged": "TRUE",
        "sender": "miriam.goldstein@goldsteinpartners.com",
        "recipient": "exec-team@apexpipeline.com",
        "subject": "ATTORNEY-CLIENT PRIVILEGED: Antitrust Review of Proposed Capacity Sharing Agreement",
        "text": (
            "Executive Team,\n\n"
            "We have evaluated the legal implications under Section 1 of the Sherman Act regarding the proposed joint capacity coordination pact with Northern Gas. "
            "Because the agreement contemplates mutual notifications of uncommitted throughput prior to open-season postings, this creates an acute risk of "
            "per se illegal horizontal market allocation. I advise against executing the memorandum of understanding in its current form. "
            "If the commercial objective is operational reliability, we must restructure the arrangement through a blind third-party clearinghouse mechanism.\n\n"
            "Miriam Goldstein\nAntitrust Practice Group Leader\nGoldstein & Partners LLP"
        ),
        "privilege_explanation": "Antitrust counsel rendering legal advice warning that proposed commercial terms risk criminal antitrust exposure under the Sherman Act."
    },
    {
        "benchmark_id": "synth_priv_0010",
        "source": "synthetic",
        "category": "legal_advice_environmental_enforcement",
        "is_privileged": "TRUE",
        "sender": "stephen.walsh@walshregulatory.com",
        "recipient": "danielle.ortiz@californiacleanpower.com",
        "subject": "PRIVILEGED & CONFIDENTIAL: EPA Region 9 Notice of Violation - Settlement Negotiation Posture",
        "text": (
            "Danielle,\n\n"
            "Following our meeting with EPA Region 9 enforcement attorneys, here is our legal assessment of the proposed administrative consent order. "
            "The agency is demanding $850k in civil penalties and mandatory continuous monitoring upgrades under the Clean Air Act Title V permit. "
            "Legally, their calculation misapplies the EPA penalty policy by counting minor startup flaring as continuous unpermitted emissions. "
            "I have drafted counter-findings of fact demonstrating that 80% of the exceeded intervals fall within the emergency upset defense under 40 CFR 60.11. "
            "Attached is our proposed response letter for your review.\n\n"
            "Stephen Walsh\nEnvironmental Counsel\nWalsh Regulatory Law Group"
        ),
        "privilege_explanation": "Environmental defense lawyer evaluating civil enforcement penalty exposure and drafting substantive legal defenses under federal environmental regulations."
    },
    {
        "benchmark_id": "synth_priv_0011",
        "source": "synthetic",
        "category": "merger_regulatory_clearance_advice",
        "is_privileged": "TRUE",
        "sender": "claudia.vogel@vogelhartman.com",
        "recipient": "brett.sommers@pacificwestenergy.com, board@pacificwestenergy.com",
        "subject": "ATTORNEY-CLIENT PRIVILEGED: HSR Clearance and Hart-Scott-Rodino Second Request Vulnerability",
        "text": (
            "Brett and Members of the Board,\n\n"
            "In preparing the pre-merger notification filings for the Cascade Midstream acquisition, our antitrust team has identified significant market concentration "
            "issues in the Williston Basin gathering submarket (HHI increase exceeding 450 points). As your legal counsel, we believe the FTC is virtually certain "
            "to issue a Second Request unless we proactively offer an upfront divestiture package for the Beaver Creek pipeline assets. "
            "We strongly counsel against submitting the initial HSR filing until we have secured a binding letter of intent with an eligible third-party buyer.\n\n"
            "Claudia Vogel\nPartner, Antitrust & M&A Regulatory\nVogel & Hartman LLP"
        ),
        "privilege_explanation": "Mergers & Acquisitions regulatory attorney providing strategic legal counsel regarding antitrust agency review and asset divestiture requirements."
    },
    {
        "benchmark_id": "synth_priv_0012",
        "source": "synthetic",
        "category": "internal_legal_memorandum_tax",
        "is_privileged": "TRUE",
        "sender": "timothy.bell@inhouse-vanguard.com",
        "recipient": "cfo@inhouse-vanguard.com, treasury@inhouse-vanguard.com",
        "subject": "LEGAL MEMORANDUM: Tax Opinion on Section 45 Production Tax Credit Eligibility",
        "text": (
            "Mark and Treasury Colleagues,\n\n"
            "Attached is my formal legal memorandum analyzing whether the repowering work completed at the Red Rock wind facility satisfies the 80/20 Rule "
            "under IRS Revenue Ruling 94-31 for renewed Section 45 tax credit qualification. Based on the documented capital expenditures and our legal interpretation "
            "of Treasury Regulation 1.48-12, the project meets the legal threshold of new property placed in service, provided we secure contemporaneous appraisal affidavits. "
            "Please treat this memorandum as privileged attorney-client work product prepared in anticipation of IRS examination.\n\n"
            "Timothy Bell\nChief Tax Counsel\nVanguard Power Infrastructure"
        ),
        "privilege_explanation": "In-house tax counsel delivering a formal legal opinion on federal statutory tax credit eligibility and tax controversy preparedness."
    },

    # =========================================================================
    # FALSE HARD NEGATIVES: Looks Privileged at First Glance, But Is Not (12 records)
    # =========================================================================
    {
        "benchmark_id": "synth_priv_0013",
        "source": "synthetic",
        "category": "lawyer_ccd_purely_business_discussion",
        "is_privileged": "FALSE",
        "sender": "greg.simpson@meridianenergy.com",
        "recipient": "marcus.trent@meridianenergy.com, terry.wong@meridianenergy.com",
        "subject": "August Gas Basis Pricing and Pipeline Nominations (CC: Elena Vance)",
        "text": (
            "Marcus and Terry,\n\n"
            "Here is the finalized commercial schedule for our August basis nominations at the Opal hub. "
            "The spread narrowed by four cents this morning, so I recommend locking in 25,000 MMBtu/day with El Paso before noon. "
            "Terry, please coordinate with dispatch to confirm gate pressure allocations. "
            "I'm copying Elena Vance from legal so she has visibility on our volume numbers for the monthly counterparty summary, "
            "but no legal questions here—this is just our standard commercial nomination sheet.\n\n"
            "Thanks,\nGreg Simpson\nSenior Gas Trader\nMeridian Energy Trading",
        ),
        "privilege_explanation": "Lawyer is merely CC'd on an operational gas trading schedule. No legal advice requested, rendered, or discussed."
    },
    {
        "benchmark_id": "synth_priv_0014",
        "source": "synthetic",
        "category": "boilerplate_disclaimer_only_logistics",
        "is_privileged": "FALSE",
        "sender": "amanda.clark@apexlogistics.com",
        "recipient": "chicago-dispatch@apexlogistics.com",
        "subject": "Catering and Lunch Orders for Tomorrow's Regional Operations Workshop",
        "text": (
            "Team,\n\n"
            "Please send your boxed lunch selections for tomorrow's regional operations meeting by 3:00 PM today. "
            "We have vegetarian, gluten-free, and regular turkey wrap options available from Panera. "
            "The training will start promptly at 8:30 AM in Conference Room C on the 4th floor.\n\n"
            "Amanda Clark\nOffice Manager\n\n"
            "*** CONFIDENTIALITY NOTICE: This transmission may contain information that is privileged, confidential, "
            "legally privileged, and exempt from disclosure under applicable law. If you are not the intended recipient, "
            "any disclosure, copying, distribution, or use of the information contained herein is strictly prohibited. ***"
        ),
        "privilege_explanation": "Email discusses catering/logistics; contains an automatic boilerplate confidentiality/privilege disclaimer footer with zero substantive legal content."
    },
    {
        "benchmark_id": "synth_priv_0015",
        "source": "synthetic",
        "category": "legal_dept_routine_administrative_intake",
        "is_privileged": "FALSE",
        "sender": "contracts-intake@solisutilities.com",
        "recipient": "robert.hayward@solisutilities.com",
        "subject": "Automated Ticket Confirmation: Contract Review Request #2024-0891 Assigned",
        "text": (
            "Robert Hayward,\n\n"
            "This automated message confirms that your contract review submission has been logged into the Legal Department workflow portal.\n"
            "Ticket ID: LEG-2024-0891\n"
            "Submission Date: August 14, 2024\n"
            "Counterparty: Caterpillar Financial Services\n"
            "Assigned Reviewer: TBD (Commercial Legal Queue)\n"
            "Target Turnaround: 5 business days\n\n"
            "You will receive an email update once an attorney has been assigned to begin drafting review. Please do not reply directly to this ticket notification.\n\n"
            "Legal Department Operations Portal\nSolis Utilities Inc."
        ),
        "privilege_explanation": "Automated administrative intake receipt generated by legal ticketing software; contains no legal advice or substantive analysis."
    },
    {
        "benchmark_id": "synth_priv_0016",
        "source": "synthetic",
        "category": "forwarding_lawyer_contact_info_unrelated",
        "is_privileged": "FALSE",
        "sender": "brian.connelly@novabiotech.com",
        "recipient": "karen.mccarthy@novabiotech.com",
        "subject": "Contact info for patent attorney / golf charity event",
        "text": (
            "Karen,\n\n"
            "You asked yesterday for Arthur Pendleton's phone number—he is our outside patent attorney at Pendleton IP Law. "
            "His direct office line is (312) 555-0198 and mobile is (312) 555-0144. "
            "He mentioned he is interested in joining our foursome for the annual Children's Hospital charity golf scramble next month. "
            "Give him a call when you have time to see if he can make the Friday tee time.\n\n"
            "Brian Connelly\nVP Business Development\nNova Biotech"
        ),
        "privilege_explanation": "Personal/social message forwarding outside attorney contact details for a charity golf event. Mentions attorney by name but contains no legal matter."
    },
    {
        "benchmark_id": "synth_priv_0017",
        "source": "synthetic",
        "category": "general_counsel_scheduling_meeting",
        "is_privileged": "FALSE",
        "sender": "laura.chen@kestrelpower.com",
        "recipient": "exec-assistants@kestrelpower.com, tom.bradford@kestrelpower.com",
        "subject": "Rescheduling Q3 Executive Strategy Lunch to Next Thursday",
        "text": (
            "Hi everyone,\n\n"
            "Due to an offsite board meeting conflict, I need to reschedule our executive team lunch that was originally set for this Tuesday. "
            "Could we move it to next Thursday at 12:30 PM at the Palm Restaurant downtown? "
            "Please confirm if that time slot works for your respective calendars, and my assistant will update the Outlook calendar invite.\n\n"
            "Laura Chen\nAssociate General Counsel\nKestrel Power Generation Corp"
        ),
        "privilege_explanation": "Administrative meeting scheduling sent by an attorney. Routine scheduling/logistical communications are not protected by privilege."
    },
    {
        "benchmark_id": "synth_priv_0018",
        "source": "synthetic",
        "category": "public_regulatory_filing_distribution",
        "is_privileged": "FALSE",
        "sender": "richard.thornton@thorntonenergy.com",
        "recipient": "all-traders@thorntonenergy.com, market-analysts@thorntonenergy.com",
        "subject": "FYI: Public FERC Order 888 Rulemaking Notice Posted Today",
        "text": (
            "Team,\n\n"
            "For your general commercial awareness, FERC has just publicly posted its Notice of Proposed Rulemaking on regional transmission organization tariffs. "
            "The full 120-page federal register notice is available on FERC's public website at www.ferc.gov/docs/filings/2024-rm21.pdf. "
            "No action is required from trading desks at this stage; this is simply the public docket notice for the upcoming open comment period.\n\n"
            "Richard Thornton\nGeneral Counsel\nThornton Energy Trading LLC"
        ),
        "privilege_explanation": "Circulation of a public regulatory agency notice without confidential legal advice, legal interpretation, or internal defense strategy."
    },
    {
        "benchmark_id": "synth_priv_0019",
        "source": "synthetic",
        "category": "outside_counsel_billing_invoice_inquiry",
        "is_privileged": "FALSE",
        "sender": "billing@rosskellerlaw.com",
        "recipient": "accounts-payable@apexlogistics.com",
        "subject": "Invoice #88412 - Ross & Keller LLP / Apex Logistics Matter 4022",
        "text": (
            "Accounts Payable Team,\n\n"
            "Attached please find our monthly statement of account and invoice #88412 for professional legal services rendered during the period of July 1 through July 31, 2024. "
            "Total outstanding balance due is $42,350.00. Please note that wire instructions have not changed from our previous remittance advice. "
            "Kindly confirm receipt and provide estimated disbursement schedule per our net-30 terms.\n\n"
            "Best regards,\nClara Oswald\nBilling Coordinator\nRoss & Keller LLP"
        ),
        "privilege_explanation": "Standard law firm billing and accounts payable correspondence; contains fee totals and wire remittance details without confidential legal substance."
    },
    {
        "benchmark_id": "synth_priv_0020",
        "source": "synthetic",
        "category": "boilerplate_disclaimer_press_release",
        "is_privileged": "FALSE",
        "sender": "media-relations@zenithfin.com",
        "recipient": "staff-announcements@zenithfin.com",
        "subject": "PRESS RELEASE: Zenith Financial Announces Expansion into Renewable Energy Tax Equity",
        "text": (
            "FOR IMMEDIATE RELEASE\n\n"
            "NEW YORK -- Zenith Financial Corp (NYSE: ZFC) today announced the launch of its dedicated Sustainable Infrastructure & Tax Equity financing group. "
            "The new division will provide structured debt and equity solutions for utility-scale solar and battery storage developments across North America. "
            "Full press release will be distributed over PR Newswire at 9:00 AM EST.\n\n"
            "Media Contact:\npress@zenithfin.com\n\n"
            "CONFIDENTIALITY NOTICE: Attorney-Client Privileged / Work Product. "
            "The information in this email is confidential and legally privileged. If you received this in error, notify the sender immediately."
        ),
        "privilege_explanation": "Public press release announcement copied to internal staff; footer contains a pasted attorney-client privilege stamp that has no legal effect on a public press release."
    },
    {
        "benchmark_id": "synth_priv_0021",
        "source": "synthetic",
        "category": "lawyer_acting_purely_in_business_negotiator_role",
        "is_privileged": "FALSE",
        "sender": "samuel.vance@inhouse-vanguard.com",
        "recipient": "dan.kramer@turbinewarehouse.com",
        "subject": "Counteroffer on Secondary Market Turbine Blades - $1.2M Firm",
        "text": (
            "Dan,\n\n"
            "I spoke with our procurement director regarding your quote on the surplus GE 1.5MW turbine rotor blades. "
            "Your asking price of $1.45M is well above current salvage book value. "
            "Vanguard is willing to offer $1.2M all-cash, provided shipment FOB site by September 15. "
            "Let me know by 5:00 PM if your management approves the price so we can instruct logistics to dispatch trucks.\n\n"
            "Samuel Vance\nVP Business Assets & Corporate Counsel\nVanguard Power Infrastructure"
        ),
        "privilege_explanation": "Corporate counsel acting purely as a commercial price negotiator haggling over turbine hardware. Business negotiations by lawyers are not privileged."
    },
    {
        "benchmark_id": "synth_priv_0022",
        "source": "synthetic",
        "category": "legal_seminar_cle_announcement",
        "is_privileged": "FALSE",
        "sender": "cle-committee@houstonbar.org",
        "recipient": "timothy.bell@inhouse-vanguard.com, legal-dept@inhouse-vanguard.com",
        "subject": "Upcoming CLE Seminar: Recent Developments in Federal Energy Regulatory Commission Enforcement",
        "text": (
            "Dear Energy Bar Association Members,\n\n"
            "Registration is now open for the 2024 Fall Continuing Legal Education (CLE) Webinar: "
            "'Navigating FERC Audits and Civil Penalty Calculations in Electric Power Markets.'\n\n"
            "Date: October 12, 2024\n"
            "Time: 1:00 PM - 3:00 PM CDT\n"
            "Credit: 2.0 hours Texas CLE (including 0.5 ethics)\n"
            "Cost: Free for active members, $75 for non-members.\n\n"
            "Click here to register online. Early registration is recommended as virtual attendance is capped.\n\n"
            "Energy Law Section | Continuing Legal Education Committee"
        ),
        "privilege_explanation": "Mass broadcast email advertising a Continuing Legal Education (CLE) webinar; contains legal industry keywords but is a marketing broadcast."
    },
    {
        "benchmark_id": "synth_priv_0023",
        "source": "synthetic",
        "category": "business_employee_asking_general_status",
        "is_privileged": "FALSE",
        "sender": "jennifer.lopez@apexpipeline.com",
        "recipient": "legal-contracts@apexpipeline.com",
        "subject": "Status check on Non-Disclosure Agreement for Vendor XYZ",
        "text": (
            "Legal Team,\n\n"
            "Could someone please check the status of the standard mutual NDA submitted for Vendor XYZ (Cisco Systems IT service agreement) last Thursday? "
            "Our cybersecurity team needs the executed document before Cisco can deliver the firewalls next Tuesday. "
            "Let me know if there are any redlines or if it is already out for signature via DocuSign.\n\n"
            "Thanks,\nJennifer Lopez\nIT Infrastructure Procurement\nApex Pipeline Co."
        ),
        "privilege_explanation": "Internal employee sending a routine administrative status check to the legal department regarding an NDA turnaround. No legal advice requested."
    },
    {
        "benchmark_id": "synth_priv_0024",
        "source": "synthetic",
        "category": "forwarded_public_news_article_by_counsel",
        "is_privileged": "FALSE",
        "sender": "stephen.walsh@walshregulatory.com",
        "recipient": "danielle.ortiz@californiacleanpower.com",
        "subject": "News Article: Wall Street Journal Article on Western Water Rights Ruling",
        "text": (
            "Danielle,\n\n"
            "Saw this article in this morning's Wall Street Journal and thought you might find it interesting given your past work on Colorado River allocations:\n\n"
            "'Supreme Court Refuses to Intervene in Multi-State Basin Dispute, Leaving Lower Court Apportionment Intact.'\n"
            "(Full article text below clipped from WSJ Online, Sept 3)\n\n"
            "No need to reply, just sharing for background reading over coffee.\n\n"
            "Stephen Walsh\nWalsh Regulatory Law Group"
        ),
        "privilege_explanation": "Lawyer forwarding a public news article for background reading with no client-specific legal advice, analysis, or strategy."
    },
]

def main():
    print("=" * 80)
    print("GENERATING STANDALONE SYNTHETIC PRIVILEGE BENCHMARK")
    print("=" * 80)

    fieldnames = [
        "benchmark_id",
        "source",
        "category",
        "is_privileged",
        "sender",
        "recipient",
        "subject",
        "text",
        "privilege_explanation"
    ]

    os.makedirs(DATA_DIR, exist_ok=True)

    with open(OUTPUT_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(BENCHMARK_RECORDS)

    print(f"Generated {len(BENCHMARK_RECORDS)} synthetic benchmark records.")
    print(f"Output saved to: {OUTPUT_CSV} ({os.path.getsize(OUTPUT_CSV)} bytes)")

    # Validation stats
    true_count = sum(1 for r in BENCHMARK_RECORDS if r["is_privileged"] == "TRUE")
    false_count = sum(1 for r in BENCHMARK_RECORDS if r["is_privileged"] == "FALSE")
    print(f"Distribution: TRUE = {true_count}, FALSE = {false_count}")
    print(f"Unique categories: {len(set(r['category'] for r in BENCHMARK_RECORDS))}")
    assert all(r["source"] == "synthetic" for r in BENCHMARK_RECORDS), "All records must have source='synthetic'"
    assert len(BENCHMARK_RECORDS) == len(set(r["benchmark_id"] for r in BENCHMARK_RECORDS)), "Duplicate IDs found!"

if __name__ == "__main__":
    main()
