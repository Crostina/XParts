import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timedelta, timezone
import time  # ← NEW

# ────────────────────────────────────────────────
#  CONFIG
# ────────────────────────────────────────────────

SERVICE_ACCOUNT_KEY = "firebaseKey.json"
LOOKBACK_HOURS = 4
SLEEP_SECONDS = 60  # ← change to 60, 300, etc. if 30s feels too fast

ACCOUNTS_POOL = {
    "fr-465934": {
        "credentials": {
            "accountLogin": "fr-465934",
            "userLogin": "admin",
            "password": "Ous123456"
        },
        "proxy": {
            "host": "159.148.236.157",
            "port": "6363",
            "user": "tanhagcl",
            "pass": "v782jk65whl3"
        }
    },
    "fr-957263": {
        "credentials": {
            "accountLogin": "fr-957263",
            "userLogin": "admin",
            "password": "Zakzak05"
        },
        "proxy": {
            "host": "31.98.7.126",
            "port": "6304",
            "user": "tanhagcl",
            "pass": "v782jk65whl3"
        }
    }
}

# ────────────────────────────────────────────────

cred = credentials.Certificate(SERVICE_ACCOUNT_KEY)
firebase_admin.initialize_app(cred)
db = firestore.client()

def balance_accounts():
    print(f"\n=== Balance check at {datetime.now()} ===\n")

    cutoff = datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)

    account_counts = {}
    for acc in ACCOUNTS_POOL.keys():
        count = (
            db.collection("search_logs")
            .where("accountID", "==", acc)
            .where("timestamp", ">=", cutoff)
            .count()
            .get()[0][0].value
        )
        account_counts[acc] = count

    least_used = min(account_counts, key=account_counts.get)
    least_count = account_counts[least_used]

    print("Search counts (last {} hours):".format(LOOKBACK_HOURS))
    for acc, cnt in sorted(account_counts.items()):
        print(f"  {acc}: {cnt} searches")
    print(f"\nLeast used account → {least_used} ({least_count} searches)\n")

    if least_count == 0:
        print("All accounts have zero recent searches — balancing evenly.\n")

    users_ref = db.collection("users")
    all_users = users_ref.stream()

    updated_count = 0
    for user_doc in all_users:
        guid = user_doc.id
        data = user_doc.to_dict()

        current_acc = data.get("credentials", {}).get("accountLogin")
        if not current_acc:
            print(f"Skipping {guid} — no accountLogin")
            continue

        if current_acc == least_used:
            # print(f"User {guid} already on {least_used} → no change")
            continue

        print(f"Re-assigning {guid} from {current_acc} → {least_used}")

        user_doc.reference.update({
            "credentials.accountLogin": least_used,
            "credentials.userLogin": ACCOUNTS_POOL[least_used]["credentials"]["userLogin"],
            "credentials.password": ACCOUNTS_POOL[least_used]["credentials"]["password"],
            "proxy": ACCOUNTS_POOL[least_used]["proxy"],
            "lastReassigned": firestore.SERVER_TIMESTAMP
        })

        updated_count += 1

    if updated_count > 0:
        print(f"\nUpdated {updated_count} users to {least_used}")
    else:
        print("No re-assignments needed this cycle")

    print("=== Balance cycle complete ===\n")

if __name__ == "__main__":
    print("Starting automatic balance loop... Press Ctrl+C to stop.")
    try:
        while True:
            balance_accounts()
            print(f"Waiting {SLEEP_SECONDS} seconds before next check...\n")
            time.sleep(SLEEP_SECONDS)
    except KeyboardInterrupt:
        print("\nStopped by user. Bye!")
