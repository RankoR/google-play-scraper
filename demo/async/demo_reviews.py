import asyncio

from google_play_scraper import GooglePlayClient, Sort


async def amain():
    client = GooglePlayClient()
    app_id = "com.mojang.minecraftpe"

    print(f"Fetching reviews for {app_id}...")

    # 1. Fetch First Page
    reviews, token = await client.areviews(app_id, num=5, sort=Sort.HELPFULNESS)

    print(f"--- Page 1 ({len(reviews)} reviews) ---")
    for r in reviews:
        print(f"[{r.score}/5] {r.user_name}: {r.text[:50]}...")

    # 2. Fetch Second Page (if token exists)
    if token:
        print(f"\nFetching next page with token: {token[:20]}...")
        reviews_p2, _ = await client.areviews(
            app_id,
            num=5,
            sort=Sort.HELPFULNESS,
            pagination_token=token,
        )

        print(f"--- Page 2 ({len(reviews_p2)} reviews) ---")
        for r in reviews_p2:
            print(f"[{r.score}/5] {r.user_name}: {r.text[:50]}...")
    else:
        print("No more pages.")


def main():
    asyncio.run(amain())


if __name__ == "__main__":
    main()
