"""Seed FDRSETU with DEMO / SYNTHETIC data: 20 institutions, 5 banks, ~100 FDRs,
4 role logins, a mock bank ledger, verification history, renewals, releases.

Also generates `sample_docs/sample_fdr.pdf` — a text-based FDR the OCR
pipeline can extract during demos.
"""
import os
import random
from datetime import date, timedelta

from .database import SessionLocal, engine, Base
from .models import (
    User, Role, Institution, Bank, FDRRecord, FDRStatus, VerificationStatus,
    RiskLevel, MockBankLedger, VerificationHistory, RenewalRecord,
    ReleaseRequest, ReleaseStatus, ApprovalHistory, Notification, RiskAlert,
    FDRDocument, VerificationRequest, AuditLog,
)
from .security import hash_password
from .services.risk import run_risk_checks, scan_all
from .services.maturity import run_maturity_scan

random.seed(42)

DEMO_PASSWORD = "Demo@123"

BANKS = [
    ("State Bank of India", "SBIN"), ("Punjab National Bank", "PUNB"),
    ("Bank of Baroda", "BARB"), ("HDFC Bank", "HDFC"), ("ICICI Bank", "ICIC"),
]

INSTITUTIONS = [
    "National Institute of Technology Raipur", "Government Engineering College Bilaspur",
    "Indian Institute of Technology Bhilai", "Bhilai Institute of Technology Durg",
    "Shri Shankaracharya Technical Campus", "Rungta College of Engineering",
    "Chhattisgarh Swami Vivekanand Technical University", "OP Jindal University Raigarh",
    "MATS University Raipur", "Kalinga University Naya Raipur",
    "Amity University Chhattisgarh", "ITM University Raipur",
    "Dr CV Raman University Bilaspur", "KR Technical College Ambikapur",
    "Central Institute of Technology Raipur", "Shri Rawatpura Sarkar Institute",
    "Columbia Institute of Engineering", "Lakhmi Chand Institute of Technology",
    "Disha Institute of Management", "Raipur Institute of Technology",
]

STATES = [("Chhattisgarh", "Raipur"), ("Chhattisgarh", "Bilaspur"), ("Chhattisgarh", "Durg"),
          ("Maharashtra", "Nagpur"), ("Madhya Pradesh", "Bhopal")]

BRANCHES = ["Main Branch", "Civil Lines", "University Road", "Sector 21", "Station Road"]

DEMO_USERS = [
    ("institution@fdrsetu.demo", "Institution Officer", Role.institution, 1, None),
    ("officer@fdrsetu.demo", "AICTE Verification Officer", Role.officer, None, None),
    ("bank@fdrsetu.demo", "SBI Bank Officer", Role.bank, None, 1),
    ("admin@fdrsetu.demo", "Super Administrator", Role.admin, None, None),
]


