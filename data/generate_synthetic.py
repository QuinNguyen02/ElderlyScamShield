# data/generate_synthetic.py
import csv, random, os

scam_templates = [
    "This is the police. Your bank account has been compromised, transfer {amount} to {acc}.",
    "Congratulations! You won a government grant. Provide your bank details to receive {amount}.",
    "Your card has been charged fraudulently. Call us at {phone} immediately and confirm your CVV.",
    "This is the bank. We need your OTP {otp} to resolve an urgent problem."
]

legit_templates = [
    "Let's schedule your medical appointment for next Monday.",
    "Are we still on for the meeting tomorrow?",
    "Your parcel is out for delivery and will arrive today.",
    "Reminder: Your electricity bill is due next week."
]

def mk_amount(): return f"${random.randint(50,5000)}"
def mk_acc(): return "".join(random.choice("0123456789") for _ in range(10))
def mk_phone(): return "+84" + "".join(random.choice("0123456789") for _ in range(9))
def mk_otp(): return "".join(random.choice("0123456789") for _ in range(6))

def generate_data():
    rows = []
    for _ in range(600):
        t = random.choice(scam_templates)
        rows.append([t.format(amount=mk_amount(), acc=mk_acc(), phone=mk_phone(), otp=mk_otp()), 1])
    for _ in range(1200):
        t = random.choice(legit_templates)
        rows.append([t, 0])
    random.shuffle(rows)
    return rows

if __name__ == "__main__":
    rows = generate_data()
    os.makedirs("data", exist_ok=True)
    with open("data/train.csv", "w", encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["text", "label"])
        writer.writerows(rows)
    print("Wrote data/train.csv")