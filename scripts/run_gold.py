import os
from supabase import create_client

def main():
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_ROLE"]  # именно service_role
    supabase = create_client(url, key)

    resp = supabase.rpc("refresh_gold_estate").execute()
    print("Refresh result:", resp)

if __name__ == "__main__":
    main()