def create_sample_pdf(path: str):
    """Generate a text-based FDR PDF the OCR pipeline can parse."""
    import pymupdf
    doc = pymupdf.open()
    page = doc.new_page()
    text = (
        "STATE BANK OF INDIA\n"
        "Fixed Deposit Receipt — DEMO / SYNTHETIC\n\n"
        "FDR No: SBI98765432101\n"
        "Branch: Civil Lines, Raipur\n"
        "IFSC: SBIN0001234\n\n"
        "Deposit Amount: Rs. 12,50,000.00\n"
        "Interest Rate: 6.80 % per annum\n\n"
        "Issue Date: 15/01/2026\n"
        "Maturity Date: 15/01/2029\n\n"
        "This is a synthetic demonstration document generated for the FDRSETU\n"
        "Smart India Hackathon prototype. Not a real bank instrument.\n"
    )
    page.insert_text((72, 100), text, fontsize=12)
    doc.save(path)
    doc.close()


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    if db.query(User).first():
        db.close()
        return False

    banks = [Bank(name=n, short_code=c, is_demo=True) for n, c in BANKS]
    db.add_all(banks)
    db.flush()

    insts = []
    for i, name in enumerate(INSTITUTIONS):
        st, city = STATES[i % len(STATES)]
        insts.append(Institution(
            code=f"INST-{i+1:03d}", name=name,
            institution_type=random.choice(["Engineering College", "Polytechnic", "University"]),
            state=st, city=city, contact_email=f"registrar{i+1}@inst{i+1:03d}.edu.demo",
            contact_phone=f"0771-{2200000+i}", is_demo=True))
    db.add_all(insts)
    db.flush()

    users = []
    for email, name, role, inst_id, bank_id in DEMO_USERS:
        users.append(User(email=email, full_name=name,
                          password_hash=hash_password(DEMO_PASSWORD), role=role,
                          institution_id=inst_id, bank_id=bank_id))
    # a second institution user + a couple more bank officers
    users.append(User(email="inst2@fdrsetu.demo", full_name="Institution Officer 2",
                      password_hash=hash_password(DEMO_PASSWORD), role=Role.institution,
                      institution_id=2))
    users.append(User(email="bank.pnb@fdrsetu.demo", full_name="PNB Bank Officer",
                      password_hash=hash_password(DEMO_PASSWORD), role=Role.bank, bank_id=2))
    db.add_all(users)
    db.flush()

    # --- FDR records across varied windows + ledger ---
    today = date.today()
    fdrs = []
    n = 0
    fdr_counter = 50000000000
    for i in range(100):
        n += 1
        inst = insts[i % len(insts)]
        bank = banks[i % len(banks)]
        fdr_num = str(fdr_counter + n * 137)
        amount = random.choice([500000, 750000, 1000000, 1250000, 1500000,
                                2000000, 2500000, 3500000, 5000000])
        issue = today - timedelta(days=random.randint(30, 900))
        tenure = random.choice([365, 730, 1095])
        maturity = issue + timedelta(days=tenure)
        ifsc = f"{bank.short_code}0{100000 + i:06d}"[:11]
        fdr = FDRRecord(
            fdr_uid=f"FDRSETU-{n:05d}", fdr_number=fdr_num,
            institution_id=inst.id, bank_id=bank.id,
            branch=random.choice(BRANCHES), ifsc=ifsc, amount=amount,
            interest_rate=round(random.uniform(5.5, 7.5), 2),
            issue_date=issue, maturity_date=maturity,
            status=(FDRStatus.expired if maturity < today else
                    random.choice([FDRStatus.active, FDRStatus.active, FDRStatus.verified])),
            verification_status=(VerificationStatus.verified
                                 if random.random() < 0.55 else VerificationStatus.pending),
            is_demo=True, created_by_id=users[0].id,
        )
        # match ledger 90% of the time
        if random.random() < 0.9:
            lamt = float(amount) * (1.15 if random.random() < 0.07 else 1.0)
            db.add(MockBankLedger(fdr_number=fdr_num, bank_id=bank.id,
                                  branch=fdr.branch, ifsc=ifsc, amount=lamt,
                                  issue_date=issue, maturity_date=maturity))
        fdrs.append(fdr)
    db.add_all(fdrs)
    db.flush()

    # --- deliberate duplicates / anomalies for demo scenario 2 ---
    dup_target = fdrs[10]
    dup = FDRRecord(
        fdr_uid=f"FDRSETU-{101:05d}", fdr_number=dup_target.fdr_number,
        institution_id=insts[7].id, bank_id=dup_target.bank_id,
        branch=dup_target.branch, ifsc=dup_target.ifsc, amount=dup_target.amount,
        interest_rate=dup_target.interest_rate, issue_date=dup_target.issue_date,
        maturity_date=dup_target.maturity_date, status=FDRStatus.pending,
        verification_status=VerificationStatus.pending, is_demo=True,
        created_by_id=users[0].id)
    db.add(dup)
    bad = FDRRecord(
        fdr_uid=f"FDRSETU-{102:05d}", fdr_number="999888777666",
        institution_id=insts[3].id, bank_id=banks[0].id,
        branch="Unknown", ifsc="BADIFSC", amount=1000000,
        issue_date=today + timedelta(days=5), maturity_date=today + timedelta(days=2),
        status=FDRStatus.pending, verification_status=VerificationStatus.pending,
        is_demo=True, created_by_id=users[0].id)
    db.add(bad)
    db.flush()

    # --- renewals: a few expired FDRs renewed into new ones ---
    renewed = 0
    for f in fdrs:
        if f.status == FDRStatus.expired and renewed < 8:
            new_num = str(fdr_counter + 90000 + renewed)
            new_fdr = FDRRecord(
                fdr_uid=f"FDRSETU-R{renewed+1:04d}", fdr_number=new_num,
                institution_id=f.institution_id, bank_id=f.bank_id,
                branch=f.branch, ifsc=f.ifsc, amount=f.amount,
                interest_rate=f.interest_rate,
                issue_date=f.maturity_date,
                maturity_date=f.maturity_date + timedelta(days=1095),
                status=FDRStatus.active, verification_status=VerificationStatus.verified,
                renewed_from_id=f.id, is_demo=True, created_by_id=users[0].id)
            db.add(new_fdr)
            db.flush()
            f.status = FDRStatus.renewed
            db.add(RenewalRecord(old_fdr_id=f.id, new_fdr_id=new_fdr.id,
                                 institution_id=f.institution_id, status="completed"))
            renewed += 1
    # pending renewal requests
    pending_renewed = 0
    for f in fdrs:
        if f.status in (FDRStatus.expired, FDRStatus.active) and pending_renewed < 5 and f.id not in [r.old_fdr_id for r in db.query(RenewalRecord).all()]:
            db.add(RenewalRecord(old_fdr_id=f.id, institution_id=f.institution_id,
                                 status="pending", remarks="Awaiting renewed FDR submission"))
            pending_renewed += 1

    # --- release requests ---
    officer = users[1]
    released_count = 0
    for i, f in enumerate(fdrs[:12]):
        if i % 3 == 0:
            continue
        status = ReleaseStatus.pending
        if i % 4 == 1:
            status = ReleaseStatus.under_review
        r = ReleaseRequest(fdr_id=f.id, institution_id=f.institution_id,
                           reason="Security deposit refund — approval of closure/completion.",
                           status=status)
        db.add(r)
        db.flush()
        if status == ReleaseStatus.under_review:
            db.add(ApprovalHistory(release_request_id=r.id, officer_id=officer.id,
                                   action="under_review", remarks="Pending clearance check."))
        released_count += 1
        if released_count >= 8:
            break

    # --- verification history samples ---
    for f in fdrs:
        if f.verification_status == VerificationStatus.verified:
            db.add(VerificationHistory(
                fdr_id=f.id, officer_id=users[4].id,  # bank officer
                bank_confirmed_number=True, bank_confirmed_amount=True,
                bank_confirmed_maturity=True, bank_confirmed_branch=True,
                result="verified", remarks="Confirmed via mock bank API.", mock_api=True))

    db.commit()

    # --- risk scan + maturity scan ---
    scan_all(db)
    run_maturity_scan(db)

    # --- sample doc for OCR demo ---
    os.makedirs("../sample_docs", exist_ok=True)
    create_sample_pdf("../sample_docs/sample_fdr.pdf")

    db.close()
    return True


if __name__ == "__main__":
    created = seed()
    print("Seeded demo data." if created else "Database already seeded — skipping.")
